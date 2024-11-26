#!/usr/bin/env python3

import sys
import argparse
import os
from pathlib import Path
from langgraph_codegen.gen_graph import (
    gen_graph, gen_nodes, gen_state, 
    gen_conditions, validate_graph, get_example_path,
    parse_graph_spec
)
from colorama import init, Fore, Style
from rich import print as rprint
from rich.syntax import Syntax
import shutil
from typing import List, Set, Optional
from langgraph_codegen.repl import GraphDesignREPL
from collections import namedtuple
from typing_extensions import TypedDict

# DO NOT EDIT, this is updated by runit script
version="v0.1.34"

# Initialize colorama (needed for Windows)
init()

# Define the named tuple at module level
class NodeFunction(namedtuple('NodeFunction', ['function_name', 'file_path'])):
    """Represents a function found in a Python file."""
    def __repr__(self):
        return f"{self.function_name} in {self.file_path}"

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

def list_examples():
    """List all available example graph files."""
    print(f"\n{Fore.LIGHTBLACK_EX}Example graphs (these are text files):{Style.RESET_ALL}\n")
    
    examples = get_available_examples()
    if not examples:
        print(f"{Fore.YELLOW}No examples found{Style.RESET_ALL}")
        return
        
    for example in sorted(examples):
        name = example.split('/')[-1]
        name = name.split('.')[0]       # Get just the filename
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
        print(f"{Fore.YELLOW}Use --list to see available examples{Style.RESET_ALL}", file=sys.stderr)
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
        print(f"{Fore.GREEN}Creating folder {Fore.BLUE}{graph_name}{Style.RESET_ALL}")
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
    if spec_file.exists():
        print(f"{Fore.BLUE}Graph specification file {spec_file} already exists{Style.RESET_ALL}")
        return
    spec_file.write_text(graph_spec)
    print(f"{Fore.GREEN}Saved graph specification to {Fore.BLUE}{spec_file}{Style.RESET_ALL}")

import inspect
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

def find_functions_in_files(node_functions, python_files):
    """
    Finds specified function names in Python files by importing and inspecting the modules.
    Returns list of NodeFunction named tuples where functions were found.
    
    Args:
        node_functions (list): List of function names to search for
        python_files (list): List of Python filenames to search in
        
    Returns:
        list[NodeFunction]: List of NodeFunction(function_name, file_path) named tuples
    """
    found_functions = []
    
    for py_file in python_files:
        try:
            file_path = Path(py_file)
            module_name = file_path.stem
            
            spec = spec_from_file_location(module_name, file_path)
            if spec is None:
                continue
                
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Inspect all module members and add matches to results
            for name, obj in inspect.getmembers(module):
                if name in node_functions and callable(obj):
                    found_functions.append(NodeFunction(
                        function_name=name,
                        file_path=py_file.split('/', 1)[-1]
                    ))
                    
        except Exception as e:
            print(f"Error processing {py_file}: {str(e)}")
            continue
            
    return found_functions

def find_class_in_files(class_name: str, python_files: List[str]) -> Optional[str]:
    """
    Finds specified class name in Python files by importing and inspecting the modules.
    Returns the file path where the class was first found, or None if not found.
    
    Args:
        class_name (str): Name of the class to search for
        python_files (list): List of Python filenames to search in
        
    Returns:
        Optional[str]: Path to file containing the class, or None if not found
    """
    for py_file in python_files:
        try:
            file_path = Path(py_file)
            module_name = file_path.stem
            
            spec = spec_from_file_location(module_name, file_path)
            if spec is None:
                continue
                
            module = module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Inspect all module members and return first match
            for name, obj in inspect.getmembers(module):
                if name == class_name and inspect.isclass(obj):
                    return py_file.split('/', 1)[-1]
                    
        except Exception as e:
            print(f"Error processing {py_file}: {str(e)}")
            continue
            
    return None

from typing import TypedDict, Type, get_type_hints

def init_state(state_class) -> dict:
    """
    Initialize any TypedDict subclass by prompting user for string fields.
    Only processes str fields, preserving default empty values for other types.
    
    Args:
        state_class: The TypedDict class to instantiate
        
    Returns:
        dict: A dictionary with user-provided values for string fields
    """
    # Get the type hints to identify string fields
    try:
        type_hints = get_type_hints(state_class)
    except TypeError:
        # Fallback if type hints cannot be retrieved
        type_hints = getattr(state_class, '__annotations__', {})
    
    # Initialize with empty values based on types
    state = {}
    for field, type_ in type_hints.items():
        # Check if it's a list type by looking at the type string
        is_list = 'list' in str(type_).lower()
        state[field] = [] if is_list else ''
    
    # Process each field
    print(f"Enter values for {state_class.__name__} fields (press Enter to skip):")
    for field, type_hint in type_hints.items():
        # Only process string fields
        if type_hint == str:
            user_input = input(f"{field}: ").strip()
            state[field] = user_input
    
    return state

INIT_STATE_FUNCTION = '''
from typing import TypedDict, Type, get_type_hints

def init_state(state_class) -> dict:
    """
    Initialize any TypedDict subclass by prompting user for string fields.
    Only processes str fields, preserving default empty values for other types.
    
    Args:
        state_class: The TypedDict class to instantiate
        
    Returns:
        dict: A dictionary with user-provided values for string fields
    """
    # Get the type hints to identify string fields
    try:
        type_hints = get_type_hints(state_class)
    except TypeError:
        # Fallback if type hints cannot be retrieved
        type_hints = getattr(state_class, '__annotations__', {})
    
    # Initialize with empty values based on types
    state = {}
    for field, type_ in type_hints.items():
        # Check if it's a list type by looking at the type string
        is_list = 'list' in str(type_).lower()
        state[field] = [] if is_list else ''
    
    # Process each field
    print(f"Enter values for {state_class.__name__} fields (press Enter to skip):")
    for field, type_hint in type_hints.items():
        # Only process string fields
        if type_hint == str:
            user_input = input(f"{field}: ").strip()
            state[field] = user_input
    
    return state
'''

def main():
    print(f"LangGraph CodeGen {version}")
    parser = argparse.ArgumentParser(description="Generate LangGraph code from graph specification")
    
    # repl and code display options
    parser.add_argument('-i', '--repl', action='store_true', 
                       help='Start interactive graph design REPL', dest='interactive')
    parser.add_argument('-l', '--line-numbers', action='store_true', help='Show line numbers in generated code')
    
    # Add the options
    parser.add_argument('--list', action='store_true', help='List available example graphs')
    parser.add_argument('--graph', action='store_true', help='Generate graph code')
    parser.add_argument('--nodes', action='store_true', help='Generate node code')
    parser.add_argument('--conditions', action='store_true', help='Generate condition code')
    parser.add_argument('--state', action='store_true', help='Generate state code')
    parser.add_argument('--code', action='store_true', help='Generate runnable graph')
    parser.add_argument('--seed', type=int, help='Random seed for reproducible tests')
     
    # Single required argument
    parser.add_argument('graph_file', nargs='?', help='Path to the graph specification file or folder')

    args = parser.parse_args()

    # Handle REPL mode - now requires graph_file
    if args.interactive:
        if not args.graph_file:
            print(f"{Fore.RED}Error: Interactive mode requires a graph file{Style.RESET_ALL}")
            sys.exit(1)
            
        # Get the graph file content
        example_path = get_example_path(args.graph_file)
        file_path = example_path if example_path else args.graph_file
        print(f"Using graph file: {file_path}")
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
            print(f"{Fore.RED}Errors in graph specification:{Style.RESET_ALL}\n")
            print(f"{validation_result['error']}\n")
            if hasattr(validation_result, 'solution'):
                print(f"{Fore.BLUE}Suggested solutions:{Style.RESET_ALL}\n")
                print(f"{validation_result['solution']}\n")
            if hasattr(validation_result, 'details'):
                print(f"{Fore.YELLOW}Details:{Style.RESET_ALL}\n")
                print(f"{validation_result['details']}\n")
            sys.exit(1)

        # Extract the graph from validation result
        graph_instance = validation_result.get("graph")
        if not graph_instance:
            print(f"{Fore.RED}Error: Invalid graph structure{Style.RESET_ALL}", file=sys.stderr)
            sys.exit(1)

        # Parse the graph spec to get the state class
        parsed_graph, start_node = parse_graph_spec(graph_spec)
        graph_dict = parsed_graph  # Use the parsed dictionary version instead of the Graph instance
        state_class = graph_dict[start_node]["state"]
        state_class_file = None
        if args.code:
            # Get graph name from file name (without extension)
            graph_name = Path(args.graph_file).stem
            
            # Create folder and determine output file paths
            graph_folder = ensure_graph_folder(graph_name)
            output_file = graph_folder / f"{graph_name}.py"
            
            # Check if file exists and prompt for overwrite
            if output_file.exists():
                response = input(f"{Fore.GREEN}File {Fore.BLUE}{output_file}{Style.RESET_ALL} exists. Overwrite? (y/n): {Style.RESET_ALL}")
                if response.lower() != 'y':
                    print(f"{Fore.LIGHTRED_EX}Code generation cancelled.{Style.RESET_ALL}")
                    sys.exit(0)
            
            # Save the graph specification
            save_graph_spec(graph_folder, graph_name, graph_spec)
            
            # Names of all the node functions:
            node_functions = [node for node in parsed_graph.keys() if node != "START"]
            # Names for all the python files in graph_folder, except for {graph_name}.py
            python_files = [ f"{graph_folder}/{f.name}" for f in graph_folder.glob('*.py') if f.stem != graph_name ]
            if len(python_files):
                print(f"Searching for node functions in {python_files}")
                found_functions = find_functions_in_files(node_functions, python_files)

                print(f"{Fore.BLUE}Found functions: {", ".join([ff.function_name for ff in found_functions])}{Style.RESET_ALL}")
                print(f"Searching for state class '{state_class}' in {python_files}")
                state_class_file = find_class_in_files(state_class, python_files)
                if state_class_file:
                    print(f"{Fore.BLUE}Found state class '{state_class}' in {Fore.BLUE}{state_class_file}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.GREEN}State class '{state_class}' not found{Style.RESET_ALL}")
            else:
                found_functions = []

            # Collect all code components
            complete_code = []
            
            # Add imports
            complete_code.append("""from typing import Dict, TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, Graph
from langchain_core.messages.tool import ToolMessage
from langchain_core.runnables.config import RunnableConfig
from operator import itemgetter
import random
""")

            # Add seed initialization if provided
            if args.seed is not None:
                complete_code.append(f"# Set random seed for reproducible tests\nrandom.seed({args.seed})\n")
            
            # Add components in specific order
            complete_code.append(gen_state(graph_spec, state_class_file))
            complete_code.append(gen_nodes(graph_dict))  
            complete_code.append(gen_conditions(graph_spec))
            ggresult = gen_graph(graph_name, graph_spec)
            complete_code.append(ggresult)
            
            init_state = f"init_state({state_class})" if state_class_file else f"initial_state_{state_class}()"
            # Add main section
            main_section = f"""
def random_one_or_zero():
    return random.choice([False, True])

{INIT_STATE_FUNCTION}

if __name__ == "__main__":
    import sys
    
    # Create the graph
    workflow = {graph_name}
    config = RunnableConfig(configurable={{"thread_id": "1"}})
    for output in workflow.stream({init_state}, config=config):
        print(f"\\n    {{output}}\\n")
    print("DONE STREAMING, final state:")
    print(workflow.get_state(config))
"""
            complete_code.append(main_section)
            # Join all code components and write to file
            full_code = "\n\n".join(complete_code)
            output_file.write_text(full_code)
            print(f"{Fore.GREEN}Generated {Fore.BLUE}{output_file}{Style.RESET_ALL}")
            return
                
        # Handle individual component generation
        if args.graph:
            print_python_code(gen_graph(graph_name, graph_spec), args.line_numbers)
        if args.nodes:
            print_python_code(gen_nodes(graph_dict), args.line_numbers)
        if args.conditions:
            print_python_code(gen_conditions(graph_spec), args.line_numbers)
        if args.state:
            print_python_code(gen_state(graph_spec), args.line_numbers)
        if hasattr(graph_instance, 'errors') and graph_instance.errors:
            print(f"{Fore.RED}Errors in graph specification: \n\n{graph_instance.errors}\n\n{Fore.RESET}", file=sys.stderr)
            
    except FileNotFoundError:
        print(f"{Fore.RED}Error: File not found: {args.graph_file}{Style.RESET_ALL}", file=sys.stderr)
        print(f"{Fore.BLUE}Use --list to see available example graphs{Style.RESET_ALL}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()