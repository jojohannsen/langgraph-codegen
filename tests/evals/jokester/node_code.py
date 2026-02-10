# Node Functions for JokesterState Graph
# Generated from node specification

from typing import Optional
from langchain_core.runnables.config import RunnableConfig
from state_code import JokesterState
from lgcodegen_llm import node_chat_model
from human_input import human_text_input, human_yesno_input


def human_display(val):
    print(val)


# Node Function
def get_joke_topic(state: JokesterState, *, config: Optional[RunnableConfig] = None):
    # reads: 
    # writes: topic
    
    topic = human_text_input("What topic would you like to hear a joke about?")
    
    return {"topic": topic}


# Node Function
def tell_joke(state: JokesterState, *, config: Optional[RunnableConfig] = None):
    # reads: topic
    # writes: joke
    
    topic = state.topic
    
    generation_prompt = f"""Generate a funny joke about the topic: {topic}"""
    
    llm = node_chat_model()
    msg = llm.invoke(generation_prompt)
    
    # Display the joke to the user
    human_display(msg.content)
    
    return {"joke": msg.content}


# Node Function
def ask_for_another(state: JokesterState, *, config: Optional[RunnableConfig] = None):
    # reads: 
    # writes: wants_another_joke
    
    wants_another = human_yesno_input("Would you like to hear another joke? (yes/no)")
    
    return {"wants_another_joke": wants_another}


# Routing Function
def tell_another(state: JokesterState):
    # reads: wants_another_joke
    # routes to: get_joke_topic, END
    
    wants_another_joke = state.wants_another_joke
    
    if wants_another_joke:
        return 'get_joke_topic'
    else:
        return 'END'