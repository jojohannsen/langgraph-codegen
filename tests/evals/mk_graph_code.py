
import sys
from colorama import init, Fore, Style
from pathlib import Path
from mk_utils import read_file_and_get_subdir, mk_agent, get_config, get_single_prompt, get_file, OpenRouterAgent, extract_python_code
from agno.agent import Agent

if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_graph_code.py graph_spec_file")
        sys.exit(1)

    file_path = sys.argv[1]
    graph_name, graph_spec = read_file_and_get_subdir(file_path)
        # create the working_dir if it does not exist
    Path(graph_name).mkdir(parents=True, exist_ok=True)

    print(f"{Fore.GREEN}Graph folder: {Fore.BLUE}{graph_name}{Style.RESET_ALL}")
    config = get_config(graph_name)
    agent = mk_agent(graph_name, config)
    # if state-spec.md doesn't exist, exit
    state_spec_file = Path(graph_name) / "state-spec.md"
    if not state_spec_file.exists():
        print(f"{Fore.RED}Error: state-spec.md does not exist, use 'python mk_state_spec.py <graph_spec_path>' first{Style.RESET_ALL}")
        sys.exit(1)
    
    state_spec = get_file(graph_name, "state", "spec")
    state_code = get_file(graph_name, "state", "code")
    node_spec = get_file(graph_name, "node", "spec")
    graph_flow_spec = get_file(graph_name, "graph", "spec")
    graph_spec_description = get_single_prompt(config, 'graph_spec_description')
    graph_code_prompt = get_single_prompt(config, 'graph_code')
    prompt = graph_code_prompt.format(graph_spec_description=graph_spec_description, 
                                     graph_name=graph_name,
                                     graph_spec=graph_spec, 
                                     graph_flow_spec=graph_flow_spec, 
                                     state_spec=state_spec, 
                                     state_code=state_code,
                                     node_spec=node_spec,
                                     model_name=agent.model.id)
    # use agent.run if its an Agno Agent, otherwise use agent.invoke
    result = agent.run(prompt)
    graph_code_file = Path(graph_name) / f"graph_code.py"
    if isinstance(agent, OpenRouterAgent):
        code = extract_python_code(result.choices[0].message.content)
        with open(graph_code_file, "w") as f:
            f.write(code)
    else:
        pass # the Agno agent writes the response to the correct file
    # verify {graph_name}_graph_code.py was created and is not empty
    if not graph_code_file.exists():
        print(f"{Fore.RED}Error: graph_code.py does not exist{Style.RESET_ALL}")
        sys.exit(1)
    if graph_code_file.stat().st_size == 0:
        print(f"{Fore.RED}Error: graph_code.py is empty{Style.RESET_ALL}")
        sys.exit(1)
    print(f"{Fore.GREEN}Graph code file: {Fore.BLUE}{graph_code_file}{Style.RESET_ALL}")

