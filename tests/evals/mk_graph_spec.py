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

from mk_utils import read_file_and_get_subdir, mk_agent, get_config, get_single_prompt, OpenRouterAgent

if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_graph_spec.py graph_spec_file")
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

    print(f"{Fore.GREEN}State spec file: {Fore.BLUE}{state_spec_file}{Style.RESET_ALL}")
    with open(state_spec_file, "r") as file:
        state_spec = file.read()
    state_code_file = Path(graph_name) / "state_code.py"
    with open(state_code_file, "r") as file:
        state_code = file.read()
    node_spec_file = Path(graph_name) / "node-spec.md"
    with open(node_spec_file, "r") as file:
        node_spec = file.read()
    graph_notation = get_single_prompt(config, 'graph_notation')
    graph_spec_prompt = get_single_prompt(config, 'graph_spec')
    prompt = graph_spec_prompt.format(graph_notation=graph_notation, 
                                     graph_name=graph_name,
                                     graph_spec=graph_spec, 
                                     state_spec=state_spec, 
                                     state_code=state_code,
                                     node_spec=node_spec,
                                     model_name=config['spec']['llm_model'])
    agent = mk_agent(graph_name, config['spec']['llm_provider'], config['spec']['llm_model'], config['spec']['agent_library'], system_prompt=prompt)
    result = agent.run(prompt)
    graph_spec_file = Path(graph_name) / f"graph-spec.md"
    if isinstance(agent, OpenRouterAgent):
        with open(graph_spec_file, "w") as f:
            f.write(result.choices[0].message.content)
    else:
        pass # the Agno agent writes the response to the correct file
    # verify {graph_name}_graph_spec.md was created and is not empty
    if not graph_spec_file.exists():
        with open("graph_spec_error.txt", "w") as f:
            result = str(result)
            f.write(result)
        print(f"{Fore.RED}Error: graph-spec.md does not exist{Style.RESET_ALL}")
        sys.exit(1)
    if graph_spec_file.stat().st_size == 0:
        print(f"{Fore.RED}Error: graph-spec.md is empty{Style.RESET_ALL}")
        sys.exit(1)
    print(f"{Fore.GREEN}Graph spec file: {Fore.BLUE}{graph_spec_file}{Style.RESET_ALL}")

