import random
import sys
from textwrap import dedent
from typing import Dict, Any, Optional, Union
from pathlib import Path
import os
from langgraph_codegen.graph import Graph

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
        if ("=>" in line or "->" in line or "→" in line) and state_class_name is None:
            state_class_name = in_parentheses(line) if "(" in line else line.strip().split()[0]
            if "=>" in line:
                start_node_name = line.split("=>")[1].strip()
            elif "->" in line:
                start_node_name = line.split("->")[1].strip()
            elif "→" in line:
                start_node_name = line.split("→")[1].strip()
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
        if "->" in line or "→" in line:
            # Determine which arrow type to use for splitting
            arrow = "->" if "->" in line else "→"
            node_name, destinations = line.split(arrow)
            if "(" in line:
                # if fn call parameter is {state_class_name}.{field_name}, we need to extract that
                fn_params = line.split("(")[1].split(")")[0].strip()
                fn_name = line.split(arrow)[1].split("(")[0].strip()
                # this would be exactly 1 parameter, in that format
                if fn_params.startswith(state_class_name):
                    iterable_field_name = fn_params.split(".")[1]
                    assignment_function_name = f"assign_workers_{fn_name}"
                    transformed_lines.append(f"{node_name}")
                    transformed_lines.append(f"  {assignment_function_name} => {fn_name}")
                    # Store the worker assignment info for later code generation
                    transformed_lines.append(f"# WORKER_ASSIGNMENT: {assignment_function_name}({iterable_field_name}) -> {fn_name}")
                else:
                    node_name = line.split(arrow)[0].strip()
                    fn_name = line.split(arrow)[1].split("(")[0].strip()
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
        elif ("=>" in line or "→" in line) and not line[0].isspace():
            # Determine which arrow type to use for splitting
            arrow = "=>" if "=>" in line else "→"
            parts = [p.strip() for p in line.split(arrow)]
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


def parse_graph_spec(graph_spec, state_class_name=None):
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
            if state_class_name:
                state = state_class_name
            graph[current_node] = {"state": state, "edges": []}
        else:
            current_node = line
            graph[current_node] = {"state": state, "edges": []}
    return graph, start_node


def all_true_fn(edges):
    return all(edge["condition"] == "true_fn" for edge in edges)


def get_routing_function_name_from_spec(graph_spec, node_name):
    """Extract the original function name from the graph specification.
    
    Looks for lines like "node_name -> function_name(param1, param2)"
    and returns "function_name".
    """
    for line in graph_spec.splitlines():
        line = line.split('#')[0].strip()  # Remove comments
        if ('->' in line or '→' in line) and line.startswith(node_name):
            # Determine which arrow type to use for splitting
            arrow = '->' if '->' in line else '→'
            parts = line.split(arrow)
            if len(parts) == 2:
                destination_part = parts[1].strip()
                if '(' in destination_part:
                    # Extract function name (everything before the first parenthesis)
                    func_name = destination_part.split('(')[0].strip()
                    if func_name:
                        return func_name
    # Fallback to the old naming scheme
    return f"after_{node_name}"


def get_routing_function_name(node_name, edges):
    """Get the appropriate name for the routing function.
    
    If there's only one conditional edge, use that condition's name.
    If there are multiple conditions, use the first non-true_fn condition.
    Otherwise, fall back to after_{node_name}.
    """
    non_true_conditions = [edge["condition"] for edge in edges if edge["condition"] != "true_fn"]
    
    if len(non_true_conditions) == 1:
        # Extract just the function name (everything before the first parenthesis)
        condition = non_true_conditions[0]
        return condition.split('(')[0] if '(' in condition else condition
    elif len(non_true_conditions) > 1:
        # Use the first condition's name for multiple conditions
        condition = non_true_conditions[0] 
        return condition.split('(')[0] if '(' in condition else condition
    else:
        # Fallback to the old naming scheme
        return f"after_{node_name}"


def mk_conditions(node_name, node_dict, graph_spec=None):
    edges = node_dict["edges"]
    state_type = node_dict["state"]

    # Return empty string if all edges are true_fn
    if all_true_fn(edges):
        return ""

    # Use the original graph spec to get the function name if available
    if graph_spec:
        routing_function_name = get_routing_function_name_from_spec(graph_spec, node_name)
    else:
        routing_function_name = get_routing_function_name(node_name, edges)
    function_body = [f"def {routing_function_name}(state: {state_type}):"]

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


def mk_conditional_edges(builder_graph, node_name, node_dict, graph_spec=None):
    edges = node_dict["edges"]

    # Case 1: parallel output (all edges are true_fn)
    if all_true_fn(edges):
        edge_lines = []
        for edge in edges:
            destination = edge["destination"]
            
            if destination == "END":
                edge_lines.append(f"{builder_graph}.add_edge('{node_name}', END)")
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
    
    # Use the original graph spec to get the function name if available
    if graph_spec:
        routing_function_name = get_routing_function_name_from_spec(graph_spec, node_name)
    else:
        routing_function_name = get_routing_function_name(node_name, edges)
    if any("," in edge["destination"] for edge in edges):
        return f"{node_name}_conditional_edges = {list(destinations)}\n{builder_graph}.add_conditional_edges('{node_name}', {routing_function_name}, {node_name}_conditional_edges)\n"
    else:
        return f"{node_name}_conditional_edges = {{ {', '.join(edge_mappings)} }}\n{builder_graph}.add_conditional_edges('{node_name}', {routing_function_name}, {node_name}_conditional_edges)\n"


def gen_node(node_name, state_type, single_node=False):
    imports = """# GENERATED CODE: node function for {node_name}
from typing import Dict, TypedDict, Annotated, Optional
from langgraph.graph import StateGraph
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
    
    if nodes:
        header = "# Node Functions"
        return header + "\n" + "\n".join(nodes)
    else:
        return "# This graph has no node functions"

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
    result = "# Conditional Edge Functions\n# Functions that determine which path to take in the graph"
    return result + "\n".join(conditions) if conditions else "# Conditional Edge Functions: None"

def find_worker_functions(graph_spec):
    """Extract Worker Functions from the original graph specification.
    
    Worker Functions are functions with a single parameter like:
    orchestrator -> llm_call(State.sections)
    """
    worker_functions = []
    for line in graph_spec.splitlines():
        line = line.split('#')[0].strip()  # Remove comments
        if ('->' in line or '→' in line) and '(' in line and ')' in line:
            # Determine which arrow type to use for splitting
            arrow = '->' if '->' in line else '→'
            parts = line.split(arrow)
            if len(parts) == 2:
                destination_part = parts[1].strip()
                if '(' in destination_part:
                    func_name = destination_part.split('(')[0].strip()
                    params_part = destination_part.split('(')[1].split(')')[0].strip()
                    
                    if params_part:
                        param_count = len([p.strip() for p in params_part.split(',') if p.strip()])
                        if param_count == 1:
                            # This is a Worker Function
                            param = params_part.strip()
                            worker_functions.append((func_name, param))
    return worker_functions

def gen_worker_function(func_name, param, state_type):
    """Generate a Worker Function implementation.
    
    For example: llm_call(State.sections) becomes a function that processes
    individual items and returns a single update.
    """
    # Extract field name from State.field pattern
    if '.' in param and param.startswith(state_type):
        field_name = param.split('.')[1]
        return f"""
def {func_name}(item):
    \"\"\"Worker function that processes individual {field_name} items.\"\"\"
    # TODO: Implement your {func_name} logic here
    # This function receives a single item from state['{field_name}']
    # and should return a dictionary with updates
    return {{"result": f"processed {{item}}"}}
"""
    else:
        # For other parameter patterns
        return f"""
def {func_name}(param):
    \"\"\"Worker function that processes {param}.\"\"\"
    # TODO: Implement your {func_name} logic here
    return {{"result": f"processed {{param}}"}}
"""

def gen_worker_functions(graph_spec):
    """Generate all Worker Function implementations."""
    graph, start_node = parse_graph_spec(graph_spec)
    state_type = graph[start_node]["state"]
    
    worker_functions = find_worker_functions(graph_spec)
    if not worker_functions:
        return "# This graph has no worker functions"
    
    result = "# Worker Function\n"
    implementations = []
    
    for func_name, param in worker_functions:
        implementations.append(gen_worker_function(func_name, param, state_type))
    
    return result + "\n".join(implementations)

def find_assignment_functions(graph_spec):
    """Extract Assignment Functions from the transformed graph specification.
    
    Assignment Functions coordinate work distribution to Worker Functions.
    They look for WORKER_ASSIGNMENT comments in the transformed spec.
    """
    assignment_functions = []
    for line in graph_spec.splitlines():
        line = line.strip()
        if line.startswith("# WORKER_ASSIGNMENT:"):
            # Parse: # WORKER_ASSIGNMENT: assign_workers_llm_call(sections) -> llm_call
            parts = line.replace("# WORKER_ASSIGNMENT:", "").strip()
            assignment_part, worker_func = parts.split(" -> ")
            assignment_func = assignment_part.split("(")[0].strip()
            field_name = assignment_part.split("(")[1].split(")")[0].strip()
            assignment_functions.append((assignment_func, field_name, worker_func))
    return assignment_functions

def gen_assignment_function(assignment_func, field_name, worker_func, state_type):
    """Generate an Assignment Function implementation.
    
    For example: assign_workers_llm_call that distributes work to llm_call workers.
    """
    return f"""
def {assignment_func}(state: {state_type}):
    \"\"\"Assignment function that distributes {field_name} items to {worker_func} workers.\"\"\"
    from langgraph.constants import Send
    return [Send('{worker_func}', {{'item': item}}) for item in state['{field_name}']]
"""

def gen_assignment_functions(graph_spec):
    """Generate all Assignment Function implementations."""
    # First get the transformed spec to find WORKER_ASSIGNMENT comments
    transformed_spec = transform_graph_spec(graph_spec)
    
    graph, start_node = parse_graph_spec(graph_spec)
    state_type = graph[start_node]["state"]
    
    assignment_functions = find_assignment_functions(transformed_spec)
    if not assignment_functions:
        return "# This graph has no assignment functions"
    
    result = "# Assignment Functions\n# Functions that coordinate work distribution to worker functions"
    implementations = []
    
    for assignment_func, field_name, worker_func in assignment_functions:
        implementations.append(gen_assignment_function(assignment_func, field_name, worker_func, state_type))
    
    return result + "\n".join(implementations)

def mock_state(state_class):
    result = f"""
# Graph State: {state_class}
from typing import Annotated, TypedDict

def add_str_to_list(a=None, b=""):
    return (a if a is not None else []) + ([b] if not isinstance(b, list) else b)

def add_int(a, b):
    if b == 0: return 0
    return b+1 if a==b else b

class {state_class}(TypedDict):
    nodes_visited: Annotated[list[str], add_str_to_list]
    counter: Annotated[int, add_int]

def initialize_{state_class}():
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
    initial_comment = f"# Graph Builder: {graph_name}\n"
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
                        nodes_added.append(nn)
                        graph_setup += f"{builder_graph}.add_node('{nn}', {nn})\n"
            elif node_name not in nodes_added:
                nodes_added.append(node_name)
                graph_setup += f"{builder_graph}.add_node('{node_name}', {node_name})\n"
    if start_node != "START":
        graph_setup += f"\n{builder_graph}.set_entry_point('{start_node}')\n\n"

    # Generate the code for edges and conditional edges
    node_code = []
    for node_name, node_dict in graph.items():
        conditions = mk_conditions(node_name, node_dict, graph_spec)
        if conditions:
            node_code.append(conditions)
        conditional_edges = mk_conditional_edges(builder_graph, node_name, node_dict, graph_spec)
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
        details.append(f"Found: {first_non_comment or 'No non-comment lines'}\n"
                      f"Expected: START(<state_type>) => <first_node>")
    
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
                    details.append(f"Found: START node without destination\n"
                                f"Expected: START(<state_type>) => <destination_node>")
            
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
                        details.append(f"Found: Node '{node_name}' without edges\n"
                                    f"Expected: {node_name} => <destination>")
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
        details.append(f"Error: {str(e)}")
    
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
