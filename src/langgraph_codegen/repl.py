from colorama import Fore, Style
from typing import Set, Dict, Callable
from langgraph_codegen.gen_graph import gen_graph, gen_nodes, gen_state, gen_conditions, validate_graph

class GraphDesignREPL:
    """Interactive REPL for designing LangGraph workflows and code."""
    
    EXIT_COMMANDS: Set[str] = {'quit', 'q', 'x', 'exit', 'bye'}
    
    def __init__(self, graph_file: str, graph_spec: str):
        """Initialize REPL with graph specification.
        
        Args:
            graph_file: Name of the graph file
            graph_spec: Contents of the graph specification
        """
        self.prompt = f"{Fore.BLUE}lgcodegen: {Style.RESET_ALL}"
        self.graph_name = graph_file.split('.')[0]  # Remove extension if present
        self.graph_spec = graph_spec
        self.graph = validate_graph(graph_spec)
        
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
                # Get input with the prompt
                user_input = input(self.prompt).strip()
                
                # Check for exit command
                if user_input.lower() in self.EXIT_COMMANDS:
                    print("Goodbye!")
                    break
                
                # Handle generation commands
                if user_input in self.commands:
                    result = self.commands[user_input]()
                    if result:
                        print(f"\n{result}\n")
                    else:
                        print(f"\n{Fore.RED}Unable to generate code for {user_input}{Style.RESET_ALL}\n")
                elif user_input:
                    print(f"Unknown command: {user_input}")
                    print("Available commands: --graph, --nodes, --conditions, --state, --code")
                    
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
                continue
            except EOFError:
                print("\nGoodbye!")
                break