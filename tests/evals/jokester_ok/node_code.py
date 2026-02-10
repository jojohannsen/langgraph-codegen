"""
Node functions for the Jokester graph application.
"""
from typing import Optional, Dict, Any
from langchain_core.runnables.config import RunnableConfig
import questionary
from lgcodegen_llm import node_chat_model
from state_code import JokesterState


def human_display(val):
    print(val)


# Node Function
def get_joke_topic(state: JokesterState, *, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """
    # reads: None
    # writes: topic
    Asks the user for a joke topic.
    """
    topic = questionary.text("Please provide a topic for a joke (e.g., cats, computers, physics).").ask()
    return {"topic": topic}


# Node Function
def tell_joke(state: JokesterState, *, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """
    # reads: topic
    # writes: joke
    Generates a joke based on the user's topic and displays it.
    """
    topic = state.topic
    
    # Create the prompt for joke generation
    generation_prompt = f"""Generate a joke based on the topic: {topic}"""
    
    # Get the LLM
    llm = node_chat_model()
    
    # Generate the joke
    msg = llm.invoke(generation_prompt)
    joke = msg.content
    
    # Display the joke to the user
    human_display(joke)
    
    return {"joke": joke}


# Node Function
def ask_for_another(state: JokesterState, *, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """
    # reads: joke (for context)
    # writes: wants_another
    Asks the user if they want another joke.
    """
    wants_another = questionary.confirm("Would you like to hear another joke? (yes/no)").ask()
    return {"wants_another": wants_another}


# Routing Function
def tell_another(state: JokesterState) -> str:
    """
    # reads: wants_another
    # routes_to: get_joke_topic, END
    Determines whether to start another joke or end the conversation based on user input.
    """
    if state.wants_another:
        return "get_joke_topic"
    else:
        return "END"