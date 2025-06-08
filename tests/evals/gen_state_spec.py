from pathlib import Path
import yaml
from mk_utils import parse_graph, validate_graph, mk_agent, get_single_prompt, OpenRouterAgent, prepare_working_folder, get_tools

def generate_state_spec(graph_name, graph_spec):
    """Generate state specification from graph spec using LLM"""
    print(f"generate_state_spec called with graph_name='{graph_name}'", flush=True)
    
    # Parse and validate graph
    print("Parsing graph...", flush=True)
    try:
        parsed_graph = parse_graph(graph_spec)
        print("Graph parsed successfully", flush=True)
    except Exception as e:
        print(f"ERROR parsing graph: {e}", flush=True)
        raise
    
    print("Validating graph...", flush=True)
    try:
        validated_graph = validate_graph(parsed_graph)
        print("Graph validated successfully", flush=True)
    except Exception as e:
        print(f"ERROR validating graph: {e}", flush=True)
        raise
    
    if not validated_graph.is_valid:
        print(f"ERROR: Invalid graph: {validated_graph.validation_messages}", flush=True)
        raise ValueError(f"Invalid graph: {validated_graph.validation_messages}")
    
    # Prepare working folder and get config
    print("Preparing working folder and getting config...", flush=True)
    try:
        config = prepare_working_folder(graph_name)
        print("Working folder prepared and config loaded", flush=True)
    except Exception as e:
        print(f"ERROR preparing working folder: {e}", flush=True)
        raise
    
    # Get LLM configuration for spec generation
    print("Getting LLM configuration...", flush=True)
    agent_library, llm_provider, llm_model = get_tools(config, 'spec')
    
    # Get prompts from config
    print("Getting prompts from config...", flush=True)
    try:
        state_spec_prompt = get_single_prompt(config, 'state_spec')
        print(f"Got state_spec_prompt: {state_spec_prompt is not None}", flush=True)
        
        graph_notation = get_single_prompt(config, 'graph_notation')
        print(f"Got graph_notation: {graph_notation is not None}", flush=True)
        
        if state_spec_prompt and graph_notation:
            state_spec_prompt = state_spec_prompt.format(
                graph_notation=graph_notation,
                model_name=llm_model
            )
            print("Prompts formatted successfully", flush=True)
        else:
            print("ERROR: Could not retrieve required prompts", flush=True)
            raise ValueError("Could not retrieve required prompts from configuration")
    except Exception as e:
        print(f"ERROR getting prompts: {e}", flush=True)
        raise ValueError(f"Error getting prompts: {str(e)}")
    
    # Create agent
    print("Creating agent...", flush=True)
    try:
        system_prompt = "You are a technical writer, creating design documents for the development team. You write in markdown."
        agent = mk_agent(graph_name, llm_provider, llm_model, agent_library, system_prompt=system_prompt)
        print(f"Agent created successfully: {type(agent)}", flush=True)
    except Exception as e:
        print(f"ERROR creating agent: {e}", flush=True)
        raise ValueError(f"Error creating agent: {str(e)}")
    
    # Generate human request
    human_request = f"""Here's the graph specification:
<GRAPH_SPEC>
{graph_spec}
</GRAPH_SPEC>

Please write the State class specification in markdown, and save it to 'state-spec.md'
"""
    print("Generated human request", flush=True)
    
    # Run agent
    print("Running agent...", flush=True)
    try:
        result = agent.run(state_spec_prompt + "\n\n" + human_request)
        print(f"Agent run completed: {type(result)}", flush=True)
    except Exception as e:
        print(f"ERROR running agent: {e}", flush=True)
        raise
    
    # Extract content based on agent type
    print("Extracting content based on agent type...", flush=True)
    try:
        if isinstance(agent, OpenRouterAgent):
            print("Processing OpenRouterAgent result", flush=True)
            content = result.choices[0].message.content
            # Write to file
            state_spec_file = Path(graph_name) / "state-spec.md"
            state_spec_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_spec_file, "w") as f:
                f.write(content)
            print("OpenRouterAgent content written to file", flush=True)
        else:
            print("Processing Agno agent result", flush=True)
            # Agno agent writes file directly
            state_spec_file = Path(graph_name) / "state-spec.md"
            if state_spec_file.exists():
                with open(state_spec_file, "r") as f:
                    content = f.read()
                print("Agno agent content read from file", flush=True)
            else:
                print("ERROR: State spec file was not created by Agno agent", flush=True)
                raise ValueError("State spec file was not created")
    except Exception as e:
        print(f"ERROR extracting content: {e}", flush=True)
        raise
    
    print(f"Returning content ({len(content)} characters)", flush=True)
    return content