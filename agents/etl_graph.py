
import os
import sys

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

from langgraph.graph import StateGraph, START, END
from models.schema import ETLAgentSchema


# Create a dummy graph with the same nodes and edges
etl_analyst_graph = StateGraph(ETLAgentSchema)

etl_analyst_graph.add_node("llm_node", lambda state: state)
etl_analyst_graph.add_node("tool_node", lambda state: state)

etl_analyst_graph.add_edge(START, "llm_node")


def is_tool_call(state: ETLAgentSchema):
    # Only needed to define the graph structure
    return "tool_node"


etl_analyst_graph.add_conditional_edges(
    "llm_node",
    is_tool_call,
    {
        "tool_node": "tool_node",
        "end": END,
    },
)

etl_analyst_graph.add_edge("tool_node", "llm_node")


# Compile the graph
etl_analyst = etl_analyst_graph.compile()


# Save graph as PNG
png_data = etl_analyst.get_graph().draw_mermaid_png()

output_path = os.path.join(
    os.path.dirname(__file__),
    "etl_analyst_graph.png",
)

with open(output_path, "wb") as f:
    f.write(png_data)

print(f"Graph saved successfully at: {output_path}")