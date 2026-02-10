"""
Node functions for Exercise 1 graph.
This file contains implementations of the node functions specified in the graph.
"""

from typing import Optional, Dict, Any
from langchain_core.runnables.config import RunnableConfig
from state_code import Exercise_1_State
from lgcodegen_llm import node_chat_model

def human_display(val):
    print(val)

# Node Function
def compliment(state: Exercise_1_State, *, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    # reads: name
    # writes: compliment_text
    name = state.name
    
    # Create the LLM for generating the compliment
    llm = node_chat_model()
    
    # Generate a prompt for the compliment
    compliment_prompt = f"""Generate a warm and personalized compliment for {name}.
    The compliment should use their name and make them feel special.
    Keep it concise, positive, and genuine."""
    
    # Generate the compliment using the LLM
    response = llm.invoke(compliment_prompt)
    compliment_text = response.content
    
    # Display the compliment to the user
    human_display(compliment_text)
    
    # Return the updated state
    return {"compliment_text": compliment_text}