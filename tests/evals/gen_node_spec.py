from pathlib import Path
import yaml
from mk_utils import mk_agent, get_single_prompt, OpenRouterAgent, get_config

def generate_node_spec(graph_name, graph_spec):
    """Generate node specification from graph spec and state spec using LLM"""
    print(f"generate_node_spec called with graph_name='{graph_name}'", flush=True)
    
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
    
    # Look for state code file (BaseModel class)
    print("Looking for state code file...", flush=True)
    try:
        py_files = [f.name for f in Path(graph_name).glob("*.py") if f.name != "__init__.py"]
        print(f"Found Python files: {py_files}", flush=True)
        
        state_code = ""
        for file in py_files:
            with open(Path(graph_name) / file, "r") as f:
                content = f.read()
                if "(BaseModel)" in content:
                    state_code = content
                    print(f"Found state code in {file}", flush=True)
                    break
        
        if not state_code:
            state_code = "State class has not yet been created."
            print("No state code with BaseModel found, using placeholder", flush=True)
    except Exception as e:
        print(f"ERROR reading state code: {e}", flush=True)
        state_code = "State class has not yet been created."
    
    # Get config
    print("Getting config...", flush=True)
    try:
        config = get_config(graph_name)
        print("Config loaded successfully", flush=True)
    except Exception as e:
        print(f"ERROR getting config: {e}", flush=True)
        raise
    
    # Get LLM configuration for spec generation (using 'spec' section like mk_node_spec.py)
    print("Getting LLM configuration...", flush=True)
    spec_config = config.get('spec', {})
    agent_library = spec_config.get('agent_library', 'agno')
    llm_provider = spec_config.get('llm_provider', 'anthropic')
    llm_model = spec_config.get('llm_model', 'claude-3-sonnet-20240229')
    print(f"LLM config: library={agent_library}, provider={llm_provider}, model={llm_model}", flush=True)
    
    # Get prompts from config
    print("Getting prompts from config...", flush=True)
    try:
        graph_notation = get_single_prompt(config, 'graph_notation')
        print(f"Got graph_notation: {graph_notation is not None}", flush=True)
        
        node_spec_prompt = get_single_prompt(config, 'node_spec')
        print(f"Got node_spec_prompt: {node_spec_prompt is not None}", flush=True)
        
        if node_spec_prompt and graph_notation:
            prompt = node_spec_prompt.format(
                graph_notation=graph_notation,
                graph_name=graph_name,
                graph_spec=graph_spec,
                state_spec=state_spec,
                state_code=state_code,
                model_name=llm_model
            )
            print("Prompts formatted successfully", flush=True)
        else:
            print("ERROR: Could not retrieve required prompts", flush=True)
            raise ValueError("Could not retrieve required prompts from configuration")
    except Exception as e:
        print(f"ERROR getting prompts: {e}", flush=True)
        raise ValueError(f"Error getting prompts: {str(e)}")
    
    # Create agent (using system_prompt like mk_node_spec.py)
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
        node_spec_file = Path(graph_name) / "node-spec.md"
        
        if isinstance(agent, OpenRouterAgent):
            print("Processing OpenRouterAgent result", flush=True)
            content = result.choices[0].message.content
            # Write to file
            node_spec_file.parent.mkdir(parents=True, exist_ok=True)
            with open(node_spec_file, "w") as f:
                f.write(content)
            print("OpenRouterAgent content written to file", flush=True)
        else:
            print("Processing Agno agent result", flush=True)
            # Agno agent writes file directly
            if node_spec_file.exists():
                with open(node_spec_file, "r") as f:
                    content = f.read()
                print("Agno agent content read from file", flush=True)
            else:
                print("ERROR: Node spec file was not created by Agno agent", flush=True)
                raise ValueError("Node spec file was not created")
        
        # Verify file exists and is not empty
        if not node_spec_file.exists():
            print("ERROR: node-spec.md does not exist", flush=True)
            raise ValueError("node-spec.md was not created")
        
        if node_spec_file.stat().st_size == 0:
            print("ERROR: node-spec.md is empty", flush=True)
            raise ValueError("node-spec.md is empty")
            
    except Exception as e:
        print(f"ERROR extracting content: {e}", flush=True)
        raise
    
    print(f"Returning content ({len(content)} characters)", flush=True)
    return content