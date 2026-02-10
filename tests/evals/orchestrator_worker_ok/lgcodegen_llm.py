from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
import yaml
import os

# Load the configuration from yaml
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "orchestrator_worker.yaml")
    with open(config_path, "r") as file:
        return yaml.safe_load(file)

# Access worker LLMs configuration
def get_worker_llms_config():
    config = load_config()
    return config.get("node", {}).get("worker_llms", [])

# Default node chat model (for orchestrator and synthesizer)
def node_chat_model():
    config = load_config()
    provider = config.get("node", {}).get("llm_provider", "openai")
    model = config.get("node", {}).get("llm_model", "gpt-4.1")
    return make_llm(provider, model)

# Create a specific worker model by index
def worker_chat_model(worker_index=0):
    worker_llms = get_worker_llms_config()
    if not worker_llms or worker_index >= len(worker_llms):
        # Fallback to default if no worker LLMs are configured
        config = load_config()
        provider = config.get("node", {}).get("llm_provider", "openai")
        model = config.get("node", {}).get("llm_model", "gpt-4.1")
        return make_llm(provider, model)
    
    worker_config = worker_llms[worker_index]
    return make_llm(worker_config.get("provider"), worker_config.get("model"))

def make_llm(provider, model):
    if provider == "openai":
        return ChatOpenAI(model=model)
    elif provider == "anthropic":
        return ChatAnthropic(model=model)
    elif provider == "openrouter":
        return ChatOpenAI(base_url="https://openrouter.ai/api/v1", model=model)
    else:
        raise ValueError(f"Unexpected llm_provider, expected one of 'openai', 'anthropic', 'openrouter', got '{provider}'")
