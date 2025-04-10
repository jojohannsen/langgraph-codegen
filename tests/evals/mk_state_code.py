import os
import sys
from pathlib import Path
from colorama import init, Fore, Style
from agno.agent import Agent
from agno.tools.file import FileTools
from agno.models.anthropic import Claude

from mk_utils import get_prompts, read_file_and_get_subdir, mk_agent



if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_state_spec.py graph_spec_file")
        sys.exit(1)

    file_path = sys.argv[1]
    subdir, graph_spec = read_file_and_get_subdir(file_path)
    print(f"{Fore.GREEN}Graph folder: {Fore.BLUE}{subdir}{Style.RESET_ALL}")
    agent = mk_agent(subdir)
    # if state_spec.md doesn't exist, exit
    if not (Path(subdir) / "state_spec.md").exists():
        print(f"{Fore.RED}Error: state_spec.md does not exist, use 'python mk_state_spec.py <graph_spec_path>' first{Style.RESET_ALL}")
        sys.exit(1)
    state_spec_file = Path(subdir) / "state_spec.md"
    print(f"{Fore.GREEN}State spec file: {Fore.BLUE}{state_spec_file}{Style.RESET_ALL}")
    with open(state_spec_file, "r") as file:
        state_spec = file.read()
    graph_spec_description, state_spec_prompt, state_code_prompt, node_spec_prompt, node_code_prompt = get_prompts()
    prompt = state_code_prompt.format(graph_spec_description=graph_spec_description, graph_spec=graph_spec, state_spec=state_spec, model_name=agent.model.id)
    result = agent.run(prompt)
    # list py files in the subdir
    py_files = [f.name for f in Path(subdir).glob("*.py") if f.name != "__init__.py"]
    print(f"{Fore.GREEN}Python files: {Fore.BLUE}{py_files}{Style.RESET_ALL}")

