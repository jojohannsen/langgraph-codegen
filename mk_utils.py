import os
import sys
import yaml
from colorama import init, Fore, Style
from langsmith import Client
from pathlib import Path
from agno.agent import Agent
from agno.tools.file import FileTools
from agno.models.anthropic import Anthropic
from agno.models.openai import OpenAI

def get_prompts():
    client = Client()
    graph_spec = client.pull_prompt("johannes/lgcodegen-graph-spec")
    return graph_spec.messages[0].prompt.template

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
    # we look for yaml file first in {working_dir}/{working_dir}.yaml
    # if not found, we look for config.yaml in the current directory, and copy it to {working_dir}/{working_dir}.yaml
    path_to_yaml = Path(working_dir) / f"{working_dir}.yaml"
    if not path_to_yaml.exists():
        path_to_yaml = Path(f"{working_dir}.yaml")
        if not path_to_yaml.exists():
            print(f"{Fore.ORANGE}{path_to_yaml} does not exist.{Style.RESET_ALL}")

    path_to_yaml = Path(working_dir) / f"{working_dir}.yaml"
    if not path_to_yaml.exists():
        print(f"{Fore.ORANGE}Creating {path_to_yaml}{Style.RESET_ALL}")
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
    print(config)
    agent = None
    if config['provider'] == "anthropic":
        agent = Agent(model=Anthropic(id="claude-3-7-sonnet-latest"), tools=[FileTools(Path(working_dir))])
    elif config['provider'] == "openai":
        agent = Agent(model=OpenAI(id="gpt-4o-mini"), tools=[FileTools(Path(working_dir))])
    return agent

def check_api_keys(working_dir):
    # if the config.yaml file does not exist, print message about file not found and return False,False,False
    if not os.path.exists(Path(working_dir) / "config.yaml"):
        print("config.yaml file not found, LLMs will NOT be used.")
        return False,False,False
    # read the config.yaml file
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
        print(config)
        print(config['use_openai_api'])
    # Dictionary to store results
    api_keys = {
        "OPENAI_API_KEY": {"exists": False, "use": False},
        "ANTHROPIC_API_KEY": {"exists": False, "use": False},
        "GEMINI_API_KEY": {"exists": False, "use": False}
    }
    
    # Check which environment variables exist
    for key in api_keys:
        if os.environ.get(key):
            api_keys[key]["exists"] = True
            print(f"Found {key} in environment variables.")
        else:
            print(f"{key} not found in environment variables.")
    
    # Ask user whether to use each key
    for key in api_keys:
        if api_keys[key]["exists"]:
            while True:
                response = input(f"Do you want to use {key}? (y/n): ").lower()
                if response in ["y", "yes"]:
                    api_keys[key]["use"] = True
                    break
                elif response in ["n", "no"]:
                    break
                else:
                    print("Please enter 'y' or 'n'.")
    
    # Create the result variables
    use_openai_api_key = api_keys["OPENAI_API_KEY"]["use"]
    use_anthropic_api_key = api_keys["ANTHROPIC_API_KEY"]["use"]
    use_gemini_api_key = api_keys["GEMINI_API_KEY"]["use"]
    
    # Return the results
    return use_openai_api_key, use_anthropic_api_key, use_gemini_api_key

if __name__ == "__main__":
    use_openai_api_key, use_anthropic_api_key, use_gemini_api_key = check_api_keys()
    
    print("\nResults:")
    print(f"use_openai_api_key = {use_openai_api_key}")
    print(f"use_anthropic_api_key = {use_anthropic_api_key}")
    print(f"use_gemini_api_key = {use_gemini_api_key}")
