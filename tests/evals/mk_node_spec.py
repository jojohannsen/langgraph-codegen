import sys

from langchain_core.prompts import ChatPromptTemplate
from pathlib import Path
from colorama import init, Fore, Style
from mk_utils import get_prompts, read_file_and_get_subdir, mk_agent, get_config

if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_node_spec.py graph_spec_file")
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
    print(f"{Fore.GREEN}State spec file: {Fore.BLUE}{state_spec_file}{Style.RESET_ALL}")
    with open(state_spec_file, "r") as file:
        state_spec = file.read()
    node_spec_file = Path(graph_name) / f"node_spec.md"
    # if node_spec.md exists, ask if we should overwrite it, use questionary to ask
    if node_spec_file.exists():
        print(f"{Fore.GREEN}Node spec file exists: {Fore.BLUE}{node_spec_file}{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}Node spec file does not exist: {Fore.BLUE}{node_spec_file}{Style.RESET_ALL}")
    py_files = [f.name for f in Path(graph_name).glob("*.py") if f.name != "__init__.py"]
    # find the file that contains a "(BaseModel)", assume that is the state class, read that into state_code
    state_code = ""
    for file in py_files:
        with open(Path(graph_name) / file, "r") as f:
            content = f.read()
            if "(BaseModel)" in content:
                state_code = content
                break
    if not state_code:
        print(f"{Fore.RED}Error: could not find state class in {py_files}{Style.RESET_ALL}")
        sys.exit(1)
    print(f"{Fore.GREEN}Node spec file: {Fore.BLUE}{node_spec_file}{Style.RESET_ALL}")
    graph_spec_description, state_spec_prompt, state_code_prompt, node_spec_prompt, node_code_prompt = get_prompts(config)
    prompt = node_spec_prompt.format(graph_spec_description=graph_spec_description, 
                                     graph_name=graph_name,
                                     graph_spec=graph_spec, 
                                     state_spec=state_spec, 
                                     state_code=state_code,
                                     model_name=agent.model.id)
    result = agent.run(prompt)
    # verify node_spec.md exists
    if not node_spec_file.exists():
        print(f"{Fore.RED}Error: node_spec.md does not exist{Style.RESET_ALL}")
        sys.exit(1)
    print(f"{Fore.GREEN}Successfully generated: {Fore.BLUE}{node_spec_file}{Style.RESET_ALL}")
