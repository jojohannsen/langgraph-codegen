"""
Graph builder code for parallel content generation workflow
Generated using ['claude-3-7-sonnet-latest']
"""

from langgraph.graph import START, END, StateGraph

# Import the State class
from state_code import State

# Import node functions
from node_code import get_topic, story, joke, poem, aggregator

def make_builder():
    """
    Creates a StateGraph builder for the parallel content generation workflow.
    
    Graph structure:
    State -> get_topic
    get_topic -> story, joke, poem (parallel execution)
    story, joke, poem -> aggregator
    aggregator -> END
    """
    # Initialize the StateGraph with our State class
    builder = StateGraph(State)
    
    # Add all node functions to the graph
    builder.add_node('get_topic', get_topic)
    builder.add_node('story', story)
    builder.add_node('joke', joke)
    builder.add_node('poem', poem)
    builder.add_node('aggregator', aggregator)
    
    # Define the edges for the execution flow
    builder.add_edge(START, 'get_topic')
    
    # Parallel execution from get_topic to story, joke, and poem
    builder.add_edge('get_topic', 'story')
    builder.add_edge('get_topic', 'joke')
    builder.add_edge('get_topic', 'poem')
    
    # All parallel nodes converge to aggregator
    builder.add_edge('story', 'aggregator')
    builder.add_edge('joke', 'aggregator')
    builder.add_edge('poem', 'aggregator')
    
    # Final edge from aggregator to END
    builder.add_edge('aggregator', END)
    
    return builder