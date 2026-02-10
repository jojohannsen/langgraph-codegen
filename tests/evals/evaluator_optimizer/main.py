"""
main.py - Main entry point for the joke generator application

This script runs the joke generator workflow, which creates jokes based on user-provided topics
and evaluates whether they are funny.
"""

from langchain_core.runnables.config import RunnableConfig
from graph_code import make_builder
from state_code import State
from human_input import init_human_input, init_graph_state
import questionary
import uuid
import sys
from langgraph.checkpoint.sqlite import SqliteSaver

if __name__ == "__main__":
    # Allow command line specification of human input style using either "--human interrupt" or "--human questionary"
    init_human_input(sys.argv)
    
    # Create the graph, use actual graph name for the db
    with SqliteSaver.from_conn_string("joke_generator.db") as checkpointer:
        # Create the graph builder
        builder = make_builder()
        joke_graph = builder.compile(checkpointer=checkpointer)
        workflow = joke_graph
        
        # Generate a unique thread ID for this execution
        thread_id = str(uuid.uuid4())
        config = RunnableConfig(configurable={"thread_id": thread_id})
        
        # Get the initial topic from the user
        topic = questionary.text("Please enter a topic for the joke:").ask()
        
        # Initialize the state with the provided topic
        initial_state = State(topic=topic)
        
        # Stream through the graph execution, initialize text and resume_value
        text = None
        resume_value = None
        
        while True:
            # Initialize the graph state
            stream_input = init_graph_state(initial_state, text, resume_value)
            
            for output in joke_graph.stream(stream_input, config=config):
                # Print the output in a clear format
                if isinstance(output, dict):
                    for node_name, node_output in output.items():
                        print(f"\n[{node_name}] Output:")
                        print(f"{node_output}\n")
                if "__interrupt__" in output:
                    # Extract the interrupt value
                    interrupt_obj = output["__interrupt__"][0]
                    interrupt_value = interrupt_obj.value
                    print(f"Interrupt received: {interrupt_value}")
                    if 'text' in interrupt_value:
                        text = questionary.text(interrupt_value['text']).ask()
                        resume_value = text
                    elif 'confirm' in interrupt_value:
                        yn_answer = questionary.confirm(interrupt_value['confirm']).ask()
                        resume_value = yn_answer
                    break  # Break the inner loop to restart with new input
            else:
                # If we complete the stream without an interrupt, we're done
                break  # Break the outer loop
                
        print("DONE STREAMING, final state:")
        state = workflow.get_state(config)
        for k, v in state.values.items():
            print(f"  {k}: {v}")