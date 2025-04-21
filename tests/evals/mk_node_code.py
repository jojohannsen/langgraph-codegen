import os
import sys
import questionary

from colorama import init, Fore, Style
from langchain_core.prompts import ChatPromptTemplate
from pathlib import Path
from agno.agent import Agent
from agno.tools.file import FileTools
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

from mk_utils import read_file_and_get_subdir, mk_agent, get_config, get_single_prompt, OpenRouterAgent, extract_python_code

if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_node_code.py graph_spec_file")
        sys.exit(1)

    file_path = sys.argv[1]
    graph_name, graph_spec = read_file_and_get_subdir(file_path)
        # create the working_dir if it does not exist
    Path(graph_name).mkdir(parents=True, exist_ok=True)
    config = get_config(graph_name)
    print(f"{Fore.GREEN}Graph folder: {Fore.BLUE}{graph_name}{Style.RESET_ALL}")
    agent = mk_agent(graph_name, config)
    # if state_spec.md doesn't exist, exit

    state_spec_file = Path(graph_name) / "state-spec.md"
    if not state_spec_file.exists():
        print(f"{Fore.RED}Error: state-spec.md does not exist, use 'python mk_state_spec.py <graph_spec_path>' first{Style.RESET_ALL}")
        sys.exit(1)
    print(f"{Fore.GREEN}State spec file: {Fore.BLUE}{state_spec_file}{Style.RESET_ALL}")
    with open(state_spec_file, "r") as file:
        state_spec = file.read()
    state_code_file = Path(graph_name) / "state_code.py"
    with open(state_code_file, "r") as file:
        state_code = file.read()
    node_spec_file = Path(graph_name) / "node-spec.md"
    if not node_spec_file.exists():
        print(f"{Fore.RED}Error: node-spec.md does not exist, use 'python mk_node_spec.py <graph_spec_path>' first{Style.RESET_ALL}")
        sys.exit(1)
    with open(node_spec_file, "r") as file:
        node_spec = file.read()
    graph_spec_description = get_single_prompt(config, 'graph_spec_description')
    human_input_example = get_single_prompt(config, 'human_input_example')
    node_code_prompt = get_single_prompt(config, 'node_code')
    node_code_example = get_single_prompt(config, 'node_code_example')
    prompt = node_code_prompt.format(graph_spec_description=graph_spec_description, 
                                     graph_name=graph_name,
                                     graph_spec=graph_spec, 
                                     state_spec=state_spec, 
                                     state_code=state_code,
                                     node_spec=node_spec,
                                     model_name=agent.model.id,
                                     human_input_example=human_input_example,
                                     node_code_example=node_code_example)
    result = agent.run(prompt)
    node_code_file = Path(graph_name) / "node_code.py"
    if isinstance(agent, OpenRouterAgent):
        code = extract_python_code(result.choices[0].message.content)
        with open(node_code_file, "w") as f:
            f.write(code)
    else:
        pass # the Agno agent writes the response to the correct file
    # verify node_code.py exists and is not empty
    if not (Path(graph_name) / "node_code.py").exists():
        print(f"{Fore.RED}Error: node_code.py does not exist{Style.RESET_ALL}")
    if (Path(graph_name) / "node_code.py").stat().st_size == 0:
        print(f"{Fore.RED}Error: node_code.py is empty{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Successfully generated: {Fore.BLUE}{node_code_file}{Style.RESET_ALL}")