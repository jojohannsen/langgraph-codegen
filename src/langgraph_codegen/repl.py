from colorama import Fore, Style
from typing import Set, Dict, Callable
from langgraph_codegen.gen_graph import gen_graph, gen_nodes, gen_state, gen_conditions, validate_graph
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel
from typing import Literal
from langchain_core.prompts import PromptTemplate

# Initialize the global LLM instance
anthropic_llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")

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

Current Graph Specification:
{graph_spec}

Classify this request into one of the above categories."""

# Specific prompts for each type of query
PROMPT_TEMPLATES = {
    "nodes": """Focus on the node-specific aspects of the graph design.
Consider node creation, modification, inputs/outputs, and relationships between nodes.

User Request: {user_input}

Current Graph Specification:
{graph_spec}

Response:""",

    "conditions": """Focus on the conditional logic and flow control aspects of the graph.
Consider edge conditions, branching logic, and transition rules.

User Request: {user_input}

Current Graph Specification:
{graph_spec}

Response:""",

    "graph": """Focus on the overall graph structure and workflow design.
Consider the high-level architecture, data flow, and graph composition.

User Request: {user_input}

Current Graph Specification:
{graph_spec}

Response:""",

    "state": """Focus on state management and transitions in the graph.
Consider state definitions, modifications, and how state flows through the graph.

User Request: {user_input}

Current Graph Specification:
{graph_spec}

Response:""",

    "general": """Provide general guidance on graph design based on the user's request.

User Request: {user_input}

Current Graph Specification:
{graph_spec}

Response:"""
}

def graph_design_agent(user_input: str, graph_spec: str) -> str:
    """Process natural language input about graph design using Claude with dynamic prompt selection.
    
    Args:
        user_input: The user's natural language input
        graph_spec: The current graph specification
        
    Returns:
        A string response about the graph design
    """
    # Create the classifier chain
    classifier_prompt = PromptTemplate.from_template(CLASSIFIER_PROMPT)
    classifier_chain = (
        classifier_prompt 
        | anthropic_llm.with_structured_output(GraphDesignType)
    )
    
    # Classify the input
    classification = classifier_chain.invoke({
        "user_input": user_input,
        "graph_spec": graph_spec
    })
    
    # Get the appropriate prompt template
    selected_prompt = PromptTemplate.from_template(
        PROMPT_TEMPLATES[classification.design_type]
    )
    
    # Create and run the response chain
    response_chain = selected_prompt | anthropic_llm
    response = response_chain.invoke({
        "user_input": user_input,
        "graph_spec": graph_spec
    })
    
    return response


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
        self.prompt = f"{Fore.BLUE}lgcodegen: {Style.RESET_ALL}"
        self.graph_name = graph_file.split('.')[0]  # Remove extension if present
        self.graph_spec = graph_spec
        self.graph = validate_graph(graph_spec)
        self.print_code = code_printer
        
        # Map commands to their corresponding generation functions
        self.commands: Dict[str, Callable] = {
            '--graph': lambda: gen_graph(self.graph_name, self.graph_spec),
            '--nodes': lambda: gen_nodes(self.graph['graph']) if 'graph' in self.graph else None,
            '--conditions': lambda: gen_conditions(self.graph_spec),
            '--state': lambda: gen_state(self.graph_spec),
            '--code': self._generate_complete_code
        }
    
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
    
    def run(self):
        """Start the REPL loop"""
        print(f"\nWelcome to the LangGraph Design REPL!")
        print(f"Working with graph: {self.graph_name}")
        print("Available commands: --graph, --nodes, --conditions, --state, --code")
        print("Type 'quit' to exit\n")
        
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
                    result = self.commands[user_input]()
                    if result:
                        print("\n")
                        self.print_code(result)  # Use the passed-in printer function
                        print("\n")
                    else:
                        print(f"\n{Fore.RED}Unable to generate code for {user_input}{Style.RESET_ALL}\n")
                elif user_input.startswith('-'):
                    print(f"Unknown command: {user_input}")
                    print("Available commands: --graph, --nodes, --conditions, --state, --code")
                elif user_input:  # Only process non-empty input
                    response = graph_design_agent(user_input, self.graph_spec)
                    print(f"\n{response}\n")
                    
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
                continue
            except EOFError:
                print("\nGoodbye!")
                break