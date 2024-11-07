#!/usr/bin/env python3

import sys
import argparse
import os
from pathlib import Path
from langgraph_codegen.gen_graph import gen_graph, validate_graph

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
    """List all available example graphs."""
    try:
        import langgraph_codegen
        package_dir = Path(os.path.dirname(langgraph_codegen.__file__))
        examples_dir = package_dir / 'data' / 'examples'
        
        if not examples_dir.exists():
            print(f"Examples directory not found at {examples_dir}", file=sys.stderr)
            return
            
        graph_files = [f.name for f in examples_dir.glob('*.graph')]
        
        if not graph_files:
            print("No .graph files found in examples directory", file=sys.stderr)
            return
            
        print("Available example graphs:")
        for file in graph_files:
            print(f"  {file}")
        print("\nTo use an example, run:")
        print("  lgcodegen my_graph example.graph")
    except Exception as e:
        print(f"Error listing examples: {str(e)}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Generate LangGraph code from graph specification")
    
    # Add --list-examples as an optional argument
    parser.add_argument('--list-examples', action='store_true', help='List available example graphs')
    
    # These arguments are only required if --list-examples is not used
    parser.add_argument('graph_name', nargs='?', help='Name of the compiled graph')
    parser.add_argument('spec_file', nargs='?', help='Path to the graph specification file')

    args = parser.parse_args()

    if args.list_examples:
        list_examples()
        return

    # If not listing examples, we need both arguments
    if not args.graph_name or not args.spec_file:
        parser.print_help()
        sys.exit(1)

    try:
        # First try to find the file as an example
        example_path = get_example_path(args.spec_file)
        
        if example_path:
            file_path = example_path
        else:
            file_path = args.spec_file
            
        # Read the specification file
        with open(file_path, 'r') as f:
            graph_spec = f.read()
        
        # Validate the graph specification
        validation_result = validate_graph(graph_spec)
        if "error" in validation_result:
            print(f"Error in graph specification:\n{validation_result['error']}", file=sys.stderr)
            print(f"\nSuggested solutions:\n{validation_result['solution']}", file=sys.stderr)
            sys.exit(1)

        # Generate the graph code and print result
        print(gen_graph(args.graph_name, graph_spec))
        
    except FileNotFoundError:
        print(f"Error: File not found: {args.spec_file}", file=sys.stderr)
        print("Use --list-examples to see available example graphs", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()