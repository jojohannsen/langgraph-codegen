import os
import sys
import yaml
from colorama import init, Fore, Style
from langsmith import Client
from pathlib import Path
from agno.agent import Agent
from agno.tools.file import FileTools
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat

def get_prompts():
    client = Client()
    graph_spec = client.pull_prompt("johannes/lgcodegen-graph-spec")
    state_spec = client.pull_prompt("johannes/lgcodegen-gen_state_spec")
    state_code = client.pull_prompt("johannes/lgcodegen-gen_state_code")
    node_spec = client.pull_prompt("johannes/lgcodegen-gen_node_spec")
    node_code = client.pull_prompt("johannes/lgcodegen-gen_node_code")
    return graph_spec.messages[0].prompt.template, state_spec.messages[0].prompt, state_code.messages[0].prompt, node_spec.messages[0].prompt, node_code.messages[0].prompt

def read_file_and_get_subdir(file_path):
    """
    Read the contents of a file and extract the subdirectory name.
    
    Args:
        file_path (str): Path to the file to read
        
    Returns:
        tuple: (subdir, pseudo_code) - The subdirectory name and file contents
    """
    # Check if the file exists
    if not os.path.isfile(file_path):
        print(f"Error: The file '{file_path}' does not exist")
        sys.exit(1)

    # Read the file contents into a string variable
    try:
        pseudo_code = None
        with open(file_path, 'r') as file:
            pseudo_code = file.read()
        if not pseudo_code or len(pseudo_code) < 10:
            print(f"Error: pseudo_code missing from file")
            sys.exit(1)
        subdir = file_path.split("/")[-1].split(".")[0]
        return subdir, pseudo_code
    except Exception as e:
        print(f"Error reading the file: {e}")
        sys.exit(1)

def mk_agent(working_dir):
    # create the working_dir if it does not exist
    Path(working_dir).mkdir(parents=True, exist_ok=True)
    # we look for yaml file first in {working_dir}/{working_dir}.yaml
    # if not found, we look for config.yaml in the current directory, and copy it to {working_dir}/{working_dir}.yaml
    path_to_yaml = Path(working_dir) / f"{working_dir}.yaml"
    if not path_to_yaml.exists():
        path_to_yaml = Path(f"{working_dir}.yaml")
        if not path_to_yaml.exists():
            print(f"{Fore.CYAN}{path_to_yaml} does not exist.{Style.RESET_ALL}")

    path_to_yaml = Path(working_dir) / f"{working_dir}.yaml"
    if not path_to_yaml.exists():
        print(f"{Fore.CYAN}Creating: {Fore.BLUE}{path_to_yaml}{Style.RESET_ALL}")
        with open(path_to_yaml, "w") as f:
            yaml_to_write = '''provider: "anthropic"  # "google", "openai", or "anthropic"
models:
  google: "gemini-2.5-pro-exp-03-25"
  openai: "o3-mini-high"
  anthropic: "claude-3-7-sonnet-latest"'''
            f.write(yaml_to_write)
    # read it
    with open(path_to_yaml, "r") as f:
        config = yaml.safe_load(f)
    model_name = config['models'][config['provider']]
    print(f"{Fore.CYAN}Agent Model: {Fore.BLUE}{model_name}{Style.RESET_ALL}")
    agent = None
    if config['provider'] == "anthropic":
        agent = Agent(model=Claude(id=model_name), tools=[FileTools(Path(working_dir))])
    elif config['provider'] == "openai":
        agent = Agent(
            model=OpenAIChat(id=model_name),
            tools=[FileTools(Path(working_dir))]
        )
    return agent


