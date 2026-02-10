"""
Generated using claude-3-7-sonnet-latest

This file contains the graph builder code for Exercise 1
based on the provided graph specification.
"""

from langgraph.graph import START, END, StateGraph
from state_code import Exercise_1_State
from node_code import compliment

def make_builder():
    """
    Creates and returns a StateGraph builder for the Exercise 1 graph.
    
    The graph flow is:
    START -> compliment -> END
    
    The compliment node takes a name from the state and generates a
    personalized compliment that is saved back to the state.
    """
    builder = StateGraph(Exercise_1_State)
    
    # Add node functions
    builder.add_node('compliment', compliment)
    
    # Add edges for execution flow
    builder.add_edge(START, 'compliment')
    builder.add_edge('compliment', END)
    
    return builder