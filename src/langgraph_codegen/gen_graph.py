import re
import random
import sys
from textwrap import dedent
from typing import Dict, Any, Optional, Union
from pathlib import Path
import os
from colorama import Fore, Style

from langgraph_codegen.graph import Graph

# Add these constants near the top of the file, after the imports
ERROR_MISSING_IMPORTS = "Missing required imports for graph compilation"
ERROR_START_NODE_NOT_FOUND = "START node not found at beginning of graph specification"

def transform_graph_spec(graph_spec: str) -> str:
    graph_spec = dedent(graph_spec)
    lines = graph_spec.split("\n")
    transformed_lines = []

    for line in lines:
        # Remove comments from the line
        # design issue here, we are relying on whitespace at beginning controls how to interpret the line, so have to rstrip only
        line = line.split('#')[0].rstrip()
        
        if not line or line[0] in ["-", "/"]:
            continue
        if "=>" in line and not line[0].isspace():
            parts = [p.strip() for p in line.split("=>")]
            if parts[0]:
                transformed_lines.append(parts[0])
                transformed_lines.append(f"  => {parts[1]}")
            else:
                transformed_lines.append(line)
        else:
            transformed_lines.append(line)

    return "\n".join(transformed_lines)


def parse_string(input_string):
    pattern = r"\[(\w+)\((\w+) in (\w+)\)\]"
    match = re.match(pattern, input_string)

    if match:
        function, var_name, state_field = match.groups()
        return function, var_name, state_field
    else:
        raise ValueError("String format is incorrect")


def parse_graph_spec(graph_spec):
    # transform graph into a uniform format
    # node_name
    #   => destination
    # node_name
    #   condition_name => destination
    graph_spec = transform_graph_spec(graph_spec)

    TRUE_FN = "true_fn"
    graph = {}
    current_node = None
    state = None
    start_node = None

    for line in graph_spec.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        if "=>" in line:
            if line.startswith("=>"):
                condition = TRUE_FN
                destination = line.split("=>")[1].strip()
                graph[current_node]["edges"].append(
                    {"condition": condition, "destination": destination}
                )
            else:
                parts = line.split("=>")
                condition = parts[0].strip()
                destination = parts[1].strip()
                graph[current_node]["edges"].append(
                    {"condition": condition, "destination": destination}
                )
        elif "(" in line:
            node_info = line.split("(")
            current_node = node_info[0].strip()
            start_node = current_node
            state = node_info[1].strip(")")
            graph[current_node] = {"state": state, "edges": []}
        else:
            current_node = line
            graph[current_node] = {"state": state, "edges": []}
    return graph, start_node


def all_true_fn(edges):
    return all(edge["condition"] == "true_fn" for edge in edges)


def mk_conditions(node_name, node_dict):
    edges = node_dict["edges"]
    state_type = node_dict["state"]

    # Special case: single 'true_fn' condition
    if all_true_fn(edges):
        return ""

    function_body = [f"def after_{node_name}(state: {state_type}):"]

    for i, edge in enumerate(edges):
        condition = edge["condition"]
        destination = edge["destination"]

        if "," in destination:
            # Split the destination by commas and strip spaces
            destinations = [d.strip() for d in destination.split(",")]
            # Format the return statement with a list
            return_statement = f"return {destinations}"
        else:
            # Format the return statement with a single value
            return_statement = f"return '{destination}'"

        if condition == "true_fn":
            function_body.append(f"    {return_statement}")
            break  # Exit the loop as this is always true
        elif i == 0:
            function_body.append(f"    if {condition}(state):")
        else:
            function_body.append(f"    elif {condition}(state):")

        function_body.append(f"        {return_statement}")

    # Only add the else clause if we didn't encounter 'true_fn'
    if condition != "true_fn":
        if len(edges) > 1:
            function_body.append("    else:")
            function_body.append("        # destination not found, default to END")
            function_body.append('        return END')
        else:
            function_body.append("    return END")
    function_body.append("")

    return "\n".join(function_body)


def mk_conditional_edges(graph_name, node_name, node_dict):
    edges = node_dict["edges"]

    # Case 1: parallel output
    if all_true_fn(edges):
        edge_code = ""
        for edge in edges:
            destination = edge["destination"]
            if destination == "END":
                edge_code += f"{graph_name}.add_edge('{node_name}', END)\n"
            elif "," in destination:
                data = destination.split(",")
                for x in data:
                    x = x.strip()
                    edge_code += f"{graph_name}.add_edge('{node_name}', '{x}')\n"
            elif "[" in destination:  # parallel output destinations,
                function, var_name, state_field = parse_string(destination)
                edge_code += f"def after_{node_name}(state):\n"
                edge_code += f"    return [Send('{function}', {{'{var_name}': s}}) for s in state['{state_field}']]\n"
                edge_code += f"{graph_name}.add_conditional_edges('{node_name}', after_{node_name}, ['{function}'])\n"
            else:
                if "," in node_name:
                    node_names = [f"'{n.strip()}'" for n in node_name.split(",")]
                    edge_first_node_name = f"[{','.join(node_names)}]"
                else:
                    edge_first_node_name = (
                        f"'{node_name}'" if node_name != "START" else "START"
                    )
                edge_code += (
                    f"{graph_name}.add_edge({edge_first_node_name}, '{destination}')\n"
                )
        return edge_code.rstrip()

    # Case 2: Multiple conditions
    else:
        # Helper function to create dictionary entries
        def maybe_multiple(s):
            if "," in s:
                data = s.split(",")
                quoted = [f"'{x.strip()}'" for x in data]
                return "[" + ",".join(quoted) + "]"
            else:
                return f"'{s}'"

        def mk_entry(edge):
            if edge["destination"] == "END":
                return f"'{edge['destination']}': END"
            else:
                return f"'{edge['destination']}': {maybe_multiple(edge['destination'])}"

        # Create the dictionary string
        dict_entries = ", ".join([mk_entry(e) for e in edges])
        # If there's a single edge with a condition, dict needs END: END
        if len(edges) == 1 and edges[0]["condition"] != "true_fn":
            dict_entries += ", END: END"
        node_dict_str = f"{node_name}_conditional_edges = {{ {dict_entries} }}"
        multiple = any("," in edge["destination"] for edge in edges)
        if multiple:
            # not really understanding, but it seems that in this case, we just have a list of
            # nodes instead of a dict for third parameter
            s = set()
            for edge in edges:
                destinations = edge["destination"].split(",")
                for dest in destinations:
                    s.add(dest.strip())
            node_dict_str = f"{node_name}_conditional_edges = {list(s)}"

        # Create the add_conditional_edges call
        add_edges_str = f"{graph_name}.add_conditional_edges( '{node_name}', after_{node_name}, {node_name}_conditional_edges )"
        return f"{node_dict_str}\n{add_edges_str}\n"


def true_fn(state):
    return True

def gen_node(node_name, state_type):
    return f"""
def {node_name}(state: {state_type}, *, config:Optional[RunnableConfig] = None):
    print(f'NODE: {node_name}')
    return {{ 'nodes_visited': '{node_name}', 'counter': state['counter'] + 1 }}
"""

# graph parameter is result of validate_graph
def gen_nodes(graph: Union[Graph, dict], found_functions: list[str] = None):
    """Generate code for graph nodes.
    
    Args:
        graph: Either a Graph instance containing nodes and edges, or a dictionary with graph data
        found_functions: Optional list of found function names
    """
    nodes = []
    # workaround python mutable default argument problem (list is mutable, and created once at function definition time)
    if found_functions is None:
        found_functions = []
    found_function_names = [ff.function_name for ff in found_functions]

    # Handle both Graph and dict inputs
    if isinstance(graph, Graph):
        node_items = sorted([(node, None) for node in graph.nodes])
        state_type = graph.state_type if hasattr(graph, 'state_type') else 'default'
    else:
        # For dict, sort by node names (the keys)
        node_items = sorted(graph.items(), key=lambda x: x[0])
        state_type = 'default'

    for node_name, node_data in node_items:
        # get file name and function name from found_functions
        l = [ff for ff in found_functions if ff.function_name == node_name]
        if node_name != "START":
            if len(l) == 1:
                file_name, function_name = l[0].file_path, l[0].function_name
                nodes.append(f"from {file_name.split('.')[0]} import {function_name}")
            else:
                if isinstance(graph, dict) and node_data is not None:
                    state_type = node_data.get('state', 'default')
                nodes.append(gen_node(node_name, state_type))
    return "\n".join(nodes)

def find_conditions(node_dict):
    edges = node_dict["edges"]
    conditions = []
    for edge in edges:
        if 'true_fn' != edge["condition"]:
            conditions.append(edge["condition"])
    return conditions

def random_one_or_zero():
    return random.choice([False, True])

def gen_condition(condition, state_type):
    return f"""
def {condition}(state: {state_type}) -> bool:
    result = random_one_or_zero()
    print(f'CONDITION: {condition}. Result: {{result}}')
    return result
"""

def gen_conditions(graph_spec):
    graph, start_node = parse_graph_spec(graph_spec)
    conditions = []
    state_type = graph[start_node]["state"]
    for node_name, node_dict in graph.items():
        for condition in find_conditions(node_dict):
            conditions.append(gen_condition(condition, state_type))
    result = "# GENERATED CODE -- used for graph simulation mode"
    return result + "\n".join(conditions) if conditions else "# This graph has no conditional edges"

def mock_state(state_class):
    result = f"""
# GENERATED CODE: mock graph state
from typing import Annotated, TypedDict

def add_str_to_list(a=None, b=""):
    return (a if a is not None else []) + ([b] if not isinstance(b, list) else b)

class {state_class}(TypedDict):
    nodes_visited: Annotated[list[str], add_str_to_list]
    counter: int

def initial_state_{state_class}():
    return {{ 'nodes_visited': [], 'counter': 0 }}
"""
    return result

def gen_state(graph_spec, state_class_file=None):
    graph, start_node = parse_graph_spec(graph_spec)
    state_class = graph[start_node]["state"]
    if state_class_file:
        return f"from {state_class_file.split('.')[0]} import {state_class}"
    else:
        return mock_state(state_class)


    
def gen_graph(graph_name, graph_spec, compile_args=None):
    if not graph_spec: return ""
    graph, start_node = parse_graph_spec(graph_spec)
    nodes_added = []

    # Generate the graph state, node definitions, and entry point
    initial_comment = f"# GENERATED code, creates compiled graph: {graph_name}\n"
    graph_setup = ""

    state_type = graph[start_node]['state']
    imports = """from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver
import sqlite3"""
    if state_type == "MessageGraph":
        imports += """
from langgraph.graph import MessageGraph""" 

    graph_setup += f"checkpoint_saver = MemorySaver()\n"
    graph_setup += f"{graph_name} = StateGraph({state_type})\n"
    if state_type == "MessageGraph":
        graph_setup = f"{graph_name} = MessageGraph()\n"

    for node_name in graph:
        if node_name != "START":
            if "," in node_name:
                node_names = [n.strip() for n in node_name.split(",")]
                for nn in node_names:
                    if nn not in nodes_added:
                        nodes_added.extend(nn)
                        graph_setup += f"{graph_name}.add_node('{nn}', {nn})\n"
            elif node_name not in nodes_added:
                nodes_added.extend(node_name)
                graph_setup += f"{graph_name}.add_node('{node_name}', {node_name})\n"
    if start_node != "START":
        graph_setup += f"\n{graph_name}.set_entry_point('{start_node}')\n\n"

    # Generate the code for edges and conditional edges
    node_code = []
    for node_name, node_dict in graph.items():
        conditions = mk_conditions(node_name, node_dict)
        if conditions:
            node_code.append(conditions)
        conditional_edges = mk_conditional_edges(graph_name, node_name, node_dict)
        if conditional_edges:
            node_code.append(conditional_edges)

    compile_args = compile_args if compile_args else ""
    if compile_args:
        compile_args += ", "
    compile_args += f"checkpointer=checkpoint_saver"
    return (
        initial_comment
        + imports + "\n\n"
        + graph_setup
        + "\n".join(node_code)
        + "\n\n"
        + f"{graph_name} = {graph_name}.compile({compile_args})"
    )

def validate_graph(graph_spec: str) -> Dict[str, Any]:
    """
    Validate a graph specification and return a Graph instance or validation errors.
    
    Args:
        graph_spec: String containing the graph specification
        
    Returns:
        Dict containing either:
        - {"graph": Graph} if validation succeeds
        - {"error": error_messages, "solution": suggested_solutions} if validation fails
    """
    errors = []
    solutions = []
    details = []
    
    # Normalize indentation first
    graph_spec = dedent(graph_spec)
    
    # Validate START node
    lines = [line.strip() for line in graph_spec.split('\n') if line.strip()]
    first_non_comment = next((line for line in lines if not line.startswith('#')), None)
    
    if not first_non_comment or not first_non_comment.startswith('START('):
        errors.append(ERROR_START_NODE_NOT_FOUND)
        solutions.append(
            "The graph must begin with a START node definition, for example:\n"
            "START(State) => first_node"
        )
        details.append(f"{Fore.RED}Found:{Style.RESET_ALL} {first_non_comment or 'No non-comment lines'}\n"
                      f"{Fore.GREEN}Expected:{Style.RESET_ALL} START(<state_type>) => <first_node>")
    
    try:
        if not errors:  # Only try to parse if no errors so far
            graph_dict, start_node = parse_graph_spec(graph_spec)
            
            # Convert dictionary to Graph instance
            graph = Graph()
            
            # Find the destination of the START node
            start_node_dest = None
            if "START" in graph_dict:
                start_edges = graph_dict["START"]["edges"]
                if start_edges:
                    start_node_dest = start_edges[0]["destination"]
                else:
                    errors.append("START node has no destination")
                    solutions.append("Add a destination node after the START node using =>")
                    details.append(f"{Fore.RED}Found:{Style.RESET_ALL} START node without destination\n"
                                f"{Fore.GREEN}Expected:{Style.RESET_ALL} START(<state_type>) => <destination_node>")
            
            # Set the actual start node (the destination of START)
            if start_node_dest:
                graph.set_start_node(start_node_dest)
            
            # Add all nodes and edges
            for node_name, node_data in graph_dict.items():
                if node_name != "START":  # Skip the START node as it's handled internally
                    graph.add_node(node_name)
                    if not node_data["edges"]:
                        errors.append(f"Node '{node_name}' has no outgoing edges")
                        solutions.append(f"Add at least one destination for node '{node_name}' using =>")
                        details.append(f"{Fore.RED}Found:{Style.RESET_ALL} Node '{node_name}' without edges\n"
                                    f"{Fore.GREEN}Expected:{Style.RESET_ALL} {node_name} => <destination>")
                    for edge in node_data["edges"]:
                        destination = edge["destination"]
                        condition = edge["condition"]
                        if destination == "END":
                            graph.set_end_node("END")
                        graph.add_edge(node_name, destination, condition)
            
            if not errors:
                return {"graph": graph}
    except Exception as e:
        errors.append(str(e))
        solutions.append("Please check the graph specification syntax")
        details.append(f"{Fore.RED}Error:{Style.RESET_ALL} {str(e)}")
    
    # If we get here, there were errors
    return {
        "error": "\n".join(f"{i+1}. {error}" for i, error in enumerate(errors)),
        "solution": "\n".join(f"{i+1}. {solution}" for i, solution in enumerate(solutions)),
        "details": "\n\n".join(details)
    }

def get_example_path(filename):
    """Get the full path to an example file.
    First checks for local graph_name/graph_name.txt file,
    then falls back to package examples."""
    try:
        # First check for local graph_name/graph_name.txt
        base_name = filename.split('.')[0]
        local_path = Path(base_name) / f"{base_name}.txt"
        if local_path.exists():
            return str(local_path)
            
        # If not found locally, check package examples
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


def get_graph(graph_name: str) -> str:
    """
    Get a compiled graph by reading the graph specification from a file.
    
    Args:
        graph_name: Name of the graph file to load (with or without extension)
        
    Returns:
        String containing the compiled graph code, or empty string if file not found
    """
    graph_path = get_example_path(graph_name)
    if not graph_path:
        return ""
        
    with open(graph_path) as f:
        graph_spec = f.read()
        
    return gen_graph(graph_name.split('.')[0], graph_spec)
