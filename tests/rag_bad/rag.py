from typing import Dict, TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, Graph
from langchain_core.messages.tool import ToolMessage
from langchain_core.runnables.config import RunnableConfig
from operator import itemgetter
import random



# GENERATED CODE: mock graph state
from typing import Annotated, TypedDict

def add_str_to_list(a=None, b=""):
    return (a if a is not None else []) + ([b] if not isinstance(b, list) else b)

def add_int(a, b):
    return b+1 if a==b else b

class AgentState(TypedDict):
    nodes_visited: Annotated[list[str], add_str_to_list]
    counter: Annotated[int, add_int]

def initial_state_AgentState():
    return { 'nodes_visited': [], 'counter': 0 }


def format_docs(state: AgentState, *, config:Optional[RunnableConfig] = None):
    print(f'NODE: format_docs')
    return { 'nodes_visited': 'format_docs', 'counter': state['counter'] + 1 }

def format_prompt(state: AgentState, *, config:Optional[RunnableConfig] = None):
    print(f'NODE: format_prompt')
    return { 'nodes_visited': 'format_prompt', 'counter': state['counter'] + 1 }

def generate(state: AgentState, *, config:Optional[RunnableConfig] = None):
    print(f'NODE: generate')
    return { 'nodes_visited': 'generate', 'counter': state['counter'] + 1 }

def get_docs(state: AgentState, *, config:Optional[RunnableConfig] = None):
    print(f'NODE: get_docs')
    return { 'nodes_visited': 'get_docs', 'counter': state['counter'] + 1 }


# This graph has no conditional edges

# GENERATED code, creates compiled graph: rag
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
import sqlite3

checkpoint_saver = MemorySaver()
builder_rag = StateGraph(AgentState)
builder_rag.add_node('get_docs', get_docs)
builder_rag.add_node('format_docs', format_docs)
builder_rag.add_node('format_prompt', format_prompt)
builder_rag.add_node('generate', generate)
builder_rag.add_edge('START', 'get_docs')
builder_rag.add_edge('get_docs', 'format_docs')
builder_rag.add_edge('format_docs', 'format_prompt')
builder_rag.add_edge('format_prompt', 'generate')
builder_rag.add_edge('generate', END)

rag = builder_rag.compile(checkpointer=checkpoint_saver)


def random_one_or_zero():
    return random.choice([False, True])


from typing import TypedDict, Type, get_type_hints

def init_state(state_class) -> dict:
    """
    Initialize any TypedDict subclass by prompting user for string fields.
    Only processes str fields, preserving default empty values for other types.
    
    Args:
        state_class: The TypedDict class to instantiate
        
    Returns:
        dict: A dictionary with user-provided values for string fields
    """
    # Get the type hints to identify string fields
    try:
        type_hints = get_type_hints(state_class)
    except TypeError:
        # Fallback if type hints cannot be retrieved
        type_hints = getattr(state_class, '__annotations__', {})
    
    # Initialize with empty values based on types
    state = {}
    for field, type_ in type_hints.items():
        # Check if it's a list type by looking at the type string
        is_list = 'list' in str(type_).lower()
        state[field] = [] if is_list else ''
    
    # Process each field
    print(f"Enter values for {state_class.__name__} fields (press Enter to skip):")
    for field, type_hint in type_hints.items():
        # Only process string fields
        if type_hint == str:
            user_input = input(f"{field}: ").strip()
            state[field] = user_input
    
    return state


if __name__ == "__main__":
    import sys
    
    # Create the graph
    workflow = rag
    config = RunnableConfig(configurable={"thread_id": "1"})
    for output in workflow.stream(initial_state_AgentState(), config=config):
        print(f"\n    {output}\n")
    print("DONE STREAMING, final state:")
    print(workflow.get_state(config))
