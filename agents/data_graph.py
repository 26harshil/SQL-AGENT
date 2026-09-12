
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.schema import DataAgentSchema
from langgraph.graph import StateGraph, START, END


# Create the graph
data_agent_graph = StateGraph(DataAgentSchema)


# Add nodes
data_agent_graph.add_node("router_node", lambda state: state)
data_agent_graph.add_node("etl_node", lambda state: state)
data_agent_graph.add_node("sql_node", lambda state: state)


# Add edges
data_agent_graph.add_edge(START, "router_node")


def route_edge(state: DataAgentSchema) -> str:
    if state.route_response == "sql":
        return "sql_node"
    elif state.route_response == "etl":
        return "etl_node"
    else:
        raise ValueError(
            f"Invalid route response: {state.route_response}"
        )


data_agent_graph.add_conditional_edges(
    "router_node",
    route_edge,
    {
        "sql_node": "sql_node",
        "etl_node": "etl_node",
    },
)


# Compile the graph
data_agent = data_agent_graph.compile()


# Draw and save the graph as PNG
if __name__ == "__main__":
    png_data = data_agent.get_graph().draw_mermaid_png()

    with open("data_agent_graph.png", "wb") as f:
        f.write(png_data)

    print("Graph saved successfully!")