from pathlib import Path
import yaml
from mk_utils import mk_agent, get_single_prompt, OpenRouterAgent, extract_python_code, get_config, get_file

def generate_main(graph_name, graph_spec):
    """Generate main code from graph spec and all dependencies using LLM"""
    print(f"generate_main called with graph_name='{graph_name}'", flush=True)
    
    # Get config
    print("Getting config...", flush=True)
    try:
        config = get_config(graph_name)
        print("Config loaded successfully", flush=True)
    except Exception as e:
        print(f"ERROR getting config: {e}", flush=True)
        raise
    
    # Check if state-spec.md exists
    print("Checking if state-spec.md exists...", flush=True)
    state_spec_file = Path(graph_name) / "state-spec.md"
    if not state_spec_file.exists():
        print("ERROR: state-spec.md does not exist", flush=True)
        raise ValueError("state-spec.md does not exist. Generate state spec first.")
    
    # Check if graph_code.py exists
    print("Checking if graph_code.py exists...", flush=True)
    graph_code_file = Path(graph_name) / "graph_code.py"
    if not graph_code_file.exists():
        print("ERROR: graph_code.py does not exist", flush=True)
        raise ValueError("graph_code.py does not exist. Generate graph code first.")
    
    # Read required files using get_file utility (like mk_main.py)
    print("Reading required files...", flush=True)
    try:
        state_spec = get_file(graph_name, "state", "spec")
        print(f"Successfully read state spec ({len(state_spec)} characters)", flush=True)
        
        state_code = get_file(graph_name, "state", "code")
        print(f"Successfully read state code ({len(state_code)} characters)", flush=True)
        
        node_spec = get_file(graph_name, "node", "spec")
        print(f"Successfully read node spec ({len(node_spec)} characters)", flush=True)
        
        graph_code = get_file(graph_name, "graph", "code")
        print(f"Successfully read graph code ({len(graph_code)} characters)", flush=True)
        
    except Exception as e:
        print(f"ERROR reading required files: {e}", flush=True)
        raise ValueError(f"Error reading required files: {str(e)}")
    
    # Get LLM configuration for code generation (using 'code' section like mk_main.py)
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
        
        main_code_prompt = get_single_prompt(config, 'main_code')
        print(f"Got main_code_prompt: {main_code_prompt is not None}", flush=True)
        
        if main_code_prompt and graph_notation:
            # Note: mk_main.py has a bug with [config['code']['llm_model']] - fixing it here
            prompt = main_code_prompt.format(
                graph_notation=graph_notation,
                graph_name=graph_name,
                graph_spec=graph_spec,
                state_spec=state_spec,
                state_code=state_code,
                node_spec=node_spec,
                graph_code=graph_code,
                model_name=llm_model  # Fixed: removed the list brackets from original
            )
            print("Prompts formatted successfully", flush=True)
        else:
            print("ERROR: Could not retrieve required prompts", flush=True)
            raise ValueError("Could not retrieve required prompts from configuration")
    except Exception as e:
        print(f"ERROR getting prompts: {e}", flush=True)
        raise ValueError(f"Error getting prompts: {str(e)}")
    
    # Create agent (using system_prompt like mk_main.py)
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
        main_code_file = Path(graph_name) / "main.py"
        
        if isinstance(agent, OpenRouterAgent):
            print("Processing OpenRouterAgent result", flush=True)
            code = extract_python_code(result.choices[0].message.content)
            # Write to file
            main_code_file.parent.mkdir(parents=True, exist_ok=True)
            with open(main_code_file, "w") as f:
                f.write(code)
            print("OpenRouterAgent content written to file", flush=True)
            content = code
        else:
            print("Processing Agno agent result", flush=True)
            # Agno agent writes file directly
            if main_code_file.exists():
                with open(main_code_file, "r") as f:
                    content = f.read()
                print("Agno agent content read from file", flush=True)
            else:
                print("ERROR: Main code file was not created by Agno agent", flush=True)
                raise ValueError("Main code file was not created")
        
        # Verify file exists and is not empty
        if not main_code_file.exists():
            print("ERROR: main.py does not exist", flush=True)
            raise ValueError("main.py was not created")
        
        if main_code_file.stat().st_size == 0:
            print("ERROR: main.py is empty", flush=True)
            raise ValueError("main.py is empty")
            
    except Exception as e:
        print(f"ERROR extracting content: {e}", flush=True)
        raise
    
    print(f"Returning content ({len(content)} characters)", flush=True)
    return content