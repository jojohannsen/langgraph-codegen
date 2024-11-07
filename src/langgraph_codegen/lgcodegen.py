#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path
from .gen_graph import gen_graph, validate_graph

def main():
    if len(sys.argv) != 3:
        print("Usage: lgcodegen <graph_name> <spec_file>", file=sys.stderr)
        sys.exit(1)

    graph_name = sys.argv[1]
    spec_file = sys.argv[2]

    try:
        # Read the specification file
        with open(spec_file, 'r') as f:
            graph_spec = f.read()
        
        # Validate the graph specification
        validation_result = validate_graph(graph_spec)
        if "error" in validation_result:
            print(f"Error in graph specification:\n{validation_result['error']}", file=sys.stderr)
            print(f"\nSuggested solutions:\n{validation_result['solution']}", file=sys.stderr)
            sys.exit(1)

        # Generate the graph code
        result = gen_graph(graph_name, graph_spec)
        print(result)
        
    except FileNotFoundError:
        print(f"Error: File not found: {spec_file}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied reading file: {spec_file}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()