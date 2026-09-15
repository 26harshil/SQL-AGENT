# import os
# from dotenv import load_dotenv
# from langchain_openai import ChatOpenAI

# load_dotenv()

# # Map OPENAI_API or OPENROUTER_APIKEY to OPENAI_API_KEY if not already set
# if not os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API"):
#     os.environ["OPENAI_API_KEY"] = os.environ["OPENAI_API"]


# def pick_llm(level: str):
#     """
#     Picks the appropriate LLM based on the level of the question.

#     Args:
#         level (str): The level of the question, can be "low", "medium", or "high".

#     Returns:
#         ChatOpenAI: The LLM instance to be used.
#     """
#     level_lower = level.lower().strip()
#     if level_lower == "low":
#         llm = ChatOpenAI(
#             model_name="gpt-5.6-luna",
#             temperature=0,
#             reasoning_effort="none",
#         )
#     elif level_lower == "medium":
#         llm = ChatOpenAI(
#             model_name="gpt-5.6-terra",
#             temperature=0,
#             reasoning_effort="none",
#         )
#     elif level_lower == "high":
#         llm = ChatOpenAI(
#             model_name="gpt-5.6-sol",
#             temperature=0,
#             reasoning_effort="none",
#         )
#     else:
#         raise ValueError(f"Unsupported level: {level}")

#     return llm


# if __name__ == "__main__":
#     llm_obj = pick_llm("low")
#     print(llm_obj.invoke("What is the capital of India?"))



import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

load_dotenv()


def pick_llm(level: str):
    level_lower = level.lower().strip()

    if level_lower == "low":
        # Groq: fast inference
        llm =ChatOpenAI(
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )

    elif level_lower == "medium":
        # Google Gemini: general-purpose reasoning
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.6-flash",
            temperature=0,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        )

    elif level_lower == "high":
        # OpenRouter: free model
        llm = ChatOpenAI(
            model="nvidia/nemotron-3-ultra-550b-a55b:free",
            temperature=0,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )

    else:
        raise ValueError(
            f"Invalid level: {level}. "
            "Choose low, medium, or high."
        )

    return llm