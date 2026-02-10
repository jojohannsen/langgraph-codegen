import re
import yaml
import argparse

class GraphSummary:
    def __init__(self):
        # Data for YAML output
        self.state_class = None
        self.node_function_names = set()
        self.router_function_names = set()
        self.worker_function_names = set()
        self.node_to_node = []       # e.g. [{"source": "node1", "destinations": ["node2", ...]}]
        self.node_to_worker = []     # e.g. [{"source": ["node1", "node2"], "worker_function": "workerFn", "state_field": "field"}]
        self.worker_to_node = []     # e.g. [{"source": "nodeX", "destinations": ["nodeY", ...]}]
        # Internal bookkeeping
        self.defined_nodes = {}      # node name -> definition line (one allowed per node)
        self.node_types = {}         # node name -> "normal" or "worker"
        self.referenced_nodes = set()
        self.errors = []

def parse_first_line(line, gs):
    # First line must be: StateClassName -> first_node (each a single word)
    m = re.match(r'^\s*(\w+)\s*->\s*(\w+)\s*$', line)
    if not m:
        gs.errors.append(f"Invalid first line format: {line}")
        return
    gs.state_class = m.group(1)
    first_node = m.group(2)
    if first_node in gs.defined_nodes:
        gs.errors.append(f"Duplicate node definition: {first_node} in line: {line}")
    else:
        gs.defined_nodes[first_node] = line
        gs.node_types[first_node] = "normal"
        gs.node_function_names.add(first_node)

def parse_graph_line(line, gs):
    # Expected format: LHS -> RHS
    parts = line.split("->")
    if len(parts) != 2:
        gs.errors.append(f"Invalid format (arrow issue) in line: {line}")
        return
    lhs_raw, rhs_raw = parts[0].strip(), parts[1].strip()
    lhs_nodes = [node.strip() for node in lhs_raw.split(",") if node.strip()]
    if not lhs_nodes:
        gs.errors.append(f"No LHS nodes found in line: {line}")
        return
    # Check duplicate definitions on LHS
    for node in lhs_nodes:
        if node in gs.defined_nodes:
            gs.errors.append(f"Duplicate definition for node '{node}' in line: {line}")
    # Process RHS: it could be a function call or a simple node reference.
    func_match = re.match(r'^(\w+)\((.*)\)$', rhs_raw)
    if func_match:
        fn_name = func_match.group(1)
        args_str = func_match.group(2).strip()
        # Check worker function call: single argument of form StateClassName.field
        if args_str.count(",") == 0:
            wm = re.match(r'^(\w+)\.(\w+)$', args_str)
            if wm:
                state_in_arg, field = wm.group(1), wm.group(2)
                if state_in_arg != gs.state_class:
                    gs.errors.append(f"Worker function state mismatch in line: {line}")
                # Mark LHS nodes as defined and worker type
                for node in lhs_nodes:
                    gs.defined_nodes[node] = line
                    gs.node_types[node] = "worker"
                    gs.node_function_names.add(node)
                gs.worker_function_names.add(fn_name)
                # Disallow worker-to-worker transitions:
                for node in lhs_nodes:
                    if gs.node_types.get(node) == "worker":
                        gs.errors.append(f"Worker-to-worker transition not allowed in line: {line}")
                gs.node_to_worker.append({
                    "source": lhs_nodes, 
                    "worker_function": fn_name, 
                    "state_field": field
                })
                return
        # Otherwise treat as a router function; must have at least 2 arguments.
        args = [arg.strip() for arg in args_str.split(",") if arg.strip()]
        if len(args) < 2:
            gs.errors.append(f"Router function must have at least 2 arguments in line: {line}")
        else:
            for arg in args:
                gs.referenced_nodes.add(arg)
            for node in lhs_nodes:
                gs.defined_nodes[node] = line
                if node not in gs.node_types:
                    gs.node_types[node] = "normal"
                gs.node_function_names.add(node)
            gs.router_function_names.add(fn_name)
            for node in lhs_nodes:
                if gs.node_types.get(node) == "worker":
                    gs.worker_to_node.append({"source": node, "destinations": args})
                else:
                    gs.node_to_node.append({"source": node, "destinations": args})
            return
    else:
        # Handle simple node-to-node transitions with comma-separated RHS.
        ref_nodes = [n.strip() for n in rhs_raw.split(",") if n.strip()]
        if not ref_nodes:
            gs.errors.append(f"No RHS nodes found in line: {line}")
            return
        for rn in ref_nodes:
            gs.referenced_nodes.add(rn)
        for node in lhs_nodes:
            gs.defined_nodes[node] = line
            if node not in gs.node_types:
                gs.node_types[node] = "normal"
            gs.node_function_names.add(node)
        for node in lhs_nodes:
            if gs.node_types.get(node) == "worker":
                gs.worker_to_node.append({"source": node, "destinations": ref_nodes})
            else:
                gs.node_to_node.append({"source": node, "destinations": ref_nodes})
        return

def validate_referenced_nodes(gs):
    # Check that every node referenced in an RHS is defined on some LHS.
    for ref in gs.referenced_nodes:
        if ref not in gs.defined_nodes:
            gs.errors.append(f"Referenced node '{ref}' not defined in any LHS.")

def process_graph(lines):
    gs = GraphSummary()
    # Remove comments and blank lines.
    content = [line for line in lines if line.strip() and not line.strip().startswith("#")]
    if not content:
        gs.errors.append("No graph lines provided.")
        return gs
    # Process first line.
    parse_first_line(content[0], gs)
    # Process remaining lines.
    for line in content[1:]:
        parse_graph_line(line, gs)
    validate_referenced_nodes(gs)
    return gs

def output_yaml(gs):
    summary = {
        "state_class": gs.state_class,
        "node_function_names": sorted(list(gs.node_function_names)),
        "router_function_names": sorted(list(gs.router_function_names)),
        "worker_function_names": sorted(list(gs.worker_function_names)),
        "transitions": {
            "node_to_node": gs.node_to_node,
            "node_to_worker": gs.node_to_worker,
            "worker_to_node": gs.worker_to_node,
        }
    }
    return yaml.dump(summary)

def main():
    parser = argparse.ArgumentParser(description="Process a graph specification file.")
    parser.add_argument("filename", help="Path to the graph specification file.")
    args = parser.parse_args()

    try:
        with open(args.filename, "r") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error opening file: {e}")
        return

    gs = process_graph(lines)
    if gs.errors:
        print("Errors found in graph specification:")
        for err in gs.errors:
            print(err)
    else:
        print(output_yaml(gs))

if __name__ == "__main__":
    main()
