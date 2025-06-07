import os
import sys
import re
import yaml
from colorama import init, Fore, Style
from langsmith import Client
from pathlib import Path
from agno.agent import Agent
from agno.tools.file import FileTools
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from langchain.prompts import PromptTemplate
from dataclasses import dataclass
from typing import List, Set, Optional, Tuple
from langchain_openai import ChatOpenAI
import questionary

def get_tools(config, category):
    agent_library = config[category]['agent_library']
    llm_provider = config[category]['llm_provider']
    llm_model = config[category]['llm_model']
    # one sentence summary of tools we use (the above 3 variables) for writing specifications
    tools_summary = f"  {llm_provider}, {llm_model} using {agent_library} with tools to write file."
    print(f"{Fore.GREEN}Tools: {Fore.BLUE}{tools_summary}{Style.RESET_ALL}")
    return agent_library, llm_provider, llm_model

def get_prompt(prompt_name, template_only=False):
    client = Client()
    if prompt_name.startswith("hub:"):
        prompt = client.pull_prompt(prompt_name[4:])
        if template_only:
            return prompt.messages[0].prompt.template
        else:
            return prompt.messages[0].prompt
    elif prompt_name.startswith("file:"):
        print(f"{Fore.CYAN}Reading: {Fore.BLUE}{prompt_name[5:]}{Style.RESET_ALL}")
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
            - 'graph_notation'
            - 'state_spec'
            - 'state_code'
            - 'node_spec'
            - 'node_code'
            - 'graph_spec'
            - 'graph_code'
            - 'main_code'
            
    Returns:
        The requested prompt or None if prompt type is invalid
    """
    prompt_mapping = {
        'graph_notation': ('graph_notation', True),
        'human_input_example': ('human_input_example', True),
        'node_code_example': ('node_code_example', True),
        'state_spec': ('state_spec_prompt', False),
        'state_code': ('state_code_prompt', False),
        'node_spec': ('node_spec_prompt', False),
        'node_code': ('node_code_prompt', False),
        'graph_spec': ('graph_spec_prompt', False),
        'graph_code': ('graph_code_prompt', False),
        'main_code': ('main_code_prompt', False)
    }
    
    if prompt_type not in prompt_mapping:
        return None
        
    config_key, template_only = prompt_mapping[prompt_type]
    return get_prompt(config['prompts'][config_key], template_only=template_only)

def get_file(graph_name, area, file_type):
    extension = "md" if file_type == "spec" else "py"
    delimiter = "-" if file_type == "spec" else "_"
    file_path = Path(graph_name) / f"{area}{delimiter}{file_type}.{extension}"
    if not file_path.exists():
        print(f"{Fore.RED}Error: {area}{delimiter}{file_type}.{extension} does not exist{Style.RESET_ALL}")
        sys.exit(1)
    # return contents of file
    with open(file_path, "r") as f:
        return f.read()
    # if file is not found, return None
    return None

def prepare_working_folder(graph_name):
    """Prepares a working directory for graph code generation and configuration.

    This function creates a working directory for the specified graph if it doesn't exist,
    sets up the necessary configuration, and creates required utility files. It handles
    the setup of LLM (Language Learning Model) configurations and generates the LLM code file.

    Args:
        graph_name (str): The name of the graph, which will be used as the directory name
            and for configuration file naming.

    Returns:
        dict: A configuration dictionary containing:
            - node_agent_provider: The agent library to be used
            - node_llm_provider: The LLM provider (e.g., 'openai', 'anthropic')
            - node_llm_model: The specific LLM model to use

    Raises:
        SystemExit: If required files cannot be created or accessed.

    Example:
        >>> config = prepare_working_folder("my_graph")
        >>> print(config['node_llm_provider'])
        'openai'
    """
    # create the working_dir if it does not exist
    Path(graph_name).mkdir(parents=True, exist_ok=True)
    config = get_config(graph_name)
    node_config = config['node']
    node_agent_provider = node_config['agent_library']
    node_llm_provider = node_config['llm_provider']
    node_llm_model = node_config['llm_model']
    print(f"{Fore.CYAN}Node Agent Provider: {Fore.BLUE}{node_agent_provider}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Node LLM Provider: {Fore.BLUE}{node_llm_provider}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Node LLM Model: {Fore.BLUE}{node_llm_model}{Style.RESET_ALL}")

    # Get the LLM code template from langsmith hub
    llm_code_template = get_prompt("hub:johannes/lgcodegen-node-llm-code", template_only=True)
    if llm_code_template:
        # Format the template with the LLM configuration
        formatted_code = llm_code_template.format(
            llm_provider=node_llm_provider,
            llm_model=node_llm_model
        )
        # Write the formatted code to lgcodegen_llm.py
        llm_code_file = Path(graph_name) / "lgcodegen_llm.py"
        print(f"{Fore.CYAN}Writing LLM code to: {Fore.BLUE}{llm_code_file}{Style.RESET_ALL}")
        with open(llm_code_file, "w") as f:
            f.write(formatted_code)
    else:
        print(f"{Fore.RED}Error: Could not fetch LLM code template from langsmith hub{Style.RESET_ALL}")
        sys.exit(1)

    return config

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
            with open(path_to_yaml, "w") as f:
                f.write(default_config_content)
    print(f"{Fore.CYAN}Reading: {Fore.BLUE}{path_to_yaml}{Style.RESET_ALL}")
    # read it
    with open(path_to_yaml, "r") as f:
        config = yaml.safe_load(f)
        # if that config doesn't have prompts, add the default prompts
        if 'prompts' not in config:
            config['prompts'] = {}
            config['prompts']['graph_notation'] = "hub:johannes/lgcodegen-graph-notation"
            config['prompts']['human_input_example'] = "hub:johannes/lgcodegen-questionary_human_input"
            config['prompts']['node_code_example'] = "hub:johannes/lgcodegen-node_code_example"
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

from openai import OpenAI
from types import SimpleNamespace
class OpenRouterAgent:
    def __init__(self, model_name, api_key, instructions=None):
        self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        self.model_name = model_name
        self.model = SimpleNamespace(id=model_name)
        self.instructions = instructions
    def run(self, prompt):
        print(f"{Fore.CYAN}Running OpenRouter Agent with model {Fore.BLUE}{self.model_name}{Style.RESET_ALL}")
        print(f"Instructions: {Fore.BLUE}{self.instructions}{Style.RESET_ALL}")
        print(f"Prompt: {Fore.BLUE}{prompt}{Style.RESET_ALL}")
        return self.client.chat.completions.create(
            model=self.model_name, 
            messages=[
                {"role": "system", "content": self.instructions},
                {"role": "user", "content": prompt}
            ]
        )


def extract_python_code(text):
    """
    Extract Python code from text that contains code blocks.
    
    Args:
        text (str): Text containing Python code blocks marked with ```python and ```
        
    Returns:
        str: The extracted Python code without the markdown formatting
    """
    # Pattern to match Python code blocks
    pattern = r"```python\n(.*?)```"
    
    # Find all matches using regex with DOTALL flag to match across newlines
    matches = re.findall(pattern, text, re.DOTALL)
    
    # Return the first match if found, otherwise empty string
    return matches[0] if matches else ""



def mk_agent(working_dir, llm_provider, llm_model, agent_library, system_prompt=None):
    print(f"  {Fore.CYAN}LLM Provider: {Fore.BLUE}{llm_provider}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}LLM Model: {Fore.BLUE}{llm_model}{Style.RESET_ALL}")
    print(f"  {Fore.CYAN}Agent Library: {Fore.BLUE}{agent_library}{Style.RESET_ALL}")
    system_prompt = system_prompt.replace("{", "{{").replace("}", "}}") if system_prompt else None
    
    print(f"{Fore.CYAN}Writing files with Agno Agent + FileTools{Style.RESET_ALL}")
    if llm_provider == "anthropic":
        agent = Agent(model=Claude(id=llm_model), tools=[FileTools(Path(working_dir))])
    elif llm_provider == "openai":
        agent = Agent(
            model=OpenAIChat(id=llm_model),
            tools=[FileTools(Path(working_dir))],
            instructions=[system_prompt]
        )
    elif llm_provider == "google":
        agent = Agent(
                model=Gemini(id=llm_model),
                tools=[FileTools(Path(working_dir))],
                instructions=[system_prompt]
        )
    elif llm_provider == 'openrouter':
        print(f"{Fore.CYAN}Using OpenRouter for file management{Style.RESET_ALL}")
        agent = OpenRouterAgent(llm_model, os.getenv('OPENROUTER_API_KEY'))
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}")
    return agent



# solveit langgraph_DSL notebook
def unit_generator(graph):
    lines = graph.split("\n")
    comments = []
    for line in lines:
        if line.startswith("#"):
            comments.append(line[2:])
        else:
            yield line, "\n".join(comments)
            comments = []

def parse_line(line, is_first_line=False):
    """
    Parse a line of text in one of the specified formats and extract the information.
    
    Args:
        line (str): A line of text in one of the supported formats
        
    Returns:
        dict: A dictionary containing the extracted keys and values
    """
    # Clean the line
    line = line.strip()
    
    # Split on the arrow to get from and to parts
    if "->" not in line:
        raise ValueError("Line must contain '->' operator")
    
    from_part, to_part = [part.strip() for part in line.split("->")]
    
    result = { "line": line }
    if is_first_line:
        result["state_class_name"] = from_part
        result["start_node"] = to_part
        return result
    
    
    # Handle from part - could be a single node or multiple nodes separated by commas
    if "," in from_part:
        # Format: from_node_1, from_node_2 -> to_node_name
        from_nodes = [node.strip() for node in from_part.split(",")]
        result["from_nodes"] = from_nodes
    else:
        # Single from node
        result["from_node_name"] = from_part
    
    # Handle to part - could be a single node, multiple nodes, or a routing function
    if "(" in to_part and ")" in to_part:
        # This is either a routing function or a worker
        function_name, args = to_part.split("(", 1)
        args = args.rstrip(")")
        
        if "." in args:
            # Format: from_node_name -> to_worker(StateClassName.field_name)
            result["to_worker"] = function_name.strip()
            state_class, field_name = args.split(".")
            result["state_class_name"] = state_class.strip()
            result["field_name"] = field_name.strip()
        else:
            # Format: from_node_name -> to_routing_function(to_node_1, to_node_2)
            result["to_routing_function"] = function_name.strip()
            to_nodes = [node.strip() for node in args.split(",")]
            result["to_nodes"] = to_nodes
    elif "," in to_part:
        # Format: from_node_name -> to_node_1, to_node_2
        to_nodes = [node.strip() for node in to_part.split(",")]
        result["to_nodes"] = to_nodes
    else:
        # Format: from_node_name -> to_node_name
        result["to_node_name"] = to_part
    
    return result


@dataclass
class StartGraphTransition:
    state_class_name: str
    start_node: str
    line: str
    
    def get_source_nodes(self) -> List[str]:
        return []
    
    def get_dest_nodes(self) -> List[str]:
        return [self.start_node]
    
    def get_worker_nodes(self) -> List[tuple]:
        return []
    
    def get_router_functions(self) -> List[tuple]:
        return []

@dataclass
class SingleNodeTransition:
    from_node_name: str
    to_node_name: str
    line: str
    
    def get_source_nodes(self) -> List[str]:
        return [self.from_node_name]
    
    def get_dest_nodes(self) -> List[str]:
        return [self.to_node_name]
    
    def get_worker_nodes(self) -> List[tuple]:
        return []
    
    def get_router_functions(self) -> List[tuple]:
        return []

@dataclass
class MultiSourceTransition:
    from_nodes: List[str]
    to_node_name: str
    line: str
    
    def get_source_nodes(self) -> List[str]:
        return self.from_nodes
    
    def get_dest_nodes(self) -> List[str]:
        return [self.to_node_name]
    
    def get_worker_nodes(self) -> List[tuple]:
        return []
    
    def get_router_functions(self) -> List[tuple]:
        return []

@dataclass
class MultiTargetTransition:
    from_node_name: str
    to_nodes: List[str]
    line: str
    
    def get_source_nodes(self) -> List[str]:
        return [self.from_node_name]
    
    def get_dest_nodes(self) -> List[str]:
        return self.to_nodes
    
    def get_worker_nodes(self) -> List[tuple]:
        return []
    
    def get_router_functions(self) -> List[tuple]:
        return []

@dataclass
class RoutingTransition:
    from_node_name: str
    to_routing_function: str
    to_nodes: List[str]
    line: str
    
    def get_source_nodes(self) -> List[str]:
        return [self.from_node_name]
    
    def get_dest_nodes(self) -> List[str]:
        return self.to_nodes
    
    def get_worker_nodes(self) -> List[tuple]:
        return []
    
    def get_router_functions(self) -> List[tuple]:
        return [(self.to_routing_function, tuple(self.to_nodes))]

@dataclass
class WorkerTransition:
    from_node_name: str
    to_worker: str
    state_class_name: str
    field_name: str
    line: str
    
    def get_source_nodes(self) -> List[str]:
        return [self.from_node_name]
    
    def get_dest_nodes(self) -> List[str]:
        return [self.to_worker]
    
    def get_worker_nodes(self) -> List[tuple]:
        return [(self.to_worker, self.state_class_name, self.field_name)]
    
    def get_router_functions(self) -> List[tuple]:
        return []

def parse_transition(line, is_first_line=False):
    """
    Parse a line of text in one of the specified formats and convert it directly
    into the appropriate transition class.
    
    Args:
        line (str): A line of text in one of the supported formats
        
    Returns:
        Union[SingleNodeTransition, MultiSourceTransition, MultiTargetTransition, 
              RoutingTransition, WorkerTransition]: The appropriate transition object
    """
    # First parse the line into a dictionary
    parsed_dict = parse_line(line, is_first_line)

    # Then convert the dictionary to the appropriate transition class
    # Single node to single node
    if "state_class_name" in parsed_dict and "to_worker" not in parsed_dict:
        return StartGraphTransition(
            state_class_name=parsed_dict["state_class_name"],
            start_node=parsed_dict["start_node"],
            line=parsed_dict["line"]
        )
    elif "from_node_name" in parsed_dict and "to_node_name" in parsed_dict:
        return SingleNodeTransition(
            from_node_name=parsed_dict["from_node_name"],
            to_node_name=parsed_dict["to_node_name"],
            line=parsed_dict["line"]
        
        )
    
    # Multiple source nodes to single node
    elif "from_nodes" in parsed_dict and "to_node_name" in parsed_dict:
        return MultiSourceTransition(
            from_nodes=parsed_dict["from_nodes"],
            to_node_name=parsed_dict["to_node_name"],
            line=parsed_dict["line"]
        )
    
    # Single node to multiple target nodes
    elif "from_node_name" in parsed_dict and "to_nodes" in parsed_dict and "to_routing_function" not in parsed_dict:
        return MultiTargetTransition(
            from_node_name=parsed_dict["from_node_name"],
            to_nodes=parsed_dict["to_nodes"],
            line=parsed_dict["line"]
        
        )
    
    # Routing function
    elif "from_node_name" in parsed_dict and "to_routing_function" in parsed_dict:
        return RoutingTransition(
            from_node_name=parsed_dict["from_node_name"],
            to_routing_function=parsed_dict["to_routing_function"],
            to_nodes=parsed_dict["to_nodes"],
            line=parsed_dict["line"]
        
        )
    
    # Worker
    elif "from_node_name" in parsed_dict and "to_worker" in parsed_dict:
        return WorkerTransition(
            from_node_name=parsed_dict["from_node_name"],
            to_worker=parsed_dict["to_worker"],
            state_class_name=parsed_dict["state_class_name"],
            field_name=parsed_dict["field_name"],
            line=parsed_dict["line"]
        
        )
    
    else:
        raise ValueError(f"Unrecognized transition format: {parsed_dict}")

def parse_graph(graph_text):
    """
    Parse an entire graph in DSL format into a list of transition objects.
    
    Args:
        graph_text (str): The complete graph text in DSL format
        
    Returns:
        List[Union[SingleNodeTransition, MultiSourceTransition, MultiTargetTransition, 
                  RoutingTransition, WorkerTransition]]: List of transition objects
    """
    transitions = []
    lines = graph_text.strip().split('\n')
    
    # Skip comment lines and process valid transitions
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        # Skip comment lines (starting with #)
        if line.strip().startswith('#'):
            continue
            
        # Parse the transition line
        try:
            transition = parse_transition(line, is_first_line = len(transitions)==0)
            transitions.append(transition)
        except ValueError as e:
            print(f"Warning: Could not parse line '{line}': {e}")
    
    return transitions



@dataclass
class GraphValidationResult:
    """Represents the result of validating a graph."""
    is_valid: bool
    state_class_name: Optional[str] = None
    start_field: Optional[str] = None
    start_node: Optional[str] = None
    source_nodes: Set[str] = None
    dest_nodes: Set[str] = None
    worker_nodes: Set[str] = None
    router_functions: Set[tuple] = None
    validation_messages: List[str] = None
    orphan_source_nodes: Set[str] = None
    orphan_dest_nodes: Set[str] = None
    
    def __post_init__(self):
        # Initialize any None collections as empty
        if self.source_nodes is None:
            self.source_nodes = set()
        if self.dest_nodes is None:
            self.dest_nodes = set()
        if self.worker_nodes is None:
            self.worker_nodes = set()
        if self.router_functions is None:
            self.router_functions = set()
        if self.validation_messages is None:
            self.validation_messages = []
        if self.orphan_source_nodes is None:
            self.orphan_source_nodes = set()
        if self.orphan_dest_nodes is None:
            self.orphan_dest_nodes = set()

    # human readable format with one line per field
    def __str__(self):
        return f"""
Graph Validation Result:
    is_valid: {self.is_valid}
    validation_messages: {self.validation_messages}
    orphan_source_nodes: {self.orphan_source_nodes}
    orphan_dest_nodes: {self.orphan_dest_nodes}
Graph State:
    state_class_name: {self.state_class_name}
    start_field: {self.start_field}
Nodes:
    start_node: {self.start_node}
    source_nodes: {sorted(self.source_nodes)}
    dest_nodes: {sorted(self.dest_nodes)}
    worker_nodes: {sorted(self.worker_nodes)}
Conditional Edges:
    router_functions: {sorted(self.router_functions)}
"""

def validate_graph(transitions):
    """
    Validates a graph represented by a list of transitions.
    
    Args:
        transitions: List of transition objects
        
    Returns:
        GraphValidationResult: Object containing validation results
    """
    if not transitions:
        return GraphValidationResult(
            is_valid=False,
            validation_messages=["Graph is empty"]
        )
    
    result = GraphValidationResult(is_valid=True)
    
    # Extract state class name and starting node
    result.state_class_name = transitions[0].state_class_name
    result.start_node = transitions[0].start_node
    result.dest_nodes.add(transitions[0].start_node)
    
    # Check if state class name contains a field
    if '.' in result.state_class_name:
        result.state_class_name, result.start_field = result.state_class_name.split('.')
    
    # Collect all nodes and functions
    for transition in transitions[1:]:
        result.source_nodes.update(transition.get_source_nodes())
        result.dest_nodes.update(transition.get_dest_nodes())
        result.worker_nodes.update(transition.get_worker_nodes())
        result.router_functions.update(transition.get_router_functions())
    
    # Find orphan nodes
    result.orphan_source_nodes = result.source_nodes - result.dest_nodes
    result.orphan_dest_nodes = result.dest_nodes - result.source_nodes - {'END'}
    
    # Add validation messages for orphan nodes
    if result.orphan_source_nodes:
        print("FOUND ORPHAN SOURCE NODES")
        print(result.source_nodes, result.dest_nodes, result.orphan_source_nodes)
        result.validation_messages.append(f"Orphan source nodes: {result.orphan_source_nodes}")
        result.is_valid = False
    
    if result.orphan_dest_nodes:
        result.validation_messages.append(f"Orphan destination nodes: {result.orphan_dest_nodes}")
        result.is_valid = False
    
    return result

class FileOverwriteManager:
    def __init__(self, file_path, file_description="file"):
        self.file_path = Path(file_path)
        self.file_description = file_description
        self.should_continue = True
    def __enter__(self):
        if self.file_path.exists():
            print(f"{Fore.YELLOW}{self.file_description} already exists at {self.file_path}.{Style.RESET_ALL}")
            overwrite = questionary.confirm(
                f"Overwrite?"
            ).ask()
            if not overwrite:
                print(f"{Fore.RED}Aborted by user. {self.file_description} will not be overwritten.{Style.RESET_ALL}")
                self.should_continue = False
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.file_path.exists():
            print(f"{Fore.RED}Error: {self.file_description} was not created at {self.file_path}{Style.RESET_ALL}")
            sys.exit(1)

