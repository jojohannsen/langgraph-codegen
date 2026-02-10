from llm_cache import make_llm

def node_chat_model():
    return make_llm("anthropic", "claude-sonnet-4-20250514")