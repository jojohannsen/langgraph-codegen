from pathlib import Path
import yaml
from mk_utils import mk_agent, get_single_prompt, OpenRouterAgent, extract_python_code, get_config, get_tools

def generate_state_code(graph_name, graph_spec):
    """Generate state code from graph spec and state spec using LLM"""
    print(f"generate_state_code called with graph_name='{graph_name}'", flush=True)
    
    # Check if state-spec.md exists
    print("Checking if state-spec.md exists...", flush=True)
    state_spec_file = Path(graph_name) / "state-spec.md"
    if not state_spec_file.exists():
        print("ERROR: state-spec.md does not exist", flush=True)
        raise ValueError("state-spec.md does not exist. Generate state spec first.")
    
    # Read state spec
    print("Reading state spec...", flush=True)
    try:
        with open(state_spec_file, "r") as f:
            state_spec = f.read()
        print(f"Successfully read state spec ({len(state_spec)} characters)", flush=True)
    except Exception as e:
        print(f"ERROR reading state spec: {e}", flush=True)
        raise
    
    # Get config
    print("Getting config...", flush=True)
    try:
        config = get_config(graph_name)
        print("Config loaded successfully", flush=True)
    except Exception as e:
        print(f"ERROR getting config: {e}", flush=True)
        raise
    
    # Get LLM configuration for code generation
    print("Getting LLM configuration...", flush=True)
    agent_library, llm_provider, llm_model = get_tools(config, 'code')
    print(f"LLM config: library={agent_library}, provider={llm_provider}, model={llm_model}", flush=True)
    
    # Get prompts from config
    print("Getting prompts from config...", flush=True)
    try:
        graph_notation = get_single_prompt(config, 'graph_notation')
        print(f"Got graph_notation: {graph_notation is not None}", flush=True)
        
        state_code_prompt = get_single_prompt(config, 'state_code')
        print(f"Got state_code_prompt: {state_code_prompt is not None}", flush=True)
        
        state_code_example = get_single_prompt(config, 'state_code_example')
        print(f"Got state_code_example: {state_code_example is not None}", flush=True)
        
        if state_code_prompt and graph_notation:
            prompt = state_code_prompt.format(
                graph_notation=graph_notation,
                graph_spec=graph_spec,
                state_spec=state_spec,
                state_code_example=state_code_example,
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
        system_prompt = "You are an expert Python developer, and write code based on a design document."
        agent = mk_agent(graph_name, llm_provider, llm_model, agent_library, system_prompt=system_prompt)
        print(f"Agent created successfully: {type(agent)}", flush=True)
    except Exception as e:
        print(f"ERROR creating agent: {e}", flush=True)
        raise ValueError(f"Error creating agent: {str(e)}")
    
    # Run agent
    print("Running agent...", flush=True)
    try:
        result = agent.run(prompt)
        print(f"Agent run completed: {type(result)}", flush=True)
    except Exception as e:
        print(f"ERROR running agent: {e}", flush=True)
        raise
    
    # Extract content based on agent type
    print("Extracting content based on agent type...", flush=True)
    try:
        if isinstance(agent, OpenRouterAgent):
            print("Processing OpenRouterAgent result", flush=True)
            code = extract_python_code(result.choices[0].message.content)
            # Write to file
            state_code_file = Path(graph_name) / "state_code.py"
            state_code_file.parent.mkdir(parents=True, exist_ok=True)
            with open(state_code_file, "w") as f:
                f.write(code)
            print("OpenRouterAgent content written to file", flush=True)
            content = code
        else:
            print("Processing Agno agent result", flush=True)
            # Agno agent writes file directly
            state_code_file = Path(graph_name) / "state_code.py"
            if state_code_file.exists():
                with open(state_code_file, "r") as f:
                    content = f.read()
                print("Agno agent content read from file", flush=True)
            else:
                print("ERROR: State code file was not created by Agno agent", flush=True)
                raise ValueError("State code file was not created")
    except Exception as e:
        print(f"ERROR extracting content: {e}", flush=True)
        raise
    
    print(f"Returning content ({len(content)} characters)", flush=True)
    return content