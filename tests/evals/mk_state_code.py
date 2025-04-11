import os
import sys
from pathlib import Path
from colorama import init, Fore, Style
from mk_utils import get_prompts, read_file_and_get_subdir, mk_agent, get_config


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
    agent = mk_agent(graph_name)
    # if state_spec.md doesn't exist, exit
    if not (Path(graph_name) / "state_spec.md").exists():
        print(f"{Fore.RED}Error: state_spec.md does not exist, use 'python mk_state_spec.py <graph_spec_path>' first{Style.RESET_ALL}")
        sys.exit(1)
    state_spec_file = Path(graph_name) / "state_spec.md"
    print(f"{Fore.GREEN}State spec: {Fore.BLUE}{state_spec_file}{Style.RESET_ALL}")
    with open(state_spec_file, "r") as file:
        state_spec = file.read()
    graph_spec_description, state_spec_prompt, state_code_prompt, node_spec_prompt, node_code_prompt = get_prompts(config)
    prompt = state_code_prompt.format(graph_spec_description=graph_spec_description, graph_spec=graph_spec, state_spec=state_spec, model_name=agent.model.id)
    result = agent.run(prompt)
    # verify state_code.py exists
    if not (Path(graph_name) / "state_code.py").exists():
        print(f"{Fore.RED}Error: state_code.py does not exist{Style.RESET_ALL}")
        sys.exit(1)
    print(f"{Fore.GREEN}Successfully generated: {Fore.BLUE}{Path(graph_name) / 'state_code.py'}{Style.RESET_ALL}")
