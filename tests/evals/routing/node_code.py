from state_code import State
from typing import Optional
from langchain_core.runnables.config import RunnableConfig
from lgcodegen_llm import node_chat_model
from human_input import human_text_input, human_yesno_input

def human_display(val):
    print(val)

# Node Function
def llm_call_router(state: State, *, config: Optional[RunnableConfig] = None):
    # reads: input
    # writes: (no direct writes, but output used for routing)
    input_text = state.input
    
    # Create the LLM model
    llm = node_chat_model()
    
    # Prepare the prompt for the LLM
    prompt = f"""Analyze the following input and determine if the user wants a story, joke, or poem:
    
Input: {input_text}

Respond with ONLY ONE of these exact words: 'story', 'joke', or 'poem'."""
    
    # Invoke the LLM
    result = llm.invoke(prompt)
    
    # No direct state updates, as this is used for routing
    return {}

# Node Function
def story(state: State, *, config: Optional[RunnableConfig] = None):
    # reads: input
    # writes: (no specified state fields to write)
    input_text = state.input
    
    # Create the LLM model
    llm = node_chat_model()
    
    # Prepare the prompt for the LLM
    prompt = f"""Generate a complete story based on the following topic:
    
Topic: {input_text}

Please create an engaging, well-structured story with a beginning, middle, and end."""
    
    # Invoke the LLM
    result = llm.invoke(prompt)
    
    # Display the generated story to the user
    human_display(f"Here's your story:\n\n{result.content}")
    
    return {}

# Node Function
def joke(state: State, *, config: Optional[RunnableConfig] = None):
    # reads: input
    # writes: (no specified state fields to write)
    input_text = state.input
    
    # Create the LLM model
    llm = node_chat_model()
    
    # Prepare the prompt for the LLM
    prompt = f"""Generate a joke based on the following topic:
    
Topic: {input_text}

Please create a humorous joke that is appropriate and entertaining."""
    
    # Invoke the LLM
    result = llm.invoke(prompt)
    
    # Display the generated joke to the user
    human_display(f"Here's your joke:\n\n{result.content}")
    
    return {}

# Node Function
def poem(state: State, *, config: Optional[RunnableConfig] = None):
    # reads: input
    # writes: (no specified state fields to write)
    input_text = state.input
    
    # Create the LLM model
    llm = node_chat_model()
    
    # Prepare the prompt for the LLM
    prompt = f"""Generate a poem based on the following topic:
    
Topic: {input_text}

Please create a beautiful, thoughtful poem with appropriate structure and imagery."""
    
    # Invoke the LLM
    result = llm.invoke(prompt)
    
    # Display the generated poem to the user
    human_display(f"Here's your poem:\n\n{result.content}")
    
    return {}

# Routing Function
def route_decision(state: State):
    # reads: input
    # routes to: story, joke, poem
    input_text = state.input
    
    # Create the LLM model
    llm = node_chat_model()
    
    # Prepare the prompt for the LLM
    prompt = f"""Analyze the following input and determine if the user wants a story, joke, or poem:
    
Input: {input_text}

Respond with ONLY ONE of these exact words: 'story', 'joke', or 'poem'."""
    
    # Invoke the LLM
    result = llm.invoke(prompt)
    
    # Clean the result to ensure we get a valid return value
    content = result.content.strip().lower()
    
    if "story" in content:
        return "story"
    elif "joke" in content:
        return "joke"
    elif "poem" in content:
        return "poem"
    else:
        # Default to story if unclear
        return "story"