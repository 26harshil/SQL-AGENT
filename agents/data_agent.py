import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.llm_picks import pick_llm
from models.schema import DataAgentSchema, RouterSchema
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from agents.etl_analyst import etl_analyst
from agents.sql_analyst import sql_analyst


llm = pick_llm("low")
llm_router = llm.with_structured_output(RouterSchema)


# ---------------------------- DATA AGENT GRAPH ---------------------------- #

def router_node(state: DataAgentSchema) -> DataAgentSchema:
    message = state.messages[-1].content
    route_response_dict = llm_router.invoke(message).model_dump()
    state.route_response = route_response_dict["answer"]
    return state


def etl_node(state: DataAgentSchema) -> DataAgentSchema:
    message = state.messages[-1].content
    response = etl_analyst.invoke({"messages": [HumanMessage(content=message)]})
    state.messages = state.messages + [response]
    return state


def sql_node(state: DataAgentSchema) -> DataAgentSchema:
    message = state.messages[-1].content
    input_schema = {
        "messages": [],
        "user_question": f"{message}",
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": "",
    }
    response = sql_analyst.invoke(input_schema)
    state.messages = state.messages + [response]
    return state


def route_edge(state: DataAgentSchema) -> str:
    if state.route_response == "sql":
        return "sql_node"
    elif state.route_response == "etl":
        return "etl_node"
    else:
        raise ValueError(f"Invalid route response: {state.route_response}")


data_agent_graph = StateGraph(DataAgentSchema)
data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "router_node")
data_agent_graph.add_conditional_edges(
    "router_node",
    route_edge,
    {
        "sql_node": "sql_node",
        "etl_node": "etl_node",
    },
)
data_agent_graph.add_edge("etl_node", END)
data_agent_graph.add_edge("sql_node", END)

data_agent = data_agent_graph.compile()


if __name__ == "__main__":
    try:
        png_data = data_agent.get_graph().draw_mermaid_png()
        with open("data_agent_graph.png", "wb") as f:
            f.write(png_data)
        print("Data Agent Graph saved as data_agent_graph.png")
    except Exception as e:
        print(f"Graph image generation skipped: {e}")

    try:
        response = data_agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="I want to extract data from 'https://pokeapi.co/api/v2/pokemon' and save it in data/extract as CSV."
                    )
                ],
                "route_response": "",
            }
        )
        print("Agent Response:", response)
    except Exception as e:
        print(f"Data agent test notification: {e}")
