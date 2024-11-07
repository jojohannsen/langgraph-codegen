#!/usr/bin/env python3

import sys
import argparse
import os
from pathlib import Path
from langgraph_codegen.gen_graph import gen_graph, gen_nodes, gen_state,gen_conditions, validate_graph
from colorama import init, Fore, Style
from rich import print as rprint
from rich.syntax import Syntax

# Initialize colorama (needed for Windows)
init()


def print_python_code(code_string):
    """
    Print Python code with syntax highlighting to the terminal
    
    Args:
        code_string (str): The Python code to print
    """
    # Create a Syntax object with Python lexer
    syntax = Syntax(code_string, "python", theme="monokai", line_numbers=True)
    
    # Print the highlighted code
    rprint(syntax)

def get_example_path(filename):
    """Get the full path to an example file."""
    try:
        # Get the package directory
        import langgraph_codegen
        package_dir = Path(os.path.dirname(langgraph_codegen.__file__))
        example_path = package_dir / 'data' / 'examples' / filename
        
        if example_path.exists():
            return str(example_path)
        return None
    except Exception as e:
        print(f"Error finding example: {str(e)}", file=sys.stderr)
        return None

def list_examples():
    """List all available example graph files."""
    print(f"\n{Fore.LIGHTBLACK_EX}Available example graphs:{Style.RESET_ALL}\n")
    
    examples = get_available_examples()
    if not examples:
        print(f"{Fore.YELLOW}No examples found{Style.RESET_ALL}")
        return
        
    for example in sorted(examples):
        name = example.split('/')[-1]  # Get just the filename
        print(f" {Fore.GREEN}{name}{Style.RESET_ALL}")
    
    print(f"\n{Fore.LIGHTBLACK_EX}View a graph with: {Fore.BLUE}lgcodegen --example <graph_name>{Style.RESET_ALL}\n")

def show_example_content(example_name):
    """Show the content of an example graph file."""
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

def main():
    parser = argparse.ArgumentParser(description="Generate LangGraph code from graph specification")
    
    # Add the options
    parser.add_argument('--list', action='store_true', help='List available example graphs')
    parser.add_argument('--graph', action='store_true', help='Generate graph code')
    parser.add_argument('--nodes', action='store_true', help='Generate node code')
    parser.add_argument('--conditions', action='store_true', help='Generate condition code')
    parser.add_argument('--state', action='store_true', help='Generate state code')
    
    # Single required argument
    parser.add_argument('graph_file', nargs='?', help='Path to the graph specification file')

    args = parser.parse_args()

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
        if not (args.graph or args.nodes or args.conditions or args.state):
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
        if args.graph:
            print_python_code(gen_graph(graph_name, graph_spec))
        if args.nodes:
            if 'graph' in graph:
                print_python_code(gen_nodes(graph['graph']))
        if args.conditions:
            if 'graph' in graph:
                print_python_code(gen_conditions(graph_spec))
        if args.state:
            if 'graph' in graph:
                print_python_code(gen_state(graph_spec))
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