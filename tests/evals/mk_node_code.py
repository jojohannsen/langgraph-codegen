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

from mk_utils import get_prompts, read_file_and_get_subdir, mk_agent, get_config

node_python_example = """
from langchain_core.runnables.config import RunnableConfig

def node_1(state: MyState, *, config:Optional[RunnableConfig] = None):
    mk_node_code.py
    read_field = state.read_field
    if read_field:
        write_field = "address"
        write_value = "123 Athens Street"
        return { write_field: write_value }
    else:
        return {} # must return something
"""

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
    agent = mk_agent(graph_name)
    # if state_spec.md doesn't exist, exit
    if not (Path(graph_name) / "state_spec.md").exists():
        print(f"{Fore.RED}Error: state_spec.md does not exist, use 'python mk_state_spec.py <graph_spec_path>' first{Style.RESET_ALL}")
        sys.exit(1)
    state_spec_file = Path(graph_name) / "state_spec.md"
    print(f"{Fore.GREEN}State spec file: {Fore.BLUE}{state_spec_file}{Style.RESET_ALL}")
    with open(state_spec_file, "r") as file:
        state_spec = file.read()
    state_code_file = Path(graph_name) / "state_code.py"
    with open(state_code_file, "r") as file:
        state_code = file.read()
    node_spec_file = Path(graph_name) / "node_spec.md"
    with open(node_spec_file, "r") as file:
        node_spec = file.read()
    graph_spec_description, state_spec_prompt, state_code_prompt, node_spec_prompt, node_code_prompt = get_prompts(config)
    prompt = node_code_prompt.format(graph_spec_description=graph_spec_description, 
                                     graph_name=graph_name,
                                     graph_spec=graph_spec, 
                                     state_spec=state_spec, 
                                     state_code=state_code,
                                     node_spec=node_spec,
                                     model_name=agent.model.id,
                                     node_python_example=node_python_example)
    result = agent.run(prompt)

