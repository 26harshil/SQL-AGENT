import os
import sys
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.schema import ETLAgentSchema
from utils.llm_picks import pick_llm
from utils.etl_tools import ETLTools
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain.tools import tool


@tool
def extract_load_tool(url: str, output_folder: str, format: str = "csv") -> str:
    """
    Extracts data from an API endpoint (url) and loads it into the desired location (output_folder).

    Args:
        url (str): The API endpoint from which to extract data.
        output_folder (str): The folder where the extracted data will be saved.
        format (str): The format in which to save the extracted data (csv, json, parquet).

    Returns:
        str: A message indicating the outcome of the operation.
    """
    etl_obj = ETLTools()
    return etl_obj.extract_load(url, output_folder, format)


@tool
def transform_load_tool(
    input_file_path: str,
    output_folder: str,
    output_format: str,
    user_question: str
) -> str:
    """
    Transforms data from input_file_path using a secured Pandas Docker sandbox
    and loads the result into output_folder.

    Args:
        input_file_path (str): The path to the source dataset file.
        output_folder (str): The folder where transformed data will be saved.
        output_format (str): Desired output format (csv, json, parquet).
        user_question (str): Transformation requirements specified by the user.

    Returns:
        str: Status of AST validation and sandbox transformation.
    """
    etl_tools = ETLTools()
    input_path = Path(input_file_path)
    input_filename = input_path.name
    output_filename = f"transformed_data.{output_format.lower().strip()}"

    context_preview = etl_tools.transform_load_context(input_file_path)

    llm = pick_llm("low")

    prompt = f"""
    You are a Python Data Analyst creating secure Pandas transformation code.
    You must write ONLY executable Python code with no markdown fences, no explanations, and no comments.
    
    ENVIRONMENT CONVENTIONS:
    - The input directory is provided via the Path variable `INPUT_DIR`.
    - The output directory is provided via the Path variable `OUTPUT_DIR`.
    - Read input data from: `INPUT_DIR / "{input_filename}"`
    - Write output data to: `OUTPUT_DIR / "{output_filename}"`
    - Use standard pandas methods (e.g. pd.read_csv, df.to_csv, df.to_parquet, df.to_json).
    - Do NOT import os, sys, subprocess, socket, or requests.
    - Do NOT call exec, eval, or open arbitrary paths.
    
    TRANSFORMATION REQUIREMENT:
    {user_question}
    
    DATASET PREVIEW & SCHEMA:
    {context_preview}
    """.strip()

    response = llm.invoke(prompt)
    raw_code = response.content if hasattr(response, "content") else str(response)

    # Clean code of markdown formatting
    pandas_code = raw_code.strip()
    if pandas_code.startswith("```"):
        lines = pandas_code.splitlines()
        if len(lines) >= 2:
            pandas_code = "\n".join(lines[1:-1]).strip()

    # Execute securely via ETLTools (Python AST guard + Docker sandbox)
    result = etl_tools.execute_code(
        pandas_code=pandas_code,
        input_file_path=input_file_path,
        output_folder=output_folder,
        output_format=output_format,
    )

    return (
        f"Pandas Transformation Execution Summary:\n"
        f"- Target Output: {output_folder}/{output_filename}\n"
        f"- Result: {result}\n\n"
        f"Generated Code:\n{pandas_code}"
    )


# Register Tools
tools = [extract_load_tool, transform_load_tool]
llm = pick_llm("medium")
llm_bind = llm.bind_tools(tools)


# ============================== Agent Graph Nodes ==============================

def llm_node(state: ETLAgentSchema) -> ETLAgentSchema:
    """Invokes LLM with bound ETL tools based on conversation history."""
    messages = state.messages

    prompt = f"""
    You are a Data Engineering Agent with access to tools for extracting, loading,
    and transforming data in a secure sandboxed environment.
    Review the user's request and execute the necessary tool calls.
    If the operation is already complete, inform the user with a concise summary.
    Chat history: {messages}
    """
    final_answer = llm_bind.invoke(prompt)
    state.messages = messages + [final_answer]
    return state


def tool_node(state: ETLAgentSchema) -> ETLAgentSchema:
    """Executes requested ETL tools and appends results to message history."""
    tools_results = []
    tools_by_name = {tool.name: tool for tool in tools}

    last_message = state.messages[-1]
    tool_calls = getattr(last_message, "tool_calls", [])

    for tool_call in tool_calls:
        tool_fn = tools_by_name[tool_call["name"]]
        observation = tool_fn.invoke(tool_call["args"])
        tools_results.append(
            ToolMessage(content=str(observation), tool_call_id=tool_call["id"])
        )

    state.messages = state.messages + tools_results
    return state


def is_tool_call(state: ETLAgentSchema) -> str:
    """Determines whether another tool call is needed or if workflow is finished."""
    last_message = state.messages[-1]
    tool_calls = getattr(last_message, "tool_calls", [])
    if tool_calls:
        return "tool_node"
    return "end"


# Build ETL StateGraph
etl_analyst_graph = StateGraph(ETLAgentSchema)
etl_analyst_graph.add_node("llm_node", llm_node)
etl_analyst_graph.add_node("tool_node", tool_node)

etl_analyst_graph.add_edge(START, "llm_node")
etl_analyst_graph.add_conditional_edges(
    "llm_node",
    is_tool_call,
    {
        "tool_node": "tool_node",
        "end": END,
    },
)
etl_analyst_graph.add_edge("tool_node", "llm_node")

etl_analyst = etl_analyst_graph.compile()


if __name__ == "__main__":
    try:
        png_data = etl_analyst.get_graph().draw_mermaid_png()
        with open("etl_analyst_graph.png", "wb") as f:
            f.write(png_data)
        print("ETL Analyst Graph saved as etl_analyst_graph.png")
    except Exception as e:
        print(f"Graph image generation skipped: {e}")
