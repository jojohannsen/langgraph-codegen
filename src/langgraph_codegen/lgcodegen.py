#!/usr/bin/env python3

import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from langgraph_codegen.gen_graph import (
    gen_graph, gen_nodes, gen_state,
    gen_conditions, gen_worker_functions, gen_assignment_functions,
    find_worker_functions, gen_main, gen_readme,
    parse_spec, parse_graph_spec, parse_state_section, preprocess_start_syntax,
    expand_chains, list_examples, get_example_path
)


def main():
    # Build dynamic epilog showing available examples
    examples = list_examples()
    if examples:
        # Format example names in columns
        col_width = max(len(name) for name in examples) + 4
        cols = 80 // col_width
        rows = []
        for i in range(0, len(examples), cols):
            row = '  '.join(name.ljust(col_width) for name in examples[i:i+cols])
            rows.append('  ' + row)
        epilog = 'Available examples:\n' + '\n'.join(rows) + '\n\nUsage: lgcodegen <example_name> to generate from a built-in example.'
    else:
        epilog = None

    parser = argparse.ArgumentParser(
        description='Generate LangGraph code from DSL specification',
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('input_file', help='Path to .lgraph, .graph, or .txt DSL file, or a built-in example name')
    parser.add_argument('--state', action='store_true', help='Generate only state class')
    parser.add_argument('--nodes', action='store_true', help='Generate only node functions')
    parser.add_argument('--graph', action='store_true', help='Generate only graph builder')
    parser.add_argument('--stdout', action='store_true', help='Print to stdout instead of writing files')
    parser.add_argument('-o', '--output-dir', help='Output directory (default: basename of input file)')
    parser.add_argument('--show', action='store_true', help='Show the content of the graph spec and exit')
    parser.add_argument('--verify', action='store_true',
                        help='Verify generated files execute without import errors')
    args = parser.parse_args()

    # Resolve input file
    input_path = Path(args.input_file)
    from_example = False

    if input_path.exists() and input_path.is_file():
        # Explicit file path — use as-is
        pass
    else:
        # Try resolving as bare name
        resolved = get_example_path(args.input_file)
        if resolved is None:
            print(f"Error: '{args.input_file}' not found as file or example", file=sys.stderr)
            sys.exit(1)
        input_path = Path(resolved)
        from_example = 'data/examples' in resolved

    graph_spec = input_path.read_text()

    if args.show:
        print(graph_spec, end='')
        sys.exit(0)

    basename = input_path.stem
    is_expanded = input_path.suffix == '.lgraphx'

    # 1. Extract STATE section first (before preprocessing)
    state_class_name, state_fields, graph_spec = parse_state_section(graph_spec)
    concise_spec = graph_spec  # save pre-expansion form

    if not is_expanded:
        # 2. Expand chained arrows (a -> b -> c) into individual edges
        graph_spec = expand_chains(graph_spec)

    expanded_spec = graph_spec  # for .lgraphx — uses -> and START:Class only

    # 3. Preprocess START syntax (always runs, even for .lgraphx input)
    graph_spec = preprocess_start_syntax(graph_spec, basename)

    # 4. If STATE gave us a class name, ensure START uses it
    if state_class_name:
        import re
        # Replace START(Whatever) with STATE class name, or bare START
        graph_spec = re.sub(
            r'START\([^)]*\)',
            f'START({state_class_name})',
            graph_spec
        )

    # Determine what to generate (default = all)
    generate_all = not (args.state or args.nodes or args.graph)

    # Stages 2+3: Expanded -> Normalized -> Parsed (once)
    parsed = parse_spec(graph_spec)

    # Extract metadata for cross-file imports
    state_class = parsed.state_class
    node_names = []
    for node_key in parsed.graph_dict:
        if node_key == "START":
            continue
        if "," in node_key:
            node_names.extend(n.strip() for n in node_key.split(","))
        else:
            node_names.append(node_key)
    node_names = list(dict.fromkeys(node_names))  # dedupe, preserve order

    # Exclude worker functions (they're defined in the graph file, not nodes)
    worker_func_names = {f[0] for f in parsed.worker_functions}
    import_node_names = [n for n in node_names if n not in worker_func_names]

    # Generate requested sections
    sections = {}
    if args.state or generate_all:
        sections['state'] = gen_state(graph_spec, state_fields=state_fields if state_fields else None,
                                      state_class_name=state_class_name, parsed=parsed)
    if args.nodes or generate_all:
        sections['nodes'] = gen_nodes(parsed.graph_dict, worker_func_names=worker_func_names)
    if args.graph or generate_all:
        parts = []
        conditions = gen_conditions(graph_spec, parsed=parsed)
        if conditions and conditions.strip() != '# Conditional Edge Functions: None':
            parts.append("import random\n\ndef random_one_or_zero():\n    return random.choice([False, True])")
            parts.append(conditions)
        workers = gen_worker_functions(graph_spec, parsed=parsed)
        if workers and not workers.startswith("# This graph has no"):
            parts.append(workers)
        assignments = gen_assignment_functions(graph_spec, parsed=parsed)
        if assignments and not assignments.startswith("# This graph has no"):
            parts.append(assignments)
        parts.append(gen_graph(basename, graph_spec, parsed=parsed))
        sections['graph'] = '\n\n'.join(parts)

    # Output
    if args.stdout:
        for section in sections.values():
            print(section)
            print()
    else:
        output_dir = Path(args.output_dir) if args.output_dir else Path(basename)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Copy DSL source into output dir on first use from package examples
        if from_example:
            dest = output_dir / f"{basename}{input_path.suffix}"
            shutil.copy2(input_path, dest)
            print(f"Copied {input_path.name} to {dest}")

        # Write expanded intermediate format
        lgraphx_path = output_dir / f"{basename}.lgraphx"
        lgraphx_path.write_text(expanded_spec + '\n')
        print(f"Wrote {lgraphx_path}")

        for name, code in sections.items():
            filepath = output_dir / f"{basename}_{name}.py"

            # Prepend cross-file imports when writing to files
            if name == 'nodes':
                imports_header = (
                    f"from typing import Optional\n"
                    f"from langchain_core.runnables.config import RunnableConfig\n"
                    f"from {basename}_state import {state_class}\n\n"
                )
                code = imports_header + code
            elif name == 'graph':
                if len(import_node_names) > 5:
                    node_imports = "(\n    " + ",\n    ".join(import_node_names) + ",\n)"
                else:
                    node_imports = ", ".join(import_node_names)
                imports_header = (
                    f"from {basename}_state import {state_class}\n"
                    f"from {basename}_nodes import {node_imports}\n\n"
                )
                code = imports_header + code

            filepath.write_text(code + '\n')
            print(f"Wrote {filepath}")

        if generate_all:
            main_path = output_dir / "main.py"
            main_path.write_text(gen_main(basename, state_class) + '\n')
            print(f"Wrote {main_path}")

            readme_path = output_dir / "README.md"
            readme_path.write_text(gen_readme(basename, concise_spec, expanded_spec, output_dir.name) + '\n')
            print(f"Wrote {readme_path}")

        if args.verify:
            verify_generated_files(output_dir, basename)


def verify_generated_files(output_dir, basename):
    """Verify generated files execute without import errors."""
    graph_filename = f"{basename}_graph.py"
    graph_file = output_dir / graph_filename
    if not graph_file.exists():
        print("Skipping verification: graph file not found", file=sys.stderr)
        return

    result = subprocess.run(
        [sys.executable, graph_filename],
        cwd=str(output_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Verification FAILED for {graph_file}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(2)
    else:
        print(f"Verification OK: {graph_file}")


if __name__ == '__main__':
    main()
