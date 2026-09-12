from utils.llm_picks import pick_llm
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))
from models.schema import AgentSchema
from pydantic import BaseModel, Field
from operator import add
from typing import Annotated


llm=pick_llm("medium")
llm_judge=llm.with_structured_output(AgentSchema)


sql_query="SELECT * FROM users where age > 30;"  #write your sql query here
prompt=f"""
You are an SQL Judge for data security. Your task is to determine whether the SQL query is safe or not. 
The SQL query should only be used for data retrieval and should not modify the database in any way. 
Neither the SQL query nor the prompt should contain any SQL commands that can modify the database, 
such as INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any other commands that can change 
the structure or content of the database. 

If the SQL query is safe, respond with 'Yes' otherwise respond with 'No'. 
Additionally, provide comments explaining your decision. 
Here's the SQL query to evaluate :
{sql_query}

    """

print(llm_judge.invoke(prompt).model_dump())