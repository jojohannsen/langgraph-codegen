"""
Main application file for Exercise 1.

This file runs the graph that takes a name as input and generates a compliment.
"""

from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from graph_code import make_builder
from state_code import Exercise_1_State
from human_input import init_human_input, init_graph_state
import questionary
import uuid
import sys

if __name__ == "__main__":
    # Allow command line specification of human input style
    init_human_input(sys.argv)
    
    # Create the graph, use actual graph name for the db
    with SqliteSaver.from_conn_string("exercise_1.db") as checkpointer:
        builder = make_builder()
        compliment_graph = builder.compile(checkpointer=checkpointer)
        workflow = compliment_graph
        thread_id = str(uuid.uuid4())
        config = RunnableConfig(configurable={"thread_id": thread_id})
        
        # Get the name input from the user
        name = questionary.text("Please enter a name:").ask()
        
        # Initialize state with the name
        initial_state = Exercise_1_State(name=name)
        
        # Stream through the graph execution
        text = None
        resume_value = None
        
        while True:
            # Initialize graph state with appropriate parameters
            stream_input = init_graph_state(initial_state, text, resume_value)
            
            for output in compliment_graph.stream(stream_input, config=config):
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