import random
import sys
from dataclasses import dataclass, field
from textwrap import dedent
from typing import Dict, Any, List, Optional, Tuple, Union
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


def snake_to_state_class(name):
    """Convert a snake_case (or hyphenated) name to CamelCaseState.

    Examples:
        bea_agent -> BeaAgentState
        my-graph  -> MyGraphState
        simple    -> SimpleState
    """
    name = name.replace('-', '_')
    parts = [p for p in name.split('_') if p]
    if not parts:
        return "State"
    return ''.join(p.capitalize() for p in parts) + 'State'


def expand_chains(graph_spec):
    """Expand chained arrows into individual edges.

    ``a -> b -> c -> d`` becomes three lines: ``a -> b``, ``b -> c``, ``c -> d``.
    ``START:State -> a -> b`` becomes ``START:State -> a``, ``a -> b``.
    ``a -> b, c -> d`` (fan-out/fan-in) becomes ``a -> b, c``, ``b -> d``, ``c -> d``.
    ``a -> worker(field) -> b`` becomes ``a -> worker(field)``, ``worker -> b``.
    ``a -> b -> cond ? x : y`` becomes ``a -> b``, ``b -> cond ? x : y``.
    Lines with 0 or 1 arrows pass through unchanged.
    """
    result_lines = []
    for line in graph_spec.split('\n'):
        stripped = line.strip()
        # Pass through comments, blanks, indented lines (conditionals), old => syntax
        if not stripped or stripped.startswith('#') or line[0:1].isspace() or '->' not in stripped:
            result_lines.append(line)
            continue

        # Split on -> to get segments
        segments = stripped.split('->')
        if len(segments) <= 2:
            # 0 or 1 arrows — pass through unchanged
            result_lines.append(line)
            continue

        # Multiple arrows — expand into individual edges
        parts = [s.strip() for s in segments]
        i = 0
        while i < len(parts) - 1:
            src = parts[i]
            dst = parts[i + 1]

            # For the source: if it's a function call like worker(field),
            # use just the function name as the source node
            if i > 0 and '(' in src and ')' in src:
                src = src.split('(')[0].strip()
            # For the source: if it's pipe notation like field | func,
            # use just the func name as the source node
            if i > 0 and '|' in src:
                src = src.split('|')[1].strip()

            # If dst contains commas and there's a next segment (fan-out/fan-in),
            # handle fan-in by emitting edges from each comma-target to the next part
            if ',' in dst and i + 2 < len(parts):
                fan_nodes = [n.strip() for n in dst.split(',')]
                next_dst = parts[i + 2]
                # Emit fan-out: src -> comma group
                result_lines.append(f"{src} -> {dst}")
                # Emit fan-in: each node -> next_dst
                for node in fan_nodes:
                    result_lines.append(f"{node} -> {next_dst}")
                # Continue from the fan-in target
                i += 2
            else:
                result_lines.append(f"{src} -> {dst}")
                i += 1

    return '\n'.join(result_lines)


def preprocess_start_syntax(graph_spec, graph_name):
    """Normalise the START line to internal ``START(ClassName) => dest`` form.

    Accepted user-facing forms:
    1. ``START:ClassName -> dest`` — explicit state class
    2. ``START -> dest`` — class name derived from graph_name

    Internal passthrough:
    3. ``START(ClassName) => dest`` — already in internal form
    """
    lines = graph_spec.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        # First meaningful line
        if not stripped.startswith('START'):
            return graph_spec  # No START found — return unchanged
        if '(' in stripped:
            return graph_spec  # Already internal form
        if ':' in stripped.split('->')[0]:
            # START:ClassName -> dest
            start_part = stripped.split('->')[0].strip()
            class_name = start_part.split(':', 1)[1].strip()
            if '->' in stripped:
                destination = stripped.split('->', 1)[1].strip()
                lines[i] = f'START({class_name}) => {destination}'
                return '\n'.join(lines)
        # Bare START -> dest
        if '->' in stripped:
            state_class = snake_to_state_class(graph_name)
            destination = stripped.split('->', 1)[1].strip()
            lines[i] = f'START({state_class}) => {destination}'
            return '\n'.join(lines)
        return graph_spec
    return graph_spec

def normalize_spec(graph_spec: str) -> str:
    """Stage 2: Convert expanded format to normalized indented format.

    Input: expanded spec (one -> per line, from expand_chains + preprocess_start_syntax)
    Output: normalized spec with indented edges and metadata comments
    """
    graph_spec = dedent(graph_spec)
    # NOTE: no expand_chains() call — input is already expanded
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
            if "|" in destinations:
                # Worker pipe: field | func
                field_name, fn_name = [s.strip() for s in destinations.split("|")]
                # Strip State. prefix if present
                if '.' in field_name and field_name.split('.')[0].strip() == state_class_name:
                    field_name = field_name.split('.')[1].strip()
                assignment_function_name = f"assign_workers_{fn_name}"
                transformed_lines.append(f"{node_name}")
                transformed_lines.append(f"  {assignment_function_name} => {fn_name}")
                transformed_lines.append(f"# WORKER_ASSIGNMENT: {assignment_function_name}({field_name}) -> {fn_name}")
                continue
            elif "(" in line:
                # All func(...) calls are switch functions
                node_name = line.split(arrow)[0].strip()
                fn_name = line.split(arrow)[1].split("(")[0].strip()
                fn_params = line.split("(")[1].split(")")[0].strip()
                transformed_lines.append(f"{node_name}")
                for fn_param in fn_params.split(","):
                    transformed_lines.append(f"  {fn_name}_{fn_param.strip()} => {fn_param.strip()}")
                transformed_lines.append(f"# SWITCH: {fn_name}({fn_params})")
            elif "?" in destinations:
                dest = destinations.strip()
                fn_name = dest.split("?")[0].strip()
                rest = dest.split("?", 1)[1]
                true_node = rest.split(":")[0].strip()
                false_node = rest.split(":")[1].strip()
                node_name = node_name.strip()
                transformed_lines.append(f"{node_name}")
                transformed_lines.append(f"  {fn_name} => {true_node}")
                transformed_lines.append(f"  => {false_node}")
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


def transform_graph_spec(graph_spec: str) -> str:
    """Full transform (backward compat): expands chains then normalizes."""
    graph_spec = dedent(graph_spec)
    graph_spec = expand_chains(graph_spec)
    return normalize_spec(graph_spec)


@dataclass
class ParsedSpec:
    """Pre-computed results from parsing a graph specification."""
    raw_spec: str                                          # After expand + preprocess (expanded format)
    normalized_spec: str                                   # After normalize_spec() (normalized format)
    graph_dict: dict                                       # {node: {state, edges: [{condition, destination}]}}
    start_node: str
    state_class: str
    worker_functions: List[Tuple[str, str]] = field(default_factory=list)          # [(func_name, field_name), ...]
    assignment_functions: List[Tuple[str, str, str]] = field(default_factory=list) # [(assign_fn, field_name, worker_fn), ...]
    switch_functions: List[Tuple[str, List[str]]] = field(default_factory=list)    # [(fn_name, [params]), ...]


def parse_spec(graph_spec: str) -> 'ParsedSpec':
    """Run the full pipeline once and return all intermediate results.

    Input should already be through expand_chains() + preprocess_start_syntax().
    """
    normalized = normalize_spec(graph_spec)
    graph_dict, start_node = parse_graph_spec(graph_spec)
    state_class = graph_dict[start_node]["state"]
    return ParsedSpec(
        raw_spec=graph_spec,
        normalized_spec=normalized,
        graph_dict=graph_dict,
        start_node=start_node,
        state_class=state_class,
        worker_functions=find_worker_functions(graph_spec),
        assignment_functions=find_assignment_functions(normalized),
        switch_functions=find_switch_functions(normalized),
    )


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

def gen_nodes(graph: Union[Graph, dict], found_functions: list[str] = None, worker_func_names: set = None):
    """Generate code for graph nodes.

    Args:
        graph: Either a Graph instance containing nodes and edges, or a dictionary with graph data
        found_functions: Optional list of found function names
        worker_func_names: Optional set of worker function names to exclude
    """
    nodes = []
    # workaround python mutable default argument problem (list is mutable, and created once at function definition time)
    if found_functions is None:
        found_functions = []
    if worker_func_names is None:
        worker_func_names = set()
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
            if node_name in worker_func_names:
                continue
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

def gen_conditions(graph_spec, human=False, parsed=None):
    if parsed:
        graph, start_node = parsed.graph_dict, parsed.start_node
        assignment_func_names = {af[0] for af in parsed.assignment_functions}
        switch_funcs = parsed.switch_functions
    else:
        graph, start_node = parse_graph_spec(graph_spec)
        transformed_spec = transform_graph_spec(graph_spec)
        assignment_func_names = {af[0] for af in find_assignment_functions(transformed_spec)}
        switch_funcs = find_switch_functions(transformed_spec)

    conditions = []
    state_type = graph[start_node]["state"]

    # Switch functions — single function returning a node name string.
    # Skip individual bool conditions that belong to a switch.
    switch_condition_names = set()
    for fn_name, params in switch_funcs:
        for param in params:
            switch_condition_names.add(f"{fn_name}_{param}")

    if human:
        conditions.append(f"""
# GENERATED CODE: human input helpers for conditions
from colorama import Fore, Style
def human_bool(condition):
    result = input(f"{{Fore.BLUE}}{{condition}}{{Style.RESET_ALL}} (y/n): {{Style.RESET_ALL}}")
    if result.lower() == 'y':
        return True
    else:
        return False

def human_choice(condition, choices):
    choices_str = ', '.join(choices)
    result = input(f"{{Fore.BLUE}}{{condition}}{{Style.RESET_ALL}} ({{choices_str}}): {{Style.RESET_ALL}}")
    if result in choices:
        return result
    return choices[0]
""")

    for node_name, node_dict in graph.items():
        for condition in find_conditions(node_dict):
            if condition not in assignment_func_names and condition not in switch_condition_names:
                conditions.append(gen_condition(condition, state_type, human))

    # Generate switch condition functions
    for fn_name, params in switch_funcs:
        conditions.append(gen_switch_condition(fn_name, params, state_type, human))

    result = "# Conditional Edge Functions\n# Functions that determine which path to take in the graph"
    return result + "\n".join(conditions) if conditions else "# Conditional Edge Functions: None"

def find_worker_functions(graph_spec):
    """Extract Worker Functions from the original graph specification.

    Worker Functions use pipe notation: field | func
    e.g. orchestrator -> sections | llm_call
    """
    worker_functions = []
    for line in graph_spec.splitlines():
        line = line.split('#')[0].strip()  # Remove comments
        if ('->' in line or '→' in line) and '|' in line:
            arrow = '->' if '->' in line else '→'
            parts = line.split(arrow)
            if len(parts) == 2:
                dest = parts[1].strip()
                if '|' in dest:
                    field_name, func_name = [s.strip() for s in dest.split('|')]
                    worker_functions.append((func_name, field_name))
    return worker_functions

def gen_worker_function(func_name, param, state_type):
    """Generate a Worker Function implementation.

    For example: llm_call(State.sections) or llm_call(sections) becomes a function
    that processes individual items and returns a single update.
    """
    # Extract field name: strip State. prefix if present
    if '.' in param:
        field_name = param.split('.')[1]
    else:
        field_name = param
    return f"""
def {func_name}(item):
    \"\"\"Worker function that processes individual {field_name} items.\"\"\"
    # TODO: Implement your {func_name} logic here
    # This function receives a single item from state['{field_name}']
    # and should return a dictionary with updates
    return {{"result": f"processed {{item}}"}}
"""

def gen_worker_functions(graph_spec, parsed=None):
    """Generate all Worker Function implementations."""
    if parsed:
        state_type = parsed.state_class
        worker_functions = parsed.worker_functions
    else:
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

def find_switch_functions(transformed_spec):
    """Extract switch functions from # SWITCH: comments.
    Returns list of (fn_name, [param1, param2, ...])."""
    switch_functions = []
    for line in transformed_spec.splitlines():
        if line.strip().startswith("# SWITCH:"):
            content = line.replace("# SWITCH:", "").strip()
            fn_name = content.split("(")[0].strip()
            params = content.split("(")[1].split(")")[0].strip()
            param_list = [p.strip() for p in params.split(",")]
            switch_functions.append((fn_name, param_list))
    return switch_functions


def gen_switch_condition(fn_name, params, state_type, human=False):
    choices_str = ", ".join(f"'{p}'" for p in params)
    if human:
        choice_fn = f"human_choice('{fn_name}', [{choices_str}])"
    else:
        choice_fn = f"random.choice([{choices_str}])"
    return f"""
def {fn_name}(state: {state_type}) -> str:
    result = {choice_fn}
    print(f'CONDITION: {fn_name}. Result: {{result}}')
    return result
"""


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

def gen_assignment_functions(graph_spec, parsed=None):
    """Generate all Assignment Function implementations."""
    if parsed:
        state_type = parsed.state_class
        assignment_functions = parsed.assignment_functions
    else:
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

# --- STATE section parsing and generation ---

TYPE_REDUCERS = {'list': 'add_to_list', 'int': 'add_int'}
TYPE_DEFAULTS = {'list': '[]', 'int': '0', 'str': "''", 'dict': '{}', 'bool': 'False', 'float': '0.0'}

DEFAULT_STATE_FIELDS = [('nodes_visited', 'list[str]'), ('counter', 'int')]


def parse_state_section(graph_spec):
    """Extract STATE section from graph spec.

    Returns (class_name, fields, remaining_spec).
    - class_name: str or None
    - fields: list of (field_name, field_type)
    - remaining_spec: graph spec with STATE section removed
    """
    lines = graph_spec.split('\n')
    state_line_idx = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('STATE:') and not line[0].isspace():
            state_line_idx = i
            break

    if state_line_idx is None:
        return (None, [], graph_spec)

    # Extract class name from the STATE: line
    class_name = lines[state_line_idx].split(':', 1)[1].strip()

    # Collect field lines
    fields = []
    end_idx = state_line_idx + 1
    for j in range(state_line_idx + 1, len(lines)):
        stripped = lines[j].strip()
        # Stop at blank line, START, or arrow
        if not stripped:
            end_idx = j
            break
        if stripped.startswith('START') or '=>' in stripped or '->' in stripped:
            end_idx = j
            break
        if stripped.startswith('#'):
            end_idx = j + 1
            continue
        # Parse field: name: type
        if ':' in stripped:
            name, ftype = stripped.split(':', 1)
            fields.append((name.strip(), ftype.strip()))
        end_idx = j + 1

    # Build remaining spec without STATE section
    remaining_lines = lines[:state_line_idx] + lines[end_idx:]
    remaining_spec = '\n'.join(remaining_lines)

    return (class_name, fields, remaining_spec)


def type_to_reducer(field_type):
    """Return the reducer function name for a field type, or None."""
    base = field_type.split('[')[0]
    return TYPE_REDUCERS.get(base)


def type_to_default(field_type):
    """Return the default value string for a field type."""
    base = field_type.split('[')[0]
    return TYPE_DEFAULTS.get(base, 'None')


def gen_state_class(state_class, fields, is_default=False):
    """Generate state class code from a list of (field_name, field_type) tuples.

    Only emits reducer functions that are actually used by the fields.
    When is_default=True, adds '# default field' comments.
    """
    # Determine which reducers are needed
    needed_reducers = set()
    for _name, ftype in fields:
        r = type_to_reducer(ftype)
        if r:
            needed_reducers.add(r)

    parts = [f"\n# Graph State: {state_class}", "from typing import Annotated, TypedDict\n"]

    # Emit only needed reducer functions
    if 'add_to_list' in needed_reducers:
        parts.append('def add_to_list(a=None, b=""):\n    return (a if a is not None else []) + ([b] if not isinstance(b, list) else b)\n')
    if 'add_int' in needed_reducers:
        parts.append('def add_int(a, b):\n    if b == 0: return 0\n    return b+1 if a==b else b\n')

    # Build class body
    class_lines = [f"class {state_class}(TypedDict):"]
    for name, ftype in fields:
        reducer = type_to_reducer(ftype)
        comment = "  # default field" if is_default else ""
        if reducer:
            class_lines.append(f"    {name}: Annotated[{ftype}, {reducer}]{comment}")
        else:
            class_lines.append(f"    {name}: {ftype}{comment}")
    parts.append('\n'.join(class_lines) + '\n')

    # Build initialize_state()
    init_items = []
    for name, ftype in fields:
        init_items.append(f"'{name}': {type_to_default(ftype)}")
    init_body = ', '.join(init_items)
    parts.append(f"def initialize_state():\n    return {{ {init_body} }}\n")

    return '\n'.join(parts)


def mock_state(state_class, extra_fields=None):
    """Backward-compatible wrapper around gen_state_class using default fields."""
    fields = list(DEFAULT_STATE_FIELDS)
    if extra_fields:
        existing_names = {f[0] for f in fields}
        for field_name, field_type in extra_fields:
            if field_name not in existing_names:
                fields.append((field_name, field_type))
    return gen_state_class(state_class, fields, is_default=True)

def gen_state(graph_spec, state_class_file=None, state_fields=None, state_class_name=None, parsed=None):
    if parsed:
        state_class = state_class_name or parsed.state_class
        worker_funcs = parsed.worker_functions
    else:
        graph, start_node = parse_graph_spec(graph_spec)
        state_class = state_class_name or graph[start_node]["state"]
        worker_funcs = find_worker_functions(graph_spec)

    if state_class_file:
        return f"from {state_class_file.split('.')[0]} import {state_class}"

    # Extract worker-pattern extra fields (e.g., State.sections or plain sections)
    worker_extra = []
    for func_name, param in worker_funcs:
        if '.' in param:
            field_name = param.split('.')[1]
        else:
            field_name = param
        worker_extra.append((field_name, 'list'))

    if state_fields:
        # Custom STATE section — add worker fields only if missing
        fields = list(state_fields)
        existing_names = {f[0] for f in fields}
        for field_name, field_type in worker_extra:
            if field_name not in existing_names:
                fields.append((field_name, field_type))
        return gen_state_class(state_class, fields, is_default=False)
    else:
        # Default fields
        return mock_state(state_class, extra_fields=worker_extra if worker_extra else None)


    
def gen_graph(graph_name, graph_spec, compile_args=None, parsed=None):
    if not graph_spec: return ""
    if parsed:
        graph = parsed.graph_dict
        start_node = parsed.start_node
        assignment_funcs = parsed.assignment_functions
        switch_funcs = parsed.switch_functions
    else:
        graph, start_node = parse_graph_spec(graph_spec)
        transformed_spec = transform_graph_spec(graph_spec)
        assignment_funcs = find_assignment_functions(transformed_spec)
        switch_funcs = find_switch_functions(transformed_spec)

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

    # Build map of nodes that use worker/assignment patterns (Send API).
    # For these nodes we emit add_conditional_edges with a list target
    # instead of the normal routing-function + dict approach.
    # Map: source_node_name -> list of (assign_fn, worker_fn)
    worker_assignment_map = {}
    for assign_fn, field_name, worker_fn in assignment_funcs:
        # Walk graph edges to find which node uses this assign_fn as a condition
        for n, nd in graph.items():
            for edge in nd["edges"]:
                if edge["condition"] == assign_fn:
                    worker_assignment_map.setdefault(n, []).append((assign_fn, worker_fn))

    # Build map of nodes that use switch functions (single routing function).
    # For these nodes we skip mk_conditions (no routing wrapper needed).
    switch_node_map = {}
    for sf_name, sf_params in switch_funcs:
        for n, nd in graph.items():
            for edge in nd["edges"]:
                if edge["condition"].startswith(sf_name + "_"):
                    switch_node_map[n] = sf_name
                    break

    # Generate the code for edges and conditional edges
    node_code = []
    for node_name, node_dict in graph.items():
        if node_name in worker_assignment_map:
            # Worker/assignment pattern — emit list-based conditional edges
            for assign_fn, worker_fn in worker_assignment_map[node_name]:
                node_code.append(
                    f"{builder_graph}.add_conditional_edges('{node_name}', {assign_fn}, ['{worker_fn}'])"
                )
        elif node_name in switch_node_map:
            # Switch function IS the routing function — skip mk_conditions
            conditional_edges = mk_conditional_edges(builder_graph, node_name, node_dict, graph_spec)
            if conditional_edges:
                node_code.append(conditional_edges)
        else:
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
    
    has_start = first_non_comment and (
        first_non_comment.startswith('START(')
        or first_non_comment.startswith('START:')
        or first_non_comment.startswith('START ->')
    )
    if not has_start:
        errors.append(ERROR_START_NODE_NOT_FOUND)
        solutions.append(
            "The graph must begin with a START node definition, for example:\n"
            "START:State -> first_node"
        )
        details.append(f"Found: {first_non_comment or 'No non-comment lines'}\n"
                      f"Expected: START:StateClass -> first_node")
    
    try:
        if not errors:  # Only try to parse if no errors so far
            graph_spec = expand_chains(graph_spec)
            graph_spec = preprocess_start_syntax(graph_spec, "graph")
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

def list_examples():
    """Return sorted list of available example names (no extensions)."""
    import langgraph_codegen
    examples_dir = Path(os.path.dirname(langgraph_codegen.__file__)) / 'data' / 'examples'
    names = set()
    for f in examples_dir.iterdir():
        if f.suffix in ('.lgraph', '.graph', '.txt'):
            names.add(f.stem)
    return sorted(names)


def get_example_path(filename):
    """Get the full path to an example file.

    Lookup order for a bare name like 'plan_and_execute':
    1. ./plan_and_execute.lg, .graph, .txt (cwd with extensions)
    2. ./plan_and_execute/plan_and_execute.lg, .graph, .txt (output folder)
    3. Package data/examples/ with .lg, .graph, .txt
    """
    try:
        base_name = filename.split('.')[0]
        extensions = ['.lgraph', '.graph', '.txt']

        # 1. Check cwd with extensions
        for ext in extensions:
            local_path = Path(f"{base_name}{ext}")
            if local_path.exists():
                return str(local_path)

        # 2. Check output folder (basename/basename.ext)
        for ext in extensions:
            local_path = Path(base_name) / f"{base_name}{ext}"
            if local_path.exists():
                return str(local_path)

        # 3. Check package examples
        import langgraph_codegen
        package_dir = Path(os.path.dirname(langgraph_codegen.__file__))
        if '.' not in filename:
            filename_with_ext = filename
        else:
            filename_with_ext = filename.split('.')[0]
        for ext in extensions:
            example_path = package_dir / 'data' / 'examples' / f"{filename_with_ext}{ext}"
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


def gen_main(basename, state_class):
    """Generate a main.py entry point that runs the compiled graph."""
    return f"""from {basename}_graph import {basename}
from {basename}_state import initialize_state

def main():
    config = {{"configurable": {{"thread_id": "1"}}}}
    initial_state = initialize_state()
    result = {basename}.invoke(initial_state, config=config)
    print(result)

if __name__ == "__main__":
    main()
"""


def gen_readme(basename, graph_spec, input_filename, folder_name=None):
    """Generate a README.md with graph spec and run instructions."""
    folder = folder_name or basename
    return f"""# {basename}

## Graph Specification

From `{input_filename}`:

```
{graph_spec.strip()}
```

## Run

```bash
cd {folder}
python main.py
```
"""
