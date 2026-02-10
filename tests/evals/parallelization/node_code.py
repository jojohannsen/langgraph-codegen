"""
Node functions for parallel content generation workflow
"""

from human_input import human_text_input
from lgcodegen_llm import node_chat_model
from state_code import State
from typing import Optional
from langchain_core.runnables.config import RunnableConfig

def human_display(val):
    print(val)

# Node Function
def get_topic(state: State, *, config: Optional[RunnableConfig] = None):
    # reads: (none)
    # writes: topic
    
    # Get topic from human input
    topic = human_text_input("Please provide a topic to generate a story, joke, and poem about.")
    
    return {"topic": topic}

# Node Function
def story(state: State, *, config: Optional[RunnableConfig] = None):
    # reads: topic
    # writes: story_text
    
    topic = state.topic
    
    # Create prompt for story generation
    story_prompt = f"""Write a short story about the provided topic: {topic}."""
    
    # Generate story using LLM
    llm = node_chat_model()
    msg = llm.invoke(story_prompt)
    
    return {"story_text": msg.content}

# Node Function
def joke(state: State, *, config: Optional[RunnableConfig] = None):
    # reads: topic
    # writes: joke_text
    
    topic = state.topic
    
    # Create prompt for joke generation
    joke_prompt = f"""Write a joke about the provided topic: {topic}."""
    
    # Generate joke using LLM
    llm = node_chat_model()
    msg = llm.invoke(joke_prompt)
    
    return {"joke_text": msg.content}

# Node Function
def poem(state: State, *, config: Optional[RunnableConfig] = None):
    # reads: topic
    # writes: poem_text
    
    topic = state.topic
    
    # Create prompt for poem generation
    poem_prompt = f"""Write a poem about the provided topic: {topic}."""
    
    # Generate poem using LLM
    llm = node_chat_model()
    msg = llm.invoke(poem_prompt)
    
    return {"poem_text": msg.content}

# Node Function
def aggregator(state: State, *, config: Optional[RunnableConfig] = None):
    # reads: story_text, joke_text, poem_text
    # writes: aggregated_result
    
    story_text = state.story_text
    joke_text = state.joke_text
    poem_text = state.poem_text
    
    # Combine all generated content
    aggregated_prompt = f"""Combine the generated story, joke, and poem into a single result.

Story:
{story_text}

Joke:
{joke_text}

Poem:
{poem_text}
"""
    
    # Generate combined result using LLM
    llm = node_chat_model()
    msg = llm.invoke(aggregated_prompt)
    
    # Display the aggregated result to the user
    human_display(msg.content)
    
    return {"aggregated_result": msg.content}