from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
                    
def node_chat_model():
    """Create a chat model"""
    llm = CONFIG_NODE_CHAT_MODEL
    return llm
