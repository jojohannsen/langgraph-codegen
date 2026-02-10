from langchain_core.runnables.config import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from graph_code import make_builder
from human_input import init_human_input, init_graph_state
from state_code import JokesterState
import questionary
import uuid
import sys
    
if __name__ == "__main__":
    # allow command line specification of human input style using either "--human interrupt" or "--human questionary"
    init_human_input(sys.argv)
    # Create the graph, use actual graph name for the db
    with SqliteSaver.from_conn_string("jokester.db") as checkpointer:
        builder = make_builder()
        jokester_graph = builder.compile(checkpointer=checkpointer)
        workflow = jokester_graph
        thread_id = str(uuid.uuid4())
        config = RunnableConfig(configurable={"thread_id": thread_id})
        # Since our graph doesn't require initial input values, we start with an empty state
        initial_state = JokesterState()
       
        # Stream through the graph execution, initialize text and resume_value
        text = None
        resume_value = None
        while True:
            # IMPORTANT:  include this exactly as shown, use init_graph_state with these parameters
            stream_input = init_graph_state(initial_state, text, resume_value)
            
            for output in jokester_graph.stream(stream_input, config=config):
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
                    break  # Break the inner loop to restart with new topic
            else:
                # If we complete the stream without an interrupt, we're done
                break  # Break the outer loop
                
        print("DONE STREAMING, final state:")
        state = workflow.get_state(config)
        for k,v in state.values.items():
            print(f"  {k}: {v}")