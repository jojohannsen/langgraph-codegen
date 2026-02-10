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
    if b == 0: return 0
    return b+1 if a==b else b

class State(TypedDict):
    nodes_visited: Annotated[list[str], add_str_to_list]
    counter: Annotated[int, add_int]

def initial_state_State():
    return { 'nodes_visited': [], 'counter': 0 }


def generate_joke(state: State, *, config:Optional[RunnableConfig] = None):
    print(f'NODE: generate_joke')
    return { 'nodes_visited': 'generate_joke', 'counter': state['counter'] + 1 }

def improve_joke(state: State, *, config:Optional[RunnableConfig] = None):
    print(f'NODE: improve_joke')
    return { 'nodes_visited': 'improve_joke', 'counter': state['counter'] + 1 }

def polish_joke(state: State, *, config:Optional[RunnableConfig] = None):
    print(f'NODE: polish_joke')
    return { 'nodes_visited': 'polish_joke', 'counter': state['counter'] + 1 }


# GENERATED CODE -- used for graph simulation mode
def START((state: State) -> bool:
    result = random_one_or_zero()
    print(f'CONDITION: START(. Result: {result}')
    return result


def check_punchline_improve_joke(state: State) -> bool:
    result = random_one_or_zero()
    print(f'CONDITION: check_punchline_improve_joke. Result: {result}')
    return result


def check_punchline_END(state: State) -> bool:
    result = random_one_or_zero()
    print(f'CONDITION: check_punchline_END. Result: {result}')
    return result


# GENERATED code, creates compiled graph: x
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
import sqlite3

checkpoint_saver = MemorySaver()
builder_x = StateGraph(State)
builder_x.add_node('generate_joke', generate_joke)
builder_x.add_node('improve_joke', improve_joke)
builder_x.add_node('polish_joke', polish_joke)
def after_START(state: State):
    if START((state):
        return ')'
    return 'generate_joke'

START_conditional_edges = { ')': ')', 'generate_joke': 'generate_joke' }
builder_x.add_conditional_edges('START', after_START, START_conditional_edges)

def after_generate_joke(state: State):
    if check_punchline_improve_joke(state):
        return 'improve_joke'
    elif check_punchline_END(state):
        return 'END'
    return 'END'

generate_joke_conditional_edges = { 'improve_joke': 'improve_joke', 'END': END }
builder_x.add_conditional_edges('generate_joke', after_generate_joke, generate_joke_conditional_edges)

builder_x.add_edge('improve_joke', 'polish_joke')
builder_x.add_edge('polish_joke', END)

x = builder_x.compile(checkpointer=checkpoint_saver)


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
    workflow = x
    config = RunnableConfig(configurable={"thread_id": "1"})
    for output in workflow.stream(initial_state_State(), config=config):
        print(f"\n    {output}\n")
    print("DONE STREAMING, final state:")
    print(workflow.get_state(config))
