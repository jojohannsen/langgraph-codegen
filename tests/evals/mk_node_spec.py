import sys

from langchain_core.prompts import ChatPromptTemplate
from pathlib import Path
from colorama import init, Fore, Style
from mk_utils import read_file_and_get_subdir, mk_agent, get_config, get_single_prompt, OpenRouterAgent, extract_python_code

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

    # if state_spec.md doesn't exist, exit
    state_spec_file = Path(graph_name) / "state-spec.md"
    if not state_spec_file.exists():
        print(f"{Fore.RED}Error: state-spec.md does not exist, use 'python mk_state_spec.py <graph_spec_path>' first{Style.RESET_ALL}")
        sys.exit(1)
    with open(state_spec_file, "r") as file:
        state_spec = file.read()
    node_spec_file = Path(graph_name) / f"node-spec.md"
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
        state_code = "State class has not yet been created."
#        print(f"{Fore.RED}Error: could not find state class in {py_files}{Style.RESET_ALL}")
#       sys.exit(1)
    print(f"{Fore.GREEN}Node spec file: {Fore.BLUE}{node_spec_file}{Style.RESET_ALL}")
    graph_notation = get_single_prompt(config, 'graph_notation')
    node_spec_prompt = get_single_prompt(config, 'node_spec')
    prompt = node_spec_prompt.format(graph_notation=graph_notation, 
                                     graph_name=graph_name,
                                     graph_spec=graph_spec, 
                                     state_spec=state_spec, 
                                     state_code=state_code,
                                     model_name=config['spec']['llm_model'])
    agent = mk_agent(graph_name, config['spec']['llm_provider'], config['spec']['llm_model'], config['spec']['agent_library'], system_prompt=prompt)
    result = agent.run(prompt)
    if isinstance(agent, OpenRouterAgent):
        with open(node_spec_file, "w") as f:
            f.write(result.choices[0].message.content)
    else:
        pass # the Agno agent writes the response to the correct file
    # verify node-spec.md exists and is not empty
    if not node_spec_file.exists():
        print(f"{Fore.RED}Error: node-spec.md does not exist{Style.RESET_ALL}")
        sys.exit(1)
    if node_spec_file.stat().st_size == 0:
        print(f"{Fore.RED}Error: node-spec.md is empty{Style.RESET_ALL}")
        sys.exit(1)
    print(f"{Fore.GREEN}Successfully generated: {Fore.BLUE}{node_spec_file}{Style.RESET_ALL}")
