import re
import random
import sys
from textwrap import dedent
from typing import Dict, Any, Optional, Union
from pathlib import Path
import os
from colorama import Fore, Style

from langgraph_codegen.graph import Graph

ERROR_MISSING_IMPORTS = "Missing required imports for graph compilation"
ERROR_START_NODE_NOT_FOUND = "START node not found at beginning of graph specification"

def in_parentheses(s):
    """Extract text inside parentheses if present, otherwise return the string itself."""
    if '(' in s and ')' in s:
        return s[s.index('(') + 1:s.index(')')]
    else:
        return None

def transform_graph_spec(graph_spec: str) -> str:
    graph_spec = dedent(graph_spec)
    lines = graph_spec.split("\n")
    transformed_lines = []
    state_class_name = None
    start_node_name = None
    for line in lines:
        # Remove comments from the line
        # design issue here, we are relying on whitespace at beginning controls how to interpret the line, so have to rstrip only
        line = line.split('#')[0].rstrip()
        
        if not line or line[0] in ["-", "/"]:
            continue
        if ("=>" in line or "->" in line) and state_class_name is None:
            state_class_name = in_parentheses(line) if "(" in line else line.strip().split()[0]
            start_node_name = line.split("=>")[1].strip() if "=>" in line else line.split("->")[1].strip()
            transformed_lines.append(f"START({state_class_name})")
            transformed_lines.append(f"  => {start_node_name}")
            continue
        # if we have a line in this format:
        # "node_name -> fn_name(node_name2, node_name3, END)"
        # we need to transform that into:
        # """{node_name}
        #   {fn_name}_{fn_name_param} => {fn_name_param}"""
        # with that second line repeated for each parameter of fn_name
        
        # first check if line is in format:  node_name -> fn_name(node_name2, node_name3, END)
        if "->" in line:
            node_name, destinations = line.split("->")
            if "(" in line:
                # if fn call parameter is {state_class_name}.{field_name}, we need to extract that
                fn_params = line.split("(")[1].split(")")[0].strip()
                fn_name = line.split("->")[1].split("(")[0].strip()
                # this would be exactly 1 parameter, in that format
                if fn_params.startswith(state_class_name):
                    iterable_field_name = fn_params.split(".")[1]
                    transformed_lines.append(f"{node_name}")
                    transformed_lines.append(f"  true_fn => SEND({iterable_field_name})")
                    # write the send list as code, it looks like, append this as a :
                    # "SEND: [ {fn_name}(s) for s in state['{iterable_field_name}'] ]"
                    transformed_lines.append(f"# SEND: [ {fn_name}(s) for s in state['{iterable_field_name}'] ]")
                else:
                    node_name = line.split("->")[0].strip()
                    fn_name = line.split("->")[1].split("(")[0].strip()
                    fn_params = line.split("(")[1].split(")")[0].strip()
                    transformed_lines.append(f"{node_name}")
                    for fn_param in fn_params.split(","):
                        transformed_lines.append(f"  {fn_name}_{fn_param.strip()} => {fn_param.strip()}")
                        # we also need code for that function, we out that as a comment
                        # "# CONDITION: fn_name_{fn_param} = lambda state: {fn_name}(state) == '{fn_param}'"
                        transformed_lines.append(f"# CONDITION: {fn_name}_{fn_param.strip()} = lambda state: {fn_name}(state) == '{fn_param.strip()}'")
            else:
                node_name = node_name.strip()
                transformed_lines.append(node_name)
                # split on , and strip whitespace
                destinations = [d.strip() for d in destinations.split(",")]
                for destination in destinations:
                    transformed_lines.append(f"  true_fn => {destination}")
        elif "=>" in line and not line[0].isspace():
            parts = [p.strip() for p in line.split("=>")]
            if parts[0]:
                # parts[0] might be a comma separated list of node names
                node_names = [n.strip() for n in parts[0].split(",")]
                for node_name in node_names:
                    transformed_lines.append(node_name)
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
        if not line or line[0] in ["#", "-", "/"]:
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

    # Return empty string if all edges are true_fn
    if all_true_fn(edges):
        return ""

    function_body = [f"def after_{node_name}(state: {state_type}):"]

    for i, edge in enumerate(edges):
        condition = edge["condition"]
        destination = edge["destination"]

        # Format return statement based on destination type
        if destination == "END":
            return_statement = "return 'END'"
        elif "," in destination:
            destinations = [d.strip() for d in destination.split(",")]
            return_statement = f"return {destinations}"
        else:
            return_statement = f"return '{destination}'"

        # Add condition and return statement
        if condition == "true_fn":
            function_body.append(f"    {return_statement}")
            break
        else:
            function_body.append(f"    {'if' if i == 0 else 'elif'} {condition}(state):")
            function_body.append(f"        {return_statement}")

    # Add default END case if needed
    if condition != "true_fn":
        function_body.append("    return 'END'")  # Return END as string
    function_body.append("")

    return "\n".join(function_body)


def mk_conditional_edges(builder_graph, node_name, node_dict):
    edges = node_dict["edges"]

    # Case 1: parallel output (all edges are true_fn)
    if all_true_fn(edges):
        edge_lines = []
        for edge in edges:
            destination = edge["destination"]
            
            if destination == "END":
                edge_lines.append(f"{builder_graph}.add_edge('{node_name}', END)")
            elif "[" in destination:  # parallel output destinations
                function, var_name, state_field = parse_string(destination)
                edge_lines.extend([
                    f"def after_{node_name}(state):",
                    f"    return [Send('{function}', {{'{var_name}': s}}) for s in state['{state_field}']]",
                    f"{builder_graph}.add_conditional_edges('{node_name}', after_{node_name}, ['{function}'])"
                ])
            elif node_name == "START":
                edge_lines.append(f"{builder_graph}.add_edge(START, '{destination}')")
            else:
                # Handle comma-separated destinations
                destinations = [d.strip() for d in destination.split(",")] if "," in destination else [destination]
                for dest in destinations:
                    edge_lines.append(f"{builder_graph}.add_edge('{node_name}', '{dest}')")
        
        return "\n".join(edge_lines)

    # Case 2: Multiple conditions
    destinations = set()
    edge_mappings = []
    
    for edge in edges:
        dest = edge["destination"]
        if dest == "END":
            edge_mappings.append("'END': END")
        else:
            dests = [f"'{d.strip()}'" for d in dest.split(",")] if "," in dest else [f"'{dest}'"]
            destinations.update(dests[0].strip("'") for d in dests)
            if len(dests) > 1:
                edge_mappings.append(f"'{dest}': [{','.join(dests)}]")
            else:
                edge_mappings.append(f"'{dest}': {dests[0]}")
    
    # Only add END mapping if there's no explicit END destination
    has_end = any(edge["destination"] == "END" for edge in edges)
    no_true_fn = not any("true_fn" in edge["condition"] for edge in edges)
    if not has_end and no_true_fn:
        edge_mappings.append("'END': END")
    
    if any("," in edge["destination"] for edge in edges):
        return f"{node_name}_conditional_edges = {list(destinations)}\n{builder_graph}.add_conditional_edges('{node_name}', after_{node_name}, {node_name}_conditional_edges)\n"
    else:
        return f"{node_name}_conditional_edges = {{ {', '.join(edge_mappings)} }}\n{builder_graph}.add_conditional_edges('{node_name}', after_{node_name}, {node_name}_conditional_edges)\n"


def true_fn(state):
    return True

def gen_node(node_name, state_type, single_node=False):
    imports = """# GENERATED CODE: node function for {node_name}
from typing import Dict, TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, Graph
from langchain_core.messages.tool import ToolMessage
from langchain_core.runnables.config import RunnableConfig

""" if single_node else ""
    
    return f"""{imports}def {node_name}(state: {state_type}, *, config:Optional[RunnableConfig] = None):
    print(f'NODE: {node_name}')
    return {{ 'nodes_visited': '{node_name}', 'counter': state['counter'] + 1 }}
"""

def process_node(node_name, node_data, found_functions, graph, state_type, single_node=False):
    """Process a single node and generate appropriate code."""
    if node_name in ["START", "END"]:  # Exclude both START and END
        return None
            
    matching_functions = [ff for ff in found_functions if ff.function_name == node_name]
    if len(matching_functions) == 1:
        file_name, function_name = matching_functions[0].file_path, matching_functions[0].function_name
        return f"from {file_name.split('.')[0]} import {function_name}"
    else:
        if isinstance(graph, dict) and node_data is not None:
            state_type = node_data.get('state', 'default')
        return gen_node(node_name, state_type, single_node)

def gen_node_names(node_names):
    if "," in node_names:
        names = [n.strip() for n in node_names.split(",")]
        for name in names:
            yield name
    else:
        yield node_names

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

    for node_names, node_data in node_items:
        for node_name in gen_node_names(node_names):
            node_code = process_node(node_name, node_data, found_functions, graph, state_type)
            if node_code:
                nodes.append(node_code)
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

def gen_condition(condition, state_type, human=False):
    condition_fn = f"human_bool('{condition}')" if human else "random_one_or_zero()"
    return f"""
def {condition}(state: {state_type}) -> bool:
    result = {condition_fn}
    print(f'CONDITION: {condition}. Result: {{result}}')
    return result
"""

def gen_conditions(graph_spec, human=False):
    graph, start_node = parse_graph_spec(graph_spec)
    conditions = []
    state_type = graph[start_node]["state"]
    if human:
        conditions.append(f"""
# GENERATED CODE: human boolean input for conditions
from colorama import Fore, Style
def human_bool(condition):
    result = input(f"{{Fore.BLUE}}{{condition}}{{Style.RESET_ALL}} (y/n): {{Style.RESET_ALL}}")
    if result.lower() == 'y':
        return True
    else:
        return False
""")
        
    for node_name, node_dict in graph.items():
        for condition in find_conditions(node_dict):
            conditions.append(gen_condition(condition, state_type, human))
    result = "# GENERATED CODE -- used for graph simulation mode"
    return result + "\n".join(conditions) if conditions else "# This graph has no conditional edges"

def mock_state(state_class):
    result = f"""
# GENERATED CODE: mock graph state
from typing import Annotated, TypedDict

def add_str_to_list(a=None, b=""):
    return (a if a is not None else []) + ([b] if not isinstance(b, list) else b)

def add_int(a, b):
    if b == 0: return 0
    return b+1 if a==b else b

class {state_class}(TypedDict):
    nodes_visited: Annotated[list[str], add_str_to_list]
    counter: Annotated[int, add_int]

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
    builder_graph = f"builder_{graph_name}"
    graph_setup += f"{builder_graph} = StateGraph({state_type})\n"
    if state_type == "MessageGraph":
        graph_setup = f"{builder_graph} = MessageGraph()\n"

    for node_name in graph:
        if node_name != "START":
            if "," in node_name:
                node_names = [n.strip() for n in node_name.split(",")]
                for nn in node_names:
                    if nn not in nodes_added:
                        nodes_added.extend(nn)
                        graph_setup += f"{builder_graph}.add_node('{nn}', {nn})\n"
            elif node_name not in nodes_added:
                nodes_added.extend(node_name)
                graph_setup += f"{builder_graph}.add_node('{node_name}', {node_name})\n"
    if start_node != "START":
        graph_setup += f"\n{builder_graph}.set_entry_point('{start_node}')\n\n"

    # Generate the code for edges and conditional edges
    node_code = []
    for node_name, node_dict in graph.items():
        conditions = mk_conditions(node_name, node_dict)
        if conditions:
            node_code.append(conditions)
        conditional_edges = mk_conditional_edges(builder_graph, node_name, node_dict)
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
        + f"{graph_name} = {builder_graph}.compile({compile_args})"
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
        filename = filename.replace('.graph', '.txt')
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
