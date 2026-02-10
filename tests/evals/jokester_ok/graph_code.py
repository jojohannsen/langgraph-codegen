"""
This file was generated using ['claude-3-7-sonnet-latest']
"""
from typing import Dict, Any
import uuid

from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.runnables.config import RunnableConfig

# Import the state class
from state_code import JokesterState

# Import the node functions
from node_code import get_joke_topic, tell_joke, ask_for_another

# Routing Functions
def tell_another(state: JokesterState) -> str:
    """
    Determines whether to start another joke or end the conversation based on user's input.
    
    Args:
        state: The current JokesterState containing the wants_another field
        
    Returns:
        Either 'get_joke_topic' to start a new joke or 'END' to end the conversation
    """
    if state.wants_another is True:
        return 'get_joke_topic'
    else:
        return 'END'

def make_builder():
    """
    Creates and returns a StateGraph builder for the Jokester application.
    
    Returns:
        A configured StateGraph builder
    """
    builder = StateGraph(JokesterState)

    # Add node functions
    builder.add_node('get_joke_topic', get_joke_topic)
    builder.add_node('tell_joke', tell_joke)
    builder.add_node('ask_for_another', ask_for_another)

    # Add edges for execution flow
    builder.add_edge(START, 'get_joke_topic')
    builder.add_edge('get_joke_topic', 'tell_joke')
    builder.add_edge('tell_joke', 'ask_for_another')

    # Conditional routing from ask_for_another node
    conditional_edges = {'get_joke_topic': 'get_joke_topic', 'END': END}
    builder.add_conditional_edges('ask_for_another', tell_another, conditional_edges)
    
    return builder

if __name__ == "__main__":
    # Create the graph with SQLite checkpointing
    with SqliteSaver.from_conn_string("jokester_graph.db") as checkpointer:
        builder = make_builder()
        jokester_graph = builder.compile(checkpointer=checkpointer)
        
        # Create a unique thread ID for this run
        thread_id = str(uuid.uuid4())
        config = RunnableConfig(configurable={"thread_id": thread_id})
        
        # Run the graph and stream outputs
        print("\n🤖 Jokester Bot Started 🤖\n")
        for output in jokester_graph.stream(JokesterState(), config=config):
            print(f"\n    {output}\n")
            
        print("\nFinal state:")
        state = jokester_graph.get_state(config)
        for k, v in state.values.items():
            print(f"  {k}: {v}")