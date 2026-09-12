from langchain_openai import ChatOpenAI


def pick_llm(level: str):
    """
    Picks the appropriate LLM based on the level of the question.

    Args:
        level (str): The level of the question, can be "low", "medium", or "high".

    Returns:
        ChatOpenAI: The LLM instance to be used.
    """
    if level.lower() == "low":
        # llm = ChatAnthropic(model_name="claude-haiku-4-5", temperature=0)
        llm = ChatOpenAI(model_name="gpt-5.6-luna", temperature=0,model_kwargs={
        "reasoning_effort": "none"
        })
    elif level.lower() == "medium":
        llm = ChatOpenAI(model_name="gpt-5.6-terra", temperature=0,model_kwargs={
        "reasoning_effort": "none"
    })
    elif level.lower() == "high":
        llm = ChatOpenAI(model_name="gpt-5.6-sol", temperature=0,model_kwargs={
        "reasoning_effort": "none"
    })
   
    else:
        raise ValueError(f"Unsupported level: {level}")

    return llm

if __name__ == "__main__":
    llm_obj = pick_llm("low")  
    print(llm_obj.invoke("What is the capital of India?"))