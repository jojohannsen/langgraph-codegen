from pathlib import Path
import yaml
from mk_utils import mk_agent, get_single_prompt, OpenRouterAgent, extract_python_code, get_config, prepare_working_folder

def generate_node_code(graph_name, graph_spec):
    """Generate node code from graph spec, state spec, state code, and node spec using LLM"""
    print(f"generate_node_code called with graph_name='{graph_name}'", flush=True)
    
    # Prepare working folder and get config
    print("Preparing working folder and getting config...", flush=True)
    try:
        prepare_working_folder(graph_name)
        config = get_config(graph_name)
        print("Working folder prepared and config loaded", flush=True)
    except Exception as e:
        print(f"ERROR preparing working folder: {e}", flush=True)
        raise
    
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
    
    # Check if state_code.py exists
    print("Checking if state_code.py exists...", flush=True)
    state_code_file = Path(graph_name) / "state_code.py"
    if not state_code_file.exists():
        print("ERROR: state_code.py does not exist", flush=True)
        raise ValueError("state_code.py does not exist. Generate state code first.")
    
    # Read state code
    print("Reading state code...", flush=True)
    try:
        with open(state_code_file, "r") as f:
            state_code = f.read()
        print(f"Successfully read state code ({len(state_code)} characters)", flush=True)
    except Exception as e:
        print(f"ERROR reading state code: {e}", flush=True)
        raise
    
    # Check if node-spec.md exists
    print("Checking if node-spec.md exists...", flush=True)
    node_spec_file = Path(graph_name) / "node-spec.md"
    if not node_spec_file.exists():
        print("ERROR: node-spec.md does not exist", flush=True)
        raise ValueError("node-spec.md does not exist. Generate node spec first.")
    
    # Read node spec
    print("Reading node spec...", flush=True)
    try:
        with open(node_spec_file, "r") as f:
            node_spec = f.read()
        print(f"Successfully read node spec ({len(node_spec)} characters)", flush=True)
    except Exception as e:
        print(f"ERROR reading node spec: {e}", flush=True)
        raise
    
    # Get LLM configuration for code generation (using 'code' section like mk_node_code.py)
    print("Getting LLM configuration...", flush=True)
    code_config = config.get('code', {})
    agent_library = code_config.get('agent_library', 'agno')
    llm_provider = code_config.get('llm_provider', 'anthropic')
    llm_model = code_config.get('llm_model', 'claude-3-sonnet-20240229')
    print(f"LLM config: library={agent_library}, provider={llm_provider}, model={llm_model}", flush=True)
    
    # Get prompts from config
    print("Getting prompts from config...", flush=True)
    try:
        graph_notation = get_single_prompt(config, 'graph_notation')
        print(f"Got graph_notation: {graph_notation is not None}", flush=True)
        
        human_input_example = get_single_prompt(config, 'human_input_example')
        print(f"Got human_input_example: {human_input_example is not None}", flush=True)
        
        node_code_prompt = get_single_prompt(config, 'node_code')
        print(f"Got node_code_prompt: {node_code_prompt is not None}", flush=True)
        
        node_code_example = get_single_prompt(config, 'node_code_example')
        print(f"Got node_code_example: {node_code_example is not None}", flush=True)
        
        if node_code_prompt and graph_notation:
            prompt = node_code_prompt.format(
                graph_notation=graph_notation,
                graph_name=graph_name,
                graph_spec=graph_spec,
                state_spec=state_spec,
                state_code=state_code,
                node_spec=node_spec,
                model_name=llm_model,
                human_input_example=human_input_example,
                node_code_example=node_code_example
            )
            print("Prompts formatted successfully", flush=True)
        else:
            print("ERROR: Could not retrieve required prompts", flush=True)
            raise ValueError("Could not retrieve required prompts from configuration")
    except Exception as e:
        print(f"ERROR getting prompts: {e}", flush=True)
        raise ValueError(f"Error getting prompts: {str(e)}")
    
    # Create agent (using system_prompt like mk_node_code.py)
    print("Creating agent...", flush=True)
    try:
        agent = mk_agent(graph_name, llm_provider, llm_model, agent_library, system_prompt=prompt)
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
        node_code_file = Path(graph_name) / "node_code.py"
        
        if isinstance(agent, OpenRouterAgent):
            print("Processing OpenRouterAgent result", flush=True)
            code = extract_python_code(result.choices[0].message.content)
            # Write to file
            node_code_file.parent.mkdir(parents=True, exist_ok=True)
            with open(node_code_file, "w") as f:
                f.write(code)
            print("OpenRouterAgent content written to file", flush=True)
            content = code
        else:
            print("Processing Agno agent result", flush=True)
            # Agno agent writes file directly
            if node_code_file.exists():
                with open(node_code_file, "r") as f:
                    content = f.read()
                print("Agno agent content read from file", flush=True)
            else:
                print("ERROR: Node code file was not created by Agno agent", flush=True)
                raise ValueError("Node code file was not created")
        
        # Verify file exists and is not empty
        if not node_code_file.exists():
            print("ERROR: node_code.py does not exist", flush=True)
            raise ValueError("node_code.py was not created")
        
        if node_code_file.stat().st_size == 0:
            print("ERROR: node_code.py is empty", flush=True)
            raise ValueError("node_code.py is empty")
            
    except Exception as e:
        print(f"ERROR extracting content: {e}", flush=True)
        raise
    
    print(f"Returning content ({len(content)} characters)", flush=True)
    return content