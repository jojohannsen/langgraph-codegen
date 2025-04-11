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
from langchain.prompts import PromptTemplate
def get_prompt(prompt_name, template_only=False):
    client = Client()
    if prompt_name.startswith("hub:"):
        prompt = client.pull_prompt(prompt_name[4:])
        if template_only:
            return prompt.messages[0].prompt.template
        else:
            return prompt.messages[0].prompt
    elif prompt_name.startswith("file:"):
        print(f"{Fore.CYAN}Reading prompt from file: {Fore.BLUE}{prompt_name[5:]}{Style.RESET_ALL}")
        with open(prompt_name[5:], "r") as f:
            content = f.read()
            if template_only:
                return content
            else:
                return PromptTemplate.from_template(content)
    else:
        return None

def get_single_prompt(config, prompt_type):
    """
    Get a single prompt based on the prompt type.
    
    Args:
        config (dict): Configuration dictionary containing prompts
        prompt_type (str): Type of prompt to retrieve. Valid values are:
            - 'graph_spec_description'
            - 'state_spec'
            - 'state_code'
            - 'node_spec'
            - 'node_code'
            - 'graph_spec'
            - 'graph_code'
            
    Returns:
        The requested prompt or None if prompt type is invalid
    """
    prompt_mapping = {
        'graph_spec_description': ('graph_spec_description', True),
        'state_spec': ('state_spec_prompt', False),
        'state_code': ('state_code_prompt', False),
        'node_spec': ('node_spec_prompt', False),
        'node_code': ('node_code_prompt', False),
        'graph_spec': ('graph_spec_prompt', False),
        'graph_code': ('graph_code_prompt', False)
    }
    
    if prompt_type not in prompt_mapping:
        return None
        
    config_key, template_only = prompt_mapping[prompt_type]
    return get_prompt(config['prompts'][config_key], template_only=template_only)

def get_config(graph_name):
    # we look for yaml file first in {graph_name}/{graph_name}.yaml
    # if not found, we look for {graph_name}.yaml in the current directory, and copy it to {graph_name}/{graph_name}.yaml
    path_to_yaml = Path(graph_name) / f"{graph_name}.yaml"
    if not path_to_yaml.exists():
        path_to_yaml = Path(f"{graph_name}.yaml")
        if not path_to_yaml.exists():
            path_to_yaml = Path(graph_name) / f"{graph_name}.yaml"
            print(f"{Fore.CYAN}Creating: {Fore.BLUE}{path_to_yaml}{Style.RESET_ALL}")
            # copy default.yaml file to this path
            default_config = Path("default.yaml")
            if not default_config.exists():
                print(f"{Fore.RED}Error: default.yaml does not exist{Style.RESET_ALL}")
                sys.exit(1)
            # read default.yaml file
            with open(default_config, "r") as f:
                default_config_content = f.read()
            # copy the graph_spec_description to the graph_spec_description.txt file
            with open(path_to_yaml, "w") as f:
                f.write(default_config_content)
    print(f"{Fore.CYAN}Reading: {Fore.BLUE}{path_to_yaml}{Style.RESET_ALL}")
    # read it
    with open(path_to_yaml, "r") as f:
        config = yaml.safe_load(f)
        # if that config doesn't have prompts, add the default prompts
        if 'prompts' not in config:
            config['prompts'] = {}
            config['prompts']['graph_spec_description'] = "hub:johannes/lgcodegen-graph-spec"
            config['prompts']['state_spec_prompt'] = "hub:johannes/lgcodegen-gen_state_spec"
            config['prompts']['state_code_prompt'] = "hub:johannes/lgcodegen-gen_state_code"
            config['prompts']['node_spec_prompt'] = "hub:johannes/lgcodegen-gen_node_spec"
            config['prompts']['node_code_prompt'] = "hub:johannes/lgcodegen-gen_node_code"
            config['prompts']['graph_spec_prompt'] = "hub:johannes/lgcodegen-gen_graph_spec"
            config['prompts']['graph_code_prompt'] = "hub:johannes/lgcodegen-gen_graph_code"
    return config

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

def mk_agent(working_dir, config):
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


