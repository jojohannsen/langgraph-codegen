from pathlib import Path
import sys
from colorama import init, Fore, Style
from mk_utils import get_config,read_file_and_get_subdir, mk_agent, get_single_prompt

if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_state_spec.py graph_spec_file")
        sys.exit(1)

    file_path = sys.argv[1]
    graph_name, graph_spec = read_file_and_get_subdir(file_path)
    # create the working_dir if it does not exist
    Path(graph_name).mkdir(parents=True, exist_ok=True)
    config = get_config(graph_name)
    print(f"{Fore.GREEN}Graph folder: {Fore.BLUE}{graph_name}{Style.RESET_ALL}")
    agent = mk_agent(graph_name, config)
    # get the state_spec_prompt from the config
    state_spec_prompt = get_single_prompt(config, 'state_spec')
    graph_spec_description = get_single_prompt(config, 'graph_spec_description')
    prompt = state_spec_prompt.format(graph_spec_description=graph_spec_description, graph_spec=graph_spec, model_name=agent.model.id)
    result = agent.run(prompt)
    # list all the py files in the subdir
    py_files = [f for f in Path(graph_name).glob("*.py") if f.name != "__init__.py"]
    print(f"{Fore.GREEN}Python files: {Fore.BLUE}{py_files}{Style.RESET_ALL}")



