import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.database import DatabaseUtil
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from models.schema import JudgeSchema, AgentSchema
from utils.llm_picks import pick_llm
from utils.sql_guard import SQLGuard


def _clean_llm_text(response) -> str:
    """Extract clean string text from LLM response (supports strings, lists, and dicts)."""
    if hasattr(response, "content"):
        content = response.content
    else:
        content = response

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            elif isinstance(item, str):
                parts.append(item)
            elif hasattr(item, "text"):
                parts.append(item.text)
            else:
                parts.append(str(item))
        text = "".join(parts).strip()
    elif isinstance(content, str):
        text = content.strip()
    else:
        text = str(content).strip()

    # Strip code block fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
        elif len(lines) >= 2:
            text = "\n".join(lines[1:]).strip()

    return text


# -------------------------------------- AI Agent Nodes --------------------------------------


def curate_ques(state: AgentSchema) -> dict:
    """Refines and clarifies the user question."""
    user_question = state.user_question

    llm = pick_llm("low")
    response = llm.invoke(f"Curate the following question to make it clear and specific for SQL generation: {user_question}")
    curated_question = _clean_llm_text(response)

    return {
        "curated_ques": curated_question,
        "messages": [HumanMessage(content=curated_question)],
    }


def prompt_query_context(state: AgentSchema) -> dict:
    """Extracts database schema details and prepares the context prompt for SQL generation."""
    curated_question = state.curated_ques

    conn_details = {
       "host": os.environ.get("HOST"),
        "port": int(os.environ.get("PORT")),
        "user": os.environ.get("USER"),
        "password": os.environ.get("PASSWORD"),
        "dbname": os.environ.get("DATABASE"),
    }

    obj = DatabaseUtil(conn_details)
    schema_info = obj.schema_details("public")

    prompt = f"""
    You are an SQL analyst agent. Your task is to convert the user's natural language 
    query into a Postgres SQL query that can be executed on the database. You are provided 
    with the user's original query and the schema details of the database, including
    table names, column names, data types, and sample data for each table.
    
    Unless the user explicitly asks for a specific number of rows, always limit the output to 10 rows.
    Note - Just generate the raw SQL query without any markdown formatting, explanation, or additional text.
    
    User's Query: {curated_question}

    Database Schema Details:
    {schema_info}
    """.strip()

    return {"prompt_query_context": prompt}


def generate_sql(state: AgentSchema) -> dict:
    """Generates the SQL query based on the curated prompt and schema context."""
    prompt = state.prompt_query_context
    llm = pick_llm("medium")
    response = llm.invoke(prompt)
    generated_sql_query = _clean_llm_text(response)

    return {"generated_sql_query": generated_sql_query}


def deterministic_sql_guard(state: AgentSchema) -> dict:
    """
    Deterministic AST validation using sqlglot before allowing the LLM judge
    or database execution to proceed.
    """
    sql_guard = SQLGuard()
    generated_sql = state.generated_sql_query
    result = sql_guard.validate(generated_sql)

    if not result.is_safe:
        return {
            "sql_guard_passed": False,
            "sql_guard_reason": result.reason,
            "normalized_sql": None,
            "is_safe": "No",
            "comments": f"Deterministic SQL guard rejected the query: {result.reason}",
        }

    return {
        "sql_guard_passed": True,
        "sql_guard_reason": result.reason,
        "normalized_sql": result.normalized_sql,
        "generated_sql_query": result.normalized_sql,
    }


def is_safe_sql(state: AgentSchema) -> dict:
    """LLM Safety Judge acting as a second security reviewer."""
    sql_query = state.generated_sql_query

    llm = pick_llm("medium")
    llm_judge = llm.with_structured_output(JudgeSchema)

    prompt = f"""
    You are an SQL Judge for data security. Your task is to determine whether the SQL query is 
    safe or not. The SQL query should only be used for read-only data retrieval and must not modify the 
    database in any way. Reject any query containing DDL or DML mutations such as INSERT, UPDATE, DELETE, 
    DROP, ALTER, TRUNCATE, CREATE, or administrative commands.
    
    SQL query to evaluate:
    {sql_query}
    """

    response = llm_judge.invoke(prompt)
    if hasattr(response, "model_dump"):
        resp_dict = response.model_dump()
    elif isinstance(response, dict):
        resp_dict = response
    else:
        resp_dict = {"answer": getattr(response, "answer", "No"), "comments": getattr(response, "comments", "")}

    return {
        "is_safe": resp_dict["answer"],
        "comments": resp_dict["comments"],
    }


def canceled_sql(state: AgentSchema) -> dict:
    """Handles rejected SQL queries and provides clear explanations to the user."""
    reason = state.comments or state.sql_guard_reason or "Safety violation detected."
    final_answer = (
        f"The generated SQL query was not executed because it failed the safety checks. Reason: {reason}"
    )
    return {
        "final_answer": final_answer,
        "messages": [AIMessage(content=final_answer)],
    }


def execute_sql(state: AgentSchema) -> dict:
    """Executes validated SQL query using read-only transaction limits."""
    if not state.sql_guard_passed:
        raise RuntimeError("Execution blocked: deterministic SQL guard did not pass.")

    if state.is_safe != "Yes":
        raise RuntimeError("Execution blocked: SQL judge did not approve the query.")

    sql_query = state.generated_sql_query
    if not sql_query:
        raise RuntimeError("Execution blocked: SQL query is empty.")

    conn_details = {
        "host": os.environ.get("HOST"),
        "port": int(os.environ.get("PORT")),
        "user": os.environ.get("USER"),
        "password": os.environ.get("PASSWORD"),
        "dbname": os.environ.get("DATABASE"),
    }

    obj = DatabaseUtil(conn_details)
    execution_result = obj.execute_sql(sql_query)

    return {"sql_query_execution_result": execution_result}


def represent_final_answer(state: AgentSchema) -> dict:
    """Formats the raw query execution result into a user-friendly natural language response."""
    execution_result = state.sql_query_execution_result
    curated_question = state.curated_ques

    llm = pick_llm("low")

    prompt = f"""
    You are an SQL analyst agent. Provide a final, user-friendly response based on the
    execution result of the SQL query and the user's original question.
    
    User Question: {curated_question}
    Execution Result:
    {execution_result}
    """

    response = llm.invoke(prompt)
    final_answer = _clean_llm_text(response)

    return {
        "final_answer": final_answer,
        "messages": [AIMessage(content=final_answer)],
    }


# -------------------------------------- Conditional Edge Routing --------------------------------------


def route_after_deterministic_guard(state: AgentSchema) -> str:
    """Continue to the LLM judge only if the deterministic AST guard passes."""
    if state.sql_guard_passed:
        return "is_safe_sql"
    return "canceled_sql"


def route_after_llm_judge(state: AgentSchema) -> str:
    """Execute SQL only if the LLM judge also approves."""
    if state.is_safe == "Yes":
        return "execute_sql"
    return "canceled_sql"


# -------------------------------------- StateGraph Builder --------------------------------------

sql_agent_graph = StateGraph(AgentSchema)

# Add Nodes
sql_agent_graph.add_node("curate_ques", curate_ques)
sql_agent_graph.add_node("prompt_query_context", prompt_query_context)
sql_agent_graph.add_node("generate_sql", generate_sql)
sql_agent_graph.add_node("deterministic_sql_guard", deterministic_sql_guard)
sql_agent_graph.add_node("is_safe_sql", is_safe_sql)
sql_agent_graph.add_node("canceled_sql", canceled_sql)
sql_agent_graph.add_node("execute_sql", execute_sql)
sql_agent_graph.add_node("represent_final_answer", represent_final_answer)

# Add Linear Edges
sql_agent_graph.add_edge(START, "curate_ques")
sql_agent_graph.add_edge("curate_ques", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql")
sql_agent_graph.add_edge("generate_sql", "deterministic_sql_guard")

# Add Conditional Edges
sql_agent_graph.add_conditional_edges(
    "deterministic_sql_guard",
    route_after_deterministic_guard,
    {
        "is_safe_sql": "is_safe_sql",
        "canceled_sql": "canceled_sql",
    },
)

sql_agent_graph.add_conditional_edges(
    "is_safe_sql",
    route_after_llm_judge,
    {
        "execute_sql": "execute_sql",
        "canceled_sql": "canceled_sql",
    },
)

sql_agent_graph.add_edge("canceled_sql", END)
sql_agent_graph.add_edge("execute_sql", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer", END)

sql_analyst = sql_agent_graph.compile()


if __name__ == "__main__":
    try:
        graph = sql_analyst.get_graph()
        png_data = graph.draw_mermaid_png()
        with open("sql_agent_graph.png", "wb") as f:
            f.write(png_data)
        print("SQL Agent Graph saved as sql_agent_graph.png")
    except Exception as e:
        print(f"Graph image generation skipped: {e}")

    input_schema = {
        "user_question": "What are the different types of Payment Methods we have in our database",
    }

    try:
        sql_analyst_response = sql_analyst.invoke(input_schema)
        print("\nFinal Messages:", sql_analyst_response.get("messages"))
        print("Generated SQL:", sql_analyst_response.get("generated_sql_query"))
        print("SQL Guard Passed:", sql_analyst_response.get("sql_guard_passed"))
        print("Final Answer:", sql_analyst_response.get("final_answer"))
    except Exception as e:
        print(f"Invocation error: {e}")