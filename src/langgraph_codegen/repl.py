from pathlib import Path
from colorama import Fore, Style
from typing import Set, Dict, Callable
from langgraph_codegen.gen_graph import gen_graph, gen_nodes, gen_state, gen_conditions, validate_graph
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from langchain_anthropic import AnthropicLLM
from pydantic import BaseModel
from typing import Literal
from langchain_core.prompts import PromptTemplate
import textwrap
import os
from langchain_openai import ChatOpenAI

def get_available_models(api_key_name: str) -> list[str]:
    """Returns available models for the given API provider.
    
    Args:
        api_key_name: Name of the API key (e.g. 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY')
        
    Returns:
        List of available model names
    """
    if api_key_name == "ANTHROPIC_API_KEY":
        return ["claude-3-5-haiku-latest", "claude-3-5-sonnet-latest", "claude-3-opus-latest)"]
    elif api_key_name == "OPENAI_API_KEY":
        return ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "o1-mini", "o1-preview"]
    return []

def get_llm(api_keys: Dict[str, bool]) -> ChatAnthropic | ChatOpenAI:
    """Interactive function to select and configure an LLM based on available API keys.
    
    Args:
        api_keys: Dictionary of API key names and their availability status
        
    Returns:
        Configured LLM instance (either ChatAnthropic or ChatOpenAI)
    """
    available_keys = [key for key, available in api_keys.items() if available]
    
    if not available_keys:
        raise ValueError("No API keys available")
        
    selected_key = available_keys[0]
    
    # If multiple keys available, ask user which one to use
    if len(available_keys) > 1:
        print("\nAvailable API providers:")
        for i, key in enumerate(available_keys, 1):
            print(f"{i}. {key.replace('_API_KEY', '')}")
        
        while True:
            try:
                choice = int(input("\nSelect provider number: "))
                if 1 <= choice <= len(available_keys):
                    selected_key = available_keys[choice - 1]
                    break
                print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a number.")
    
    # Get available models for selected provider
    models = get_available_models(selected_key)
    
    print("\nAvailable models:")
    for i, model in enumerate(models, 1):
        print(f"{i}. {model}")
    
    selected_model = models[0]  # Default to first model
    while True:
        try:
            choice = int(input("\nSelect model number (or press Enter for default): ") or "1")
            if 1 <= choice <= len(models):
                selected_model = models[choice - 1]
                break
            print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a number.")
    
    # Initialize appropriate LLM based on selected provider
    if selected_key == "ANTHROPIC_API_KEY":
        return ChatAnthropic(model=selected_model)
    elif selected_key == "OPENAI_API_KEY":
        return ChatOpenAI(model=selected_model)
        
    raise ValueError(f"Unsupported API provider: {selected_key}")

def format_state_machine(graph_dict):
    output = []
    
    # List all nodes
    nodes = list(graph_dict.keys())
    output.append(f"Nodes: {', '.join(nodes)}")
    
    # State type
    first_node = next(iter(graph_dict.values()))
    output.append(f"\nThe graph keeps its state in {first_node['state']}")
    
    # Find conditional and unconditional nodes
    conditional_nodes = []
    unconditional_nodes = []
    
    for node, data in graph_dict.items():
        if len(data['edges']) > 1:
            conditional_nodes.append(node)
        elif len(data['edges']) == 1 and data['edges'][0]['condition'] == 'true_fn':
            unconditional_nodes.append(node)
    
    output.append(f"\nNodes with conditional edges: {', '.join(conditional_nodes)}")
    output.append(f"Nodes with a single unconditional edge: {', '.join(unconditional_nodes)}")
    
    # Format transitions for each node
    output.append("\nTransitions:")
    for node, data in graph_dict.items():
        if len(data['edges']) == 1 and data['edges'][0]['condition'] == 'true_fn':
            output.append(f"Node {node} transitions to Node {data['edges'][0]['destination']}")
        else:
            for edge in data['edges']:
                output.append(f"Node {node} transitions to Node {edge['destination']} when condition {edge['condition']} is True")
    
    return "\n".join(output), nodes, conditional_nodes, unconditional_nodes

class GraphDesignType(BaseModel):
    """Classification for different types of graph design queries"""
    design_type: Literal["nodes", "conditions", "graph", "state", "general"]

# Classifier prompt to determine the type of graph design query
CLASSIFIER_PROMPT = """Given a user's question or request about graph design, determine which category it best fits into.
Choose from these categories:
- nodes: Questions about node creation, modification, or node relationships
- conditions: Questions about conditional logic, edge conditions, or flow control
- graph: Questions about overall graph structure or workflow
- state: Questions about state management or state transitions
- general: General questions that don't fit the above categories

User Request: {user_input}

<NODES>
{nodes}
</NODES>
<CONDITIONS>
{conditions}
</CONDITIONS>
<STATE>
{state}
</STATE>

<GRAPH_SPEC>
{graph_spec}
</GRAPH_SPEC>
Classify this request into one of the above categories."""

# Specific prompts for each type of query
PROMPT_TEMPLATES = {
    "nodes": """We have a user request about nodes.
Answer this request providing only information about the nodes, do not discuss any other
aspects of the graph unless explicitly requested.  For example, if the user asks about 
nodes, just give them a minimal list of nodes. 

Some questions may be about specific nodes, so check for that, and in those cases 
see what the graph description says about that node.

In general, keep the response concise and to the point.

Respond only with text, do not use html or markdown.

User Request: {user_input}

<NODES>
{nodes}
</NODES>

<GRAPH_SPEC>
{graph_spec}
</GRAPH_SPEC>

<GRAPH_DESCRIPTION>
{graph_description}
</GRAPH_DESCRIPTION>

Response:""",

    "conditions": """We have a user request regarding conditional edges.

The transitions are discussed in the GRAPH_DESCRIPTION section.

In general, keep the response concise and to the point.

Respond only with text, do not use html or markdown.
User Request: {user_input}

<GRAPH_SPEC>
{graph_spec}
</GRAPH_SPEC>

<GRAPH_DESCRIPTION>
{graph_description}
</GRAPH_DESCRIPTION>

Response:""",

    "graph": """The user has a general question about the graph.  Use the
graph specification and description to answer the question.

Use the GRAPH_SPEC section below if there are references to a 'graph specification' or a 'dsl'.

In general, keep the response concise and to the point.

Respond only with text, do not use html or markdown.

User Request: {user_input}

<GRAPH_SPEC>
{graph_spec}
</GRAPH_SPEC>

<GRAPH_DESCRIPTION>
{graph_description}
</GRAPH_DESCRIPTION>

Response:""",

    "state": """User Request: {user_input}

<GRAPH_SPEC>
{graph_spec}
</GRAPH_SPEC>

<GRAPH_DESCRIPTION>
{graph_description}
</GRAPH_DESCRIPTION>

Response:""",

    "general": """The user has a general question about the graph.  Use the
graph specification and description to answer the question.

Use the GRAPH_SPEC section below if there are references to a 'graph specification' or a 'dsl'.

In general, keep the response concise and to the point.

Respond only with text, do not use html or markdown.

User Request: {user_input}

<GRAPH_SPEC>
{graph_spec}
</GRAPH_SPEC>

<GRAPH_DESCRIPTION>
{graph_description}
</GRAPH_DESCRIPTION>

Response:""",
}

def graph_design_agent(user_input: str, graph_spec: str, graph_dict: dict, llm: ChatAnthropic) -> str:
    """Process natural language input about graph design using Claude with dynamic prompt selection.
    
    Args:
        user_input: The user's natural language input
        graph_spec: The current graph specification
        graph_dict: The graph dictionary from the specification
        llm: The LLM instance to use for the graph design
        
    Returns:
        A string response about the graph design
    """
    # Format the state machine and get all return values
    graph_description, nodes, conditional_nodes, unconditional_nodes = format_state_machine(graph_dict)

    # Create the classifier chain
    classifier_prompt = PromptTemplate.from_template(CLASSIFIER_PROMPT)
    classifier_chain = (
        classifier_prompt 
        | llm.with_structured_output(GraphDesignType)
    )
    
    # Classify the input
    classification = classifier_chain.invoke({
        "user_input": user_input,
        "graph_spec": graph_spec,
        "graph_description": graph_description,
        "nodes": nodes,
        "conditions": conditional_nodes,
        "state": graph_description  # Using full description for state context
    })
    print(f"Classification: {classification}")
    # Get the appropriate prompt template
    selected_prompt = PromptTemplate.from_template(
        PROMPT_TEMPLATES[classification.design_type]
    )
    
    # Create and run the response chain
    response_chain = selected_prompt | llm
    response = response_chain.invoke({
        "user_input": user_input,
        "graph_spec": graph_spec,
        "graph_description": graph_description,
        "nodes": nodes,
        "conditions": conditional_nodes,
        "state": graph_description  # Using full description for state context
    })
    
    return classification, response


class GraphDesignREPL:
    """Interactive REPL for designing LangGraph workflows and code."""
    
    EXIT_COMMANDS: Set[str] = {'quit', 'q', 'x', 'exit', 'bye'}
    
    def __init__(self, graph_file: str, graph_spec: str, code_printer: Callable[[str], None]):
        """Initialize REPL with graph specification.
        
        Args:
            graph_file: Name of the graph file
            graph_spec: Contents of the graph specification
            code_printer: Function to print code with syntax highlighting
        """
        # Check required environment variables
        self.required_env_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
        self.api_keys = {var: var in os.environ for var in self.required_env_vars}
        
        self.prompt = f"{Fore.BLUE}lgcodegen: {Style.RESET_ALL}"
        # Convert any dashes to underscores in graph name for Python compatibility
        self.graph_name = graph_file.split('.')[0].replace('-', '_')  # Remove extension and convert dashes
        self.graph_spec = graph_spec
        self.graph = validate_graph(graph_spec)
        self.print_code = code_printer
        
        # Map commands to their corresponding generation functions
        self.command_names = [
            'graph', 
            'nodes', 
            'conditions', 
            'state', 
            'code', 
            'dsl',
            'save'
        ]
        self.commands = {}
        for name in self.command_names:
            # Handle no prefix, single dash, and double dash
            for prefix in ['', '-', '--']:
                cmd = prefix + name
                # Strip any dashes from the command to get the base command
                base_cmd = cmd.lstrip('-')
                self.commands[cmd] = self._get_command_function(base_cmd)
        
        self.llm = None
    
    def _get_llm(self):
        """Get or initialize the LLM instance."""
        if self.llm is None:
            try:
                self.llm = get_llm(self.api_keys)
            except ValueError as e:
                print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
                return None
        return self.llm
    
    def _get_command_function(self, command: str) -> Callable:
        """Return the appropriate function for a command."""
        command_map = {
            'graph': lambda: gen_graph(self.graph_name, self.graph_spec),
            'nodes': lambda: gen_nodes(self.graph['graph']) if self.graph.get('graph') else None,
            'conditions': lambda: gen_conditions(self.graph_spec),
            'state': lambda: gen_state(self.graph_spec),
            'code': self._generate_complete_code,
            'dsl': lambda: f"{self.graph_spec}",
            'save': lambda: (_ for _ in ()).throw(ValueError("should not be called from here"))
        }
        return command_map[command]
    
    def _save_code(self, file_name: str, code: str):
        """Save the code to a file."""
        if file_name:
            folder_name = file_name[:file_name.rfind('_')]
            # Create the folder if it doesn't exist
            Path(folder_name).mkdir(parents=True, exist_ok=True)
            # Use the file name as is, preserving the extension
            local_path = Path(folder_name) / file_name
            with open(local_path, 'w') as f:
                f.write(code)
            print(f"Saved code to {local_path}")
        else:
            print(f"Unable to save code to {file_name}")
    
    def _get_file(self, user_input: str) -> str:
        """Get the file name from the user input."""
        high_level_command = user_input.split(' ')[0]
        high_level_command = high_level_command.lower()
        if high_level_command == "code":
            return f"{self.graph_name}_main.py"
        elif high_level_command == "dsl":
            return f"{self.graph_name}_{high_level_command}.txt"
        elif high_level_command in self.command_names:
            return f"{self.graph_name}_{high_level_command}.py"
        return None
    
    def _generate_complete_code(self) -> str:
        """Generate complete runnable code."""
        if 'graph' not in self.graph:
            return None
            
        complete_code = []
        complete_code.append("""from typing import Dict, TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, Graph
from langchain_core.messages.tool import ToolMessage
from langchain_core.runnables.config import RunnableConfig
from operator import itemgetter
""")
        complete_code.append(gen_state(self.graph_spec))
        complete_code.append(gen_nodes(self.graph['graph']))
        complete_code.append(gen_conditions(self.graph_spec))
        complete_code.append(gen_graph(self.graph_name, self.graph_spec))
        
        return "\n\n".join(complete_code)
    
    def _print_help(self):
        """Print available commands."""
        print("\nExperimental REPL Mode")
        print("Available commands: graph, nodes, conditions, state, code, dsl")
        print("Commands can be used with or without dashes (e.g. 'graph', '-graph', or '--graph')")

    def run(self):
        """Start the REPL loop"""
        print(f"\nWelcome to the LangGraph Design REPL!")
        print(f"Working with graph: {self.graph_name}")
        self._print_help()
        print("Type 'quit' to exit\n")
        last_code = "# No code has been shown yet"
        last_code_user_input = None
        while True:
            try:
                # Get input with the prompt and strip whitespace
                user_input = input(self.prompt).strip()
                
                # Check for exit command
                if user_input.lower() in self.EXIT_COMMANDS:
                    print("Goodbye!")
                    break
                
                # Handle generation commands
                if user_input in self.commands:
                    if user_input.lower() == 'save':
                        if last_code_user_input:
                            file_name = self._get_file(last_code_user_input)
                            self._save_code(file_name, last_code)
                        else:
                            print(f"\n{Fore.RED}No code has been generated yet to save{Style.RESET_ALL}\n")
                    else:
                        result = self.commands[user_input]()
                        if result:
                            print("\n")
                            last_code = result
                            last_code_user_input = user_input
                            self.print_code(result)  # Use the passed-in printer function
                            print("\n")
                        else:
                            print(f"\n{Fore.RED}Unable to generate code for {user_input}{Style.RESET_ALL}\n")
                elif user_input.endswith('help'):
                    self._print_help()
                elif user_input.startswith('-'):
                    print(f"Unknown command: {user_input}")
                    self._print_help()
                elif user_input:  # Only process non-empty input
                    llm = self._get_llm()
                    if llm:
                        classification, response = graph_design_agent(
                            user_input, 
                            self.graph_spec, 
                            self.graph.get("graph", {}),
                            llm
                        )
                        if classification.design_type in ["graph", "conditions"]:
                            print(f"\n{Fore.CYAN}{self.graph_spec}{Style.RESET_ALL}\n")
                        txt = "\n".join(textwrap.wrap(response.content, width=80, expand_tabs=False,replace_whitespace=False))
                        print(f"\n{Fore.BLUE}{txt}{Style.RESET_ALL}\n")
                    else:
                        self._print_help()
                    
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
                continue
            except EOFError:
                print("\nGoodbye!")
                break