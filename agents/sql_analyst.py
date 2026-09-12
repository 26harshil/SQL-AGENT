

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.database import DatabaseUtil
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from models.schema import JudgeSchema
from utils.llm_picks import pick_llm
from models.schema import AgentSchema


# -------------------------------------- AI Agent Code--------------------------------------

def curate_ques(state: AgentSchema) -> AgentSchema: 

    user_question = state.user_question # Bcz this is a Pydantic model object

    llm = pick_llm("low")  # Pick the appropriate LLM based on the level of the question

    response = llm.invoke(f"Curate the following question: {user_question}").content

    state.curated_ques = response
    state.messages = state.messages + [HumanMessage(content=f"{response}")]  # Append the curated question to the messages list

    return state 


def prompt_query_context(state: AgentSchema) -> AgentSchema:

    curated_question = state.curated_ques

    conn_details = {
        "host": os.environ['host'],
        "port": os.environ['port'],
        "user": os.environ['user'],
        "password": os.environ['password'],
        "dbname": os.environ['database']
    }

    obj = DatabaseUtil(conn_details)

    schema_info = obj.schema_details("public")  # Fetch schema details for the 'public' schema

    # Constructing the prompt query for the agent to generate the SQL query
    prompt = f"""
    You are an SQL analyst agent. Your task is to convert the user's natural language 
    query into Postgres SQL query that can be executed on the database. You are provided 
    with the user's original query and the schema details of the database, including
    table names, column names, data types, and sample data for each table so that 
    you can understand the structure of the database and generate an accurate SQL query.
    Unless user explicitly asks for specific number of rows, always limit the output to 10 rows.
    Note - Just generate the SQL query without any explanation or additional text because
    this query will be executed directly on the database. So, the output should be SQL
    ready to be executed without any modifications.  
    
    User's Original Query: {curated_question}

    Database Schema Details:
    {schema_info}
    
    """    

    state.prompt_query_context = prompt

    return state


# Generate SQL Query Node
def generate_sql(state: AgentSchema) -> AgentSchema:

    prompt = state.prompt_query_context

    llm = pick_llm("medium")  # Pick the appropriate LLM based on the level of the question

    generated_sql_query = llm.invoke(prompt).content  # Generate the SQL query using the LLM

    state.generated_sql_query = generated_sql_query

    return state


# Is safe Node
def is_safe_sql(state: AgentSchema) -> AgentSchema:

    sql_query = state.generated_sql_query

    llm = pick_llm("medium")  
    llm_judge = llm.with_structured_output(JudgeSchema)

    prompt = f"""
    You are an SQL Judge for data security. Your task is to determine whether the SQL query is 
    safe or not. The SQL query should only be used for data retrieval and should not modify the 
    database in any way. Neither the SQL query nor the prompt should contain any SQL commands that can modify the
    database, such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any other commands that can change
    the structure or content of the database. If the SQL query is safe, respond with 'Yes' otherwise respond with 
    'No'. Additionally, provide comments explaining your decision.
    Here's the SQL query to evaluate:
    {sql_query}"""

    response = llm_judge.invoke(prompt).model_dump()  # Get the structured output as a dictionary
    state.is_safe = response['answer']
    state.comments = response['comments']

    return state


def canceled_sql(state:AgentSchema) -> AgentSchema:
    
    comments=state.comments
   
    state.final_answer=f"The generated SQL query was deemed unsafe to execute. The reason provided by the judge is: {comments}. Therefore, the SQL query will not be executed."
   
    return state


# Execute SQL Query Node
def execute_sql(state: AgentSchema) -> AgentSchema:

    sql_query = state.generated_sql_query

    conn_details = {
        "host": os.environ['host'],
        "port": os.environ['port'],
        "user": os.environ['user'],
        "password": os.environ['password'],
        "dbname": os.environ['database']
    }

    obj = DatabaseUtil(conn_details)

    execution_result = obj.execute_sql(sql_query)  # Execute the SQL query on the database

    state.sql_query_execution_result = execution_result

    return state


# Represent the final answer Node
def represent_final_answer(state: AgentSchema) -> AgentSchema:

    execution_result = state.sql_query_execution_result
    curated_question = state.curated_ques

    llm = pick_llm("low")

    prompt = f"""
    You are an SQL analyst agent. Your task is to provide a final answer to the user based on the
    execution result of the SQL query and the user's original question. The final answer should be
    concise, clear, and directly address the user's query. Avoid including any SQL code or technical
    details in the final answer. The final answer should be in a user-friendly format that is easy to
    understand. If the execution result is empty or does not provide a clear answer to the user's question, explain this in the final answer. \n
    Here is the execution result: {execution_result} \n
    Here is the user's original question: {curated_question}
    """

    llm_response = llm.invoke(prompt).content  # Get the final answer from the LLM

    state.final_answer = llm_response
    state.messages = state.messages + [AIMessage(content=f"{llm_response}")]  # Append the final answer to the messages list

    return state







#==============================Builder Agent==================================
sql_agent_graph = StateGraph(AgentSchema)

# Nodes
sql_agent_graph.add_node(curate_ques,name="curate_ques")
sql_agent_graph.add_node(prompt_query_context,name="prompt_query_context")
sql_agent_graph.add_node(generate_sql,name="generate_sql")
sql_agent_graph.add_node(is_safe_sql,name="is_safe_sql")
sql_agent_graph.add_node(canceled_sql,name="canceled_sql")
sql_agent_graph.add_node(execute_sql,name="execute_sql")
sql_agent_graph.add_node(represent_final_answer,name="represent_final_answer")

# Edges
sql_agent_graph.add_edge(START, "curate_ques")
sql_agent_graph.add_edge("curate_ques", "prompt_query_context")
sql_agent_graph.add_edge("prompt_query_context", "generate_sql")
sql_agent_graph.add_edge("generate_sql", "is_safe_sql")

# Codintional Edge Function
def is_safe_sql_edge(state: AgentSchema) -> str:
    is_safe = state.is_safe

    if is_safe.lower() == "yes":
        return "execute_sql"

    else :
        return "canceled_sql"

sql_agent_graph.add_conditional_edges("is_safe_sql", is_safe_sql_edge,
                                      {
                                          "execute_sql": "execute_sql",
                                          "canceled_sql": "canceled_sql"
                                      })


sql_agent_graph.add_edge("canceled_sql", END)
sql_agent_graph.add_edge("execute_sql", "represent_final_answer")
sql_agent_graph.add_edge("represent_final_answer", END)



if __name__ == "__main__":
# Compile the graph
    sql_agent_graph = sql_agent_graph.compile()


# ========view graph========
    graph = sql_agent_graph.get_graph()

    png_data = graph.draw_mermaid_png()

    with open("sql_agent_graph.png", "wb") as f:
        f.write(png_data)

    print("Graph saved as sql_agent_graph.png")
#==========end Graph===

    input_schema = {
        "messages": [],
        "user_question": "What are the different types of Payment Methods we have in our database",
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": ""
    }

    # Execute the Graph
    sql_analyst_response = sql_agent_graph.invoke(input_schema)
    print(sql_analyst_response['messages'])  # Print the final output of the graph execution
    print("********************************")

    print(sql_analyst_response['generated_sql_query'])  # Print the generated SQL query

    print("********************************")

    print(sql_analyst_response['sql_query_execution_result'])  # Print the result of executing the SQL query

    print("********************************")

    print(sql_analyst_response['prompt_query_context'])  # Print the prompt query context