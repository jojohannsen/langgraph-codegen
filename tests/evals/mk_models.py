import openai
import anthropic
import sys


def get_openrouter_models():
    client = openai.OpenAI(base_url="https://openrouter.ai/api/v1")
    models = [model.id for model in client.models.list()]
    return models

def get_openai_models():
    client = openai.OpenAI()
    models = [model.id for model in client.models.list()]
    return models

def get_anthropic_models():
    client = anthropic.Anthropic()
    models = [model.id for model in client.models.list()]
    return models

if __name__ == "__main__":
    model_provider = sys.argv[1]
    if model_provider == "openrouter":
        models = get_openrouter_models()
    elif model_provider == "openai":
        models = get_openai_models()
    elif model_provider == "anthropic":
        models = get_anthropic_models()
    else:
        print(f"Unknown provider '{sys.argv[1]}', expected one of: openrouter, openai, anthropic")
        exit(0)

    for model in models:
        print(f"{model}")

