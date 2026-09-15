import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langgraph.graph import StateGraph, START, END
from models.schema import AgentSchema
from agents.sql_analyst import (
    curate_ques,
    prompt_query_context,
    generate_sql,
    is_safe_sql,
    deterministic_sql_guard,
    canceled_sql,
    execute_sql,
    represent_final_answer,
    route_after_deterministic_guard,
    route_after_llm_judge,
)

# ============================== Graph Builder ==============================
sql_agent_graph = StateGraph(AgentSchema)

# Nodes
sql_agent_graph.add_node("curate_ques", curate_ques)
sql_agent_graph.add_node("prompt_query_context", prompt_query_context)
sql_agent_graph.add_node("generate_sql", generate_sql)
sql_agent_graph.add_node("deterministic_sql_guard", deterministic_sql_guard)
sql_agent_graph.add_node("is_safe_sql", is_safe_sql)
sql_agent_graph.add_node("canceled_sql", canceled_sql)
sql_agent_graph.add_node("execute_sql", execute_sql)
sql_agent_graph.add_node("represent_final_answer", represent_final_answer)

# Linear Edges
sql_agent_graph.add_edge(START, "curate_ques")
sql_agent_graph.add_edge("curate_ques", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql")
sql_agent_graph.add_edge("generate_sql", "deterministic_sql_guard")

# Conditional Edges
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

sql_agent = sql_agent_graph.compile()

if __name__ == "__main__":
    try:
        graph = sql_agent.get_graph()
        png_data = graph.draw_mermaid_png()
        with open("sql_agent_graph.png", "wb") as f:
            f.write(png_data)
        print("Graph saved as sql_agent_graph.png")
    except Exception as e:
        print(f"Graph rendering error: {e}")
