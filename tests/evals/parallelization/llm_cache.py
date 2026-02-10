import os
import pickle
import hashlib
import functools
from typing import Callable, Any

def cache_llm_response(cache_dir: str = None):
    """
    Decorator for caching LLM responses.
    
    Args:
        cache_dir: Directory for storing cached responses. If None, will use 'llm_cache' 
                  in the current working directory
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(self, prompt: str, **kwargs):
            # Get provider and model from the instance
            provider = getattr(self, 'provider', 'unknown')
            model = getattr(self, 'model', 'unknown')
            
            # Get the directory where this file (llm_cache.py) is located
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Create cache in the current directory
            actual_cache_dir = os.path.join(current_dir, "llm_cache")
            os.makedirs(actual_cache_dir, exist_ok=True)
            
            # Create a unique hash based on provider, model, and prompt
            cache_key = f"{provider}_{model}_{prompt}"
            prompt_hash = hashlib.md5(cache_key.encode()).hexdigest()
            cache_file = os.path.join(actual_cache_dir, f"{prompt_hash}.pickle")
            
            # Check if we have a cached response
            if os.path.exists(cache_file):
                print(f"Cache hit for {provider}/{model} in {os.path.basename(os.path.dirname(actual_cache_dir))}: {prompt_hash}")
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            
            # If no cache exists, call the original function and cache the result
            response = func(self, prompt, **kwargs)
            print(f"Cache miss for {provider}/{model} in {os.path.basename(os.path.dirname(actual_cache_dir))}: {prompt_hash}")
            with open(cache_file, 'wb') as f:
                pickle.dump(response, f)
            
            return response
        return wrapper
    return decorator

class UnifiedLLM:
    """
    Unified LLM class that wraps ChatOpenAI, ChatAnthropic, etc.
    """
    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model
        
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(model=model)
        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            self._llm = ChatAnthropic(model=model)
        elif provider == "openrouter":
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(base_url="https://openrouter.ai/api/v1", model=model)
        else:
            raise ValueError(f"Unexpected provider, expected one of 'openai', 'anthropic', 'openrouter', got '{provider}'")
    
    @cache_llm_response()
    def invoke(self, prompt: str, **kwargs):
        """Invoke the LLM with caching"""
        return self._llm.invoke(prompt, **kwargs)
    

def make_llm(provider: str, model: str):
    return UnifiedLLM(provider, model)