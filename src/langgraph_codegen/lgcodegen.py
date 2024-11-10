#!/usr/bin/env python3

import sys
import argparse
import os
from pathlib import Path
from langgraph_codegen.gen_graph import gen_graph, gen_nodes, gen_state,gen_conditions, validate_graph
from colorama import init, Fore, Style
from rich import print as rprint
from rich.syntax import Syntax
import shutil
from typing import List, Set
from langgraph_codegen.repl import GraphDesignREPL

# Initialize colorama (needed for Windows)
init()


def print_python_code(code_string, show_line_numbers=False):
    """
    Print Python code with syntax highlighting to the terminal
    
    Args:
        code_string (str): The Python code to print
        show_line_numbers (bool): Whether to show line numbers in the output
    """
    # Create a Syntax object with Python lexer
    syntax = Syntax(code_string, "python", theme="monokai", line_numbers=show_line_numbers)
    
    # Print the highlighted code
    rprint(syntax)

def get_example_path(filename):
    """Get the full path to an example file."""
    try:
        # Get the package directory
        import langgraph_codegen
        package_dir = Path(os.path.dirname(langgraph_codegen.__file__))
        if '.' not in filename:
            filename = filename + '.graph'
        example_path = package_dir / 'data' / 'examples' / filename
        
        if example_path.exists():
            return str(example_path)
        return None
    except Exception as e:
        print(f"Error finding example: {str(e)}", file=sys.stderr)
        return None

def list_examples():
    """List all available example graph files."""
    print(f"\n{Fore.LIGHTBLACK_EX}Example graphs (these are text files):{Style.RESET_ALL}\n")
    
    examples = get_available_examples()
    if not examples:
        print(f"{Fore.YELLOW}No examples found{Style.RESET_ALL}")
        return
        
    for example in sorted(examples):
        name = example.split('/')[-1]  # Get just the filename
        print(f" {Fore.BLUE}{name}{Style.RESET_ALL}")
    
    print(f"\n{Fore.LIGHTBLACK_EX}View a graph with: {Fore.BLUE}lgcodegen <graph_name>{Style.RESET_ALL}\n")

def show_example_content(example_name):
    """Show the content of an example graph file."""
    # Get base name (strip everything after the '.')
    base_name = example_name.split('.')[0]
    
    # Check for local copy first
    local_path = Path(base_name) / f"{base_name}.txt"
    if local_path.exists():
        print(f"{Fore.GREEN}Using local copy...{Style.RESET_ALL}")
        try:
            with open(local_path, 'r') as f:
                content = f.read()
            print(f"{Fore.BLUE}{content}{Style.RESET_ALL}")
            return
        except Exception as e:
            print(f"{Fore.RED}Error reading local copy: {str(e)}{Style.RESET_ALL}", file=sys.stderr)
            sys.exit(1)
    
    # If no local copy, check examples
    example_path = get_example_path(example_name)
    if not example_path:
        print(f"{Fore.RED}Error: Example '{example_name}' not found{Style.RESET_ALL}", file=sys.stderr)
        print(f"{Fore.YELLOW}Use --list-examples to see available examples{Style.RESET_ALL}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(example_path, 'r') as f:
            content = f.read()
        print(f"{Fore.BLUE}{content}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error reading example: {str(e)}{Style.RESET_ALL}", file=sys.stderr)
        sys.exit(1)

def get_available_examples():
    """Get a list of available example files."""
    try:
        import langgraph_codegen
        package_dir = Path(os.path.dirname(langgraph_codegen.__file__))
        examples_dir = package_dir / 'data' / 'examples'
        
        if not examples_dir.exists():
            return []
            
        # Get all files in the examples directory
        examples = []
        for file in examples_dir.glob('*'):
            if file.is_file():
                examples.append(str(file))
        return examples
    except Exception as e:
        print(f"{Fore.RED}Error listing examples: {str(e)}{Style.RESET_ALL}", file=sys.stderr)
        return []

def ensure_graph_folder(graph_name: str) -> Path:
    """Create a folder for the graph if it doesn't exist.
    
    Args:
        graph_name (str): Name of the graph
        
    Returns:
        Path: Path to the graph folder
    """
    folder = Path(graph_name)
    if not folder.exists():
        print(f"{Fore.GREEN}Creating folder {graph_name}{Style.RESET_ALL}")
        folder.mkdir(parents=True)
    return folder

def save_graph_spec(folder: Path, graph_name: str, graph_spec: str):
    """Save the graph specification to a text file.
    
    Args:
        folder (Path): Folder to save the file in
        graph_name (str): Name of the graph
        graph_spec (str): Graph specification content
    """
    spec_file = folder / f"{graph_name}.txt"
    spec_file.write_text(graph_spec)
    print(f"{Fore.GREEN}Saved graph specification to {spec_file}{Style.RESET_ALL}")

def main():
    parser = argparse.ArgumentParser(description="Generate LangGraph code from graph specification")
    
    # repl and code display options
    parser.add_argument('-i', '--interactive', '--repl', action='store_true', 
                       help='Start interactive graph design REPL', dest='interactive')
    parser.add_argument('-l', '--line-numbers', action='store_true', help='Show line numbers in generated code')
    
    # Add the options
    parser.add_argument('--list', action='store_true', help='List available example graphs')
    parser.add_argument('--graph', action='store_true', help='Generate graph code')
    parser.add_argument('--nodes', action='store_true', help='Generate node code')
    parser.add_argument('--conditions', action='store_true', help='Generate condition code')
    parser.add_argument('--state', action='store_true', help='Generate state code')
    parser.add_argument('--code', action='store_true', help='Generate runnable graph')
     
    # Single required argument
    parser.add_argument('graph_file', nargs='?', help='Path to the graph specification file')

    args = parser.parse_args()

    # Handle REPL mode - now requires graph_file
    if args.interactive:
        if not args.graph_file:
            print(f"{Fore.RED}Error: Interactive mode requires a graph file{Style.RESET_ALL}")
            sys.exit(1)
            
        # Get the graph file content
        example_path = get_example_path(args.graph_file)
        file_path = example_path if example_path else args.graph_file
        
        try:
            with open(file_path, 'r') as f:
                graph_spec = f.read()
        except FileNotFoundError:
            print(f"{Fore.RED}Error: File not found: {args.graph_file}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Use --list-examples to see available examples{Style.RESET_ALL}")
            sys.exit(1)
            
        repl = GraphDesignREPL(args.graph_file, graph_spec, print_python_code)
        repl.run()
        return

    if args.list:
        list_examples()
        return

    # If no graph file provided, show help
    if not args.graph_file:
        parser.print_help()
        sys.exit(1)

    try:
        # First try to find the file as an example
        example_path = get_example_path(args.graph_file)
        file_path = example_path if example_path else args.graph_file
            
        # Read the specification file
        with open(file_path, 'r') as f:
            graph_spec = f.read()

        # If no generation flags are set, just show the file contents
        if not (args.graph or args.nodes or args.conditions or args.state or args.code):
            print(f"{Fore.BLUE}{graph_spec}{Style.RESET_ALL}")
            return
            
        # Get graph name from file name (without extension)
        graph_name = Path(args.graph_file).stem
        
        # Validate the graph specification
        validation_result = validate_graph(graph_spec)
        if "error" in validation_result:
            print(f"{Fore.RED}Error in graph specification:{Style.RESET_ALL}\n{validation_result['error']}", file=sys.stderr)
            print(f"\n{Fore.YELLOW}Suggested solutions:{Style.RESET_ALL}\n{validation_result['solution']}", file=sys.stderr)
            sys.exit(1)

        # Generate the requested code
        graph = validate_graph(graph_spec)
        state_class = graph.get('graph', {}).get('START', {}).get('state')
        if args.code:
            # Get graph name from file name (without extension)
            graph_name = Path(args.graph_file).stem
            
            # Create folder and determine output file paths
            graph_folder = ensure_graph_folder(graph_name)
            output_file = graph_folder / f"{graph_name}.py"
            
            # Check if file exists and prompt for overwrite
            if output_file.exists():
                response = input(f"{Fore.GREEN}File {output_file} exists. Overwrite? (y/n): {Style.RESET_ALL}")
                if response.lower() != 'y':
                    print(f"{Fore.LIGHTRED_EX}Code generation cancelled.{Style.RESET_ALL}")
                    sys.exit(0)
            
            # Save the graph specification
            save_graph_spec(graph_folder, graph_name, graph_spec)
            
            # Collect all code components
            complete_code = []
            
            # Add imports
            complete_code.append("""from typing import Dict, TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, Graph
from langchain_core.messages.tool import ToolMessage
from langchain_core.runnables.config import RunnableConfig
from operator import itemgetter
""")
            
            # Add components in specific order
            if 'graph' in graph:
                complete_code.append(gen_state(graph_spec))
                complete_code.append(gen_nodes(graph['graph']))
                complete_code.append(gen_conditions(graph_spec))
                ggresult = gen_graph(graph_name, graph_spec)
                complete_code.append(ggresult)
                
                # Add main section
                main_section = f"""
import random
def random_one_or_zero():
    return random.choice([False, True])

if __name__ == "__main__":
    import sys
    
    # Create the graph
    workflow = {graph_name}
    config = RunnableConfig(configurable={{"thread_id": "1"}})
    for output in workflow.stream(initial_state_{state_class}(), config=config):
        print(f"\\n    {{output}}\\n")
    print("DONE STREAMING, final state:")
    print(workflow.get_state(config))
"""
                complete_code.append(main_section)
                # Join all code components and write to file
                full_code = "\n\n".join(complete_code)
                output_file.write_text(full_code)
                print(f"{Fore.GREEN}Generated {output_file}{Style.RESET_ALL}")
                return
                
        # Handle individual component generation as before
        if args.graph:
            print_python_code(gen_graph(graph_name, graph_spec), args.line_numbers)
        if args.nodes:
            if 'graph' in graph:
                print_python_code(gen_nodes(graph['graph']), args.line_numbers)
        if args.conditions:
            if 'graph' in graph:
                print_python_code(gen_conditions(graph_spec), args.line_numbers)
        if args.state:
            if 'graph' in graph:
                print_python_code(gen_state(graph_spec), args.line_numbers)
        if 'errors' in graph:
            print(f"{Fore.RED}Errors in graph specification: \n\n{graph['errors']}\n\n{Fore.RESET}", file=sys.stderr)
            
    except FileNotFoundError:
        print(f"{Fore.RED}Error: File not found: {args.graph_file}{Style.RESET_ALL}", file=sys.stderr)
        print(f"{Fore.YELLOW}Use --list-examples to see available example graphs{Style.RESET_ALL}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()