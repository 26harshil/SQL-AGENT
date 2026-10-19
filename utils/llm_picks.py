import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq

load_dotenv()


def pick_llm(level: str):
    """
    Picks the appropriate LLM based on task difficulty level.
    Uses Google Gemini (default: gemini-3.7-flash) as the primary, verified provider.
    Provides fallback to alternative providers (Groq, OpenRouter) if explicitly configured.

    Args:
        level (str): Task complexity tier: 'low', 'medium', or 'high'.

    Returns:
        BaseChatModel: An initialized LangChain chat model.
    """
    level_lower = level.lower().strip()
    google_key = os.getenv("GOOGLE_API_KEY")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

    if not google_key:
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")

        if openrouter_key:
            return ChatOpenAI(
                model=os.getenv("LLM_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free"),
                temperature=0,
                api_key=openrouter_key,
                base_url=os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
            )
        elif groq_key:
            return ChatGroq(
                model_name=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                temperature=0,
                groq_api_key=groq_key,
            )
        else:
            raise ValueError(
                "No valid LLM API key found. Please set GOOGLE_API_KEY in your .env file."
            )

    # Google Gemini is available and verified
    if level_lower == "low":
        # Fast query curation, classification, synthesis
        return ChatGoogleGenerativeAI(
            model=gemini_model,
            temperature=0,
            google_api_key=google_key,
        )

    elif level_lower == "medium":
        # SQL generation, AST safety judge with structured output
        return ChatGoogleGenerativeAI(
            model=gemini_model,
            temperature=0,
            google_api_key=google_key,
        )

    elif level_lower == "high":
        # Complex multi-step reasoning
        return ChatGoogleGenerativeAI(
            model=gemini_model,
            temperature=0,
            google_api_key=google_key,
        )

    else:
        raise ValueError(
            f"Invalid level: '{level}'. Choose 'low', 'medium', or 'high'."
        )


if __name__ == "__main__":
    test_llm = pick_llm("low")
    res = test_llm.invoke("Say hello in one word.")
    print("Test LLM output:", res.content)