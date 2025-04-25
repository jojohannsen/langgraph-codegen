import os
import sys
from pathlib import Path
from colorama import init, Fore, Style
from mk_utils import read_file_and_get_subdir, mk_agent, get_config, get_single_prompt, OpenRouterAgent, extract_python_code, get_tools


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

    print(f"{Fore.GREEN}Graph folder: {Fore.BLUE}{graph_name}{Style.RESET_ALL}")
    config = get_config(graph_name)
    agent_library, llm_provider, llm_model = get_tools(config, 'code')
    state_spec_file = Path(graph_name) / "state-spec.md"
    if not state_spec_file.exists():
        print(f"{Fore.RED}Error: state-spec.md does not exist, use 'python mk_state_spec.py <graph_spec_path>' first{Style.RESET_ALL}")
        sys.exit(1)
    print(f"{Fore.GREEN}State spec: {Fore.BLUE}{state_spec_file}{Style.RESET_ALL}")
    with open(state_spec_file, "r") as file:
        state_spec = file.read()
    graph_notation = get_single_prompt(config, 'graph_notation')
    state_code_prompt = get_single_prompt(config, 'state_code')
    state_code_example = get_single_prompt(config, 'state_code_example')
    prompt = state_code_prompt.format(graph_notation=graph_notation, 
                                      graph_spec=graph_spec, 
                                      state_spec=state_spec, 
                                      state_code_example=state_code_example,
                                      model_name=llm_model)
    agent = mk_agent(graph_name, llm_provider, llm_model, agent_library, system_prompt="You are an expert Python developer, and write code based on a design document.")
    with open("mk_state_code.prompt.txt", "w") as f:
        f.write(prompt)
    result = agent.run(prompt)
    with open("mk_state_code.result.txt", "w") as f:
        f.write(str(result))
    if isinstance(agent, OpenRouterAgent):
        code = extract_python_code(result.choices[0].message.content)
        with open(f"{graph_name}/state_code.py", "w") as f:
            f.write(code)
    else:
        pass # the Agno agent writes the response to the correct file
    # verify state_code.py exists
    if not (Path(graph_name) / "state_code.py").exists():
        print(f"{Fore.RED}Error: state_code.py does not exist{Style.RESET_ALL}")
        sys.exit(1)
    print(f"{Fore.GREEN}Successfully generated: {Fore.BLUE}{Path(graph_name) / 'state_code.py'}{Style.RESET_ALL}")
