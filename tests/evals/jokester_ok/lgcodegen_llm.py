from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

def node_chat_model():
    return make_llm("openai", "gpt-4.1")

def make_llm(provider, model):
    if provider == "openai":
        return ChatOpenAI(model=model)
    elif provider == "anthropic":
        return ChatAnthropic(model=model)
    elif provider == "openrouter":
        return ChatOpenAI(base_url="https://openrouter.ai/api/v1", model=model)
    else:
        raise ValueError(f"Unexpected llm_provider, expected one of 'openai', 'anthropic', 'openrouter', got 'openai'")
