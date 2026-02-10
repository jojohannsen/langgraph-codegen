# Generated using ['claude-3-7-sonnet-latest']
from langgraph.graph import START, END, StateGraph
from state_code import State
from node_code import llm_call_generator, llm_call_evaluator

# Routing Functions
def route_joke(state: State) -> str:
    """
    Routes execution based on the outcome of joke evaluation.
    If the joke is funny, return to generate another joke.
    Otherwise, end the execution.
    
    Args:
        state: The current State object
        
    Returns:
        String indicating the next node ('llm_call_generator' or 'END')
    """
    if state.is_funny:
        return 'llm_call_generator'
    else:
        return 'END'

def make_graph():
    """
    Creates and returns the StateGraph for joke generation and evaluation.
    
    Returns:
        A compiled StateGraph instance
    """
    # Initialize the graph builder with our State class
    builder = StateGraph(State)
    
    # Add node functions
    builder.add_node('llm_call_generator', llm_call_generator)
    builder.add_node('llm_call_evaluator', llm_call_evaluator)
    
    # Add edges for execution flow
    builder.add_edge(START, 'llm_call_generator')
    builder.add_edge('llm_call_generator', 'llm_call_evaluator')
    
    # Add conditional edge for routing based on joke evaluation
    conditional_edges = {
        'llm_call_generator': 'llm_call_generator',
        'END': END
    }
    builder.add_conditional_edges('llm_call_evaluator', route_joke, conditional_edges)
    
    return builder

# Add make_builder function to conform to expected interface
def make_builder():
    """
    Alias for make_graph, creates and returns the StateGraph builder for joke generation and evaluation.
    
    Returns:
        A StateGraph builder instance
    """
    return make_graph()

# Create the graph instance
joke_graph = make_graph().compile()