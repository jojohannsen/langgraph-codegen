#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path
from langgraph_codegen.gen_graph import (
    gen_graph, gen_nodes, gen_state,
    gen_conditions, gen_worker_functions, gen_assignment_functions,
    parse_graph_spec
)


def main():
    parser = argparse.ArgumentParser(description='Generate LangGraph code from DSL specification')
    parser.add_argument('input_file', help='Path to .lg, .graph, or .txt DSL file')
    parser.add_argument('--state', action='store_true', help='Generate only state class')
    parser.add_argument('--nodes', action='store_true', help='Generate only node functions')
    parser.add_argument('--graph', action='store_true', help='Generate only graph builder')
    parser.add_argument('--stdout', action='store_true', help='Print to stdout instead of writing files')
    parser.add_argument('-o', '--output-dir', help='Output directory (default: basename of input file)')
    args = parser.parse_args()

    # Read input
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    graph_spec = input_path.read_text()
    basename = input_path.stem

    # Determine what to generate (default = all)
    generate_all = not (args.state or args.nodes or args.graph)

    # Parse once to validate
    graph_dict, start_node = parse_graph_spec(graph_spec)

    # Generate requested sections
    sections = {}
    if args.state or generate_all:
        sections['state'] = gen_state(graph_spec)
    if args.nodes or generate_all:
        sections['nodes'] = gen_nodes(graph_dict)
    if args.graph or generate_all:
        parts = []
        conditions = gen_conditions(graph_spec)
        if conditions and conditions.strip() != '# Conditional Edge Functions: None':
            parts.append("import random\n\ndef random_one_or_zero():\n    return random.choice([False, True])")
            parts.append(conditions)
        workers = gen_worker_functions(graph_spec)
        if workers and not workers.startswith("# This graph has no"):
            parts.append(workers)
        assignments = gen_assignment_functions(graph_spec)
        if assignments and not assignments.startswith("# This graph has no"):
            parts.append(assignments)
        parts.append(gen_graph(basename, graph_spec))
        sections['graph'] = '\n\n'.join(parts)

    # Output
    if args.stdout:
        for section in sections.values():
            print(section)
            print()
    else:
        output_dir = Path(args.output_dir) if args.output_dir else Path(basename)
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, code in sections.items():
            filepath = output_dir / f"{basename}_{name}.py"
            filepath.write_text(code + '\n')
            print(f"Wrote {filepath}")


if __name__ == '__main__':
    main()
