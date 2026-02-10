from typing import Optional, Dict, Any
from state_code import State
from langchain_core.runnables.config import RunnableConfig
from lgcodegen_llm import node_chat_model
import random

def human_display(val):
    print(val)

# Node Function
def llm_call_generator(state: State, *, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    # reads: topic
    # writes: joke
    topic = state.topic
    
    # Create LLM and generate the joke
    llm = node_chat_model()
    
    # Use the generation prompt as specified
    generation_prompt = f"""Generate a joke about: {topic}."""
    
    # Invoke the LLM
    msg = llm.invoke(generation_prompt)
    joke = msg.content
    
    # Display the joke to the human
    human_display(joke)
    
    # Return updates to state
    return {"joke": joke}

# Node Function
def llm_call_evaluator(state: State, *, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    # reads: joke
    # writes: is_funny
    joke = state.joke
    
    # Create LLM for evaluation
    llm = node_chat_model()
    
    # Use the generation prompt as specified
    generation_prompt = f"""Is this joke funny? Decide randomly.
    
    Joke: {joke}"""
    
    # Instead of using LLM for this random decision, we directly implement the 50% randomness
    is_funny = random.choice([True, False])
    
    # Return updates to state
    return {"is_funny": is_funny}

# Routing Function
def route_joke(state: State) -> str:
    # reads: is_funny
    # routes to: llm_call_generator, END
    is_funny = state.is_funny
    
    # For demonstration, let's route based on the funny evaluation
    # If the joke is funny, end the graph
    # If the joke isn't funny, generate a new joke
    if is_funny:
        return "END"
    else:
        return "llm_call_generator"