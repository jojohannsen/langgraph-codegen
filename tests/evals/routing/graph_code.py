from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from state_code import State
from node_code import llm_call_router, story, joke, poem

# Routing function for determining whether to generate a story, joke, or poem
def route_decision(state: State) -> str:
    """
    Routes based on the 'input' value in state, determining whether to generate 
    a story, joke, or poem.
    
    Args:
        state: Current state object containing the input
        
    Returns:
        String indicating next node: 'story', 'joke', or 'poem'
    """
    # This is a placeholder for the actual routing logic
    # In a real implementation, this would analyze the routing decision 
    # that was made by the llm_call_router node
    
    # Since the actual implementation depends on how llm_call_router sets up
    # the information for routing, we're using a simplified approach here.
    # The actual implementation would examine state to determine the right route.
    
    # For example, if llm_call_router had set a 'content_type' field:
    # return state.content_type
    
    # Or, if the router had made a determination based on analyzing the input:
    input_text = state.input.lower() if state.input else ""
    
    if "story" in input_text:
        return "story"
    elif "joke" in input_text:
        return "joke"
    elif "poem" in input_text:
        return "poem"
    else:
        # Default case if no clear determination can be made
        return "story"

def make_builder():
    """
    Builds and returns the state graph builder for the content generation system.
    """
    # Initialize the graph builder with our State class
    builder = StateGraph(State)
    
    # Add all node functions
    builder.add_node("llm_call_router", llm_call_router)
    builder.add_node("story", story)
    builder.add_node("joke", joke)
    builder.add_node("poem", poem)
    
    # Define the starting edge
    builder.add_edge(START, "llm_call_router")
    
    # Define conditional edges for routing
    conditional_edges = {
        "story": "story",
        "joke": "joke",
        "poem": "poem"
    }
    
    # Add conditional edges from the router node to content generation nodes
    builder.add_conditional_edges(
        "llm_call_router", 
        route_decision, 
        conditional_edges
    )
    
    # Add edges from content nodes to END
    builder.add_edge("story", END)
    builder.add_edge("joke", END)
    builder.add_edge("poem", END)
    
    return builder

# Create the graph function for compatibility
def make_graph():
    """
    Builds and returns the state graph for the content generation system.
    """
    checkpoint_saver = MemorySaver()
    builder = make_builder()
    return builder.compile(checkpointer=checkpoint_saver)

# Main graph instance
graph = make_graph()