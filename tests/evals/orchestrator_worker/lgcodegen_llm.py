from llm_cache import make_llm

def node_chat_model():
    return make_llm("openai", "gpt-4.1")