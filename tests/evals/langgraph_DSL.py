evaluator_optimizer = """# Topic is provided when graph is invoked
State -> llm_call_generator
# generate a joke based on State topic
llm_call_generator -> llm_call_evaluator
# generate State funny or not result, route based on this value
llm_call_evaluator -> route_joke(llm_call_generator, END)"""

jokester = """# tells jokes, then asks if it should tell another
JokesterState -> get_joke_topic
# first we ask for topic
get_joke_topic -> tell_joke
# then we generate a joke, and display it
tell_joke -> ask_for_another
# then we ask user if they want another joke, we route based on that result
ask_for_another -> tell_another(tell_joke, END)"""

md_consensus = """MarkdownConsensusState -> get_doc
# ask human for doc path
get_doc -> read_doc
# read document content into State
read_doc -> ask_for_mods
# ask human for modifications
ask_for_mods -> handle_mods(read_doc, process_mods, END)
# update the document based on requested mods, save in a 'modified' content State field
process_mods -> accept_mods
# check if these mods are acceptable, if so
accept_mods -> mods_ok(read_doc, save_mods)
# move the modified content into main content
save_mods -> read_doc"""

orchestrator_worker = """State -> orchestrator
# ask human for 'input', generate a list of report sections to be used for a report on that nput
# generate no more than 4 sections, we store them in a list in state
orchestrator -> worker(State.sections)
# generate content for a section
worker -> synthesizer
# generate synthesized response based on the results of all the workers
synthesizer -> END"""

parallelization = """State -> get_topic
get_topic -> story, joke, poem
# generate a story, joke, and poem based on topic
story, joke, poem -> aggregator
# combine the results and end
aggregator -> END"""

prompt_chaining = """State -> generate_joke
# ask human for the topic, then generate a joke based on topic value
generate_joke -> check_punchline(improve_joke, END)
# generate an improved version of that same joke
improve_joke -> polish_joke
# generate a 'polished' version of the improved joke
polish_joke -> END"""

routing = """State -> llm_call_router
# use llm to route based on 'input' value in state
llm_call_router -> route_decistion(story, joke, poem)
# generate a story based on topic
story -> END
# generate a joke based on topic
joke -> END
# generate a poem based on topic
poem -> END"""
graph_examples = [
    evaluator_optimizer,
    jokester,
    md_consensus,
    orchestrator_worker,
    parallelization,
    prompt_chaining,
    routing
]

def unit_generator(graph):
    lines = graph.split("\n")
    comments = []
    for line in lines:
        if line.startswith("#"):
            comments.append(line[2:])
        else:
            yield line, "\n".join(comments)
            comments = []

def parse_line(line, is_first_line=False):
    """
    Parse a line of text in one of the specified formats and extract the information.
    
    Args:
        line (str): A line of text in one of the supported formats
        
    Returns:
        dict: A dictionary containing the extracted keys and values
    """
    # Clean the line
    line = line.strip()
    
    # Split on the arrow to get from and to parts
    if "->" not in line:
        raise ValueError("Line must contain '->' operator")
    
    from_part, to_part = [part.strip() for part in line.split("->")]
    
    result = { "line": line }
    if is_first_line:
        result["state_class_name"] = from_part
        result["start_node"] = to_part
        return result
    
    
    # Handle from part - could be a single node or multiple nodes separated by commas
    if "," in from_part:
        # Format: from_node_1, from_node_2 -> to_node_name
        from_nodes = [node.strip() for node in from_part.split(",")]
        result["from_nodes"] = from_nodes
    else:
        # Single from node
        result["from_node_name"] = from_part
    
    # Handle to part - could be a single node, multiple nodes, or a routing function
    if "(" in to_part and ")" in to_part:
        # This is either a routing function or a worker
        function_name, args = to_part.split("(", 1)
        args = args.rstrip(")")
        
        if "." in args:
            # Format: from_node_name -> to_worker(StateClassName.field_name)
            result["to_worker"] = function_name.strip()
            state_class, field_name = args.split(".")
            result["state_class_name"] = state_class.strip()
            result["field_name"] = field_name.strip()
        else:
            # Format: from_node_name -> to_routing_function(to_node_1, to_node_2)
            result["to_routing_function"] = function_name.strip()
            to_nodes = [node.strip() for node in args.split(",")]
            result["to_nodes"] = to_nodes
    elif "," in to_part:
        # Format: from_node_name -> to_node_1, to_node_2
        to_nodes = [node.strip() for node in to_part.split(",")]
        result["to_nodes"] = to_nodes
    else:
        # Format: from_node_name -> to_node_name
        result["to_node_name"] = to_part
    
    return result

from dataclasses import dataclass
from typing import List

@dataclass
class StartGraphTransition:
    state_class_name: str
    start_node: str
    line: str
    
    def get_source_nodes(self) -> List[str]:
        return []
    
    def get_dest_nodes(self) -> List[str]:
        return [self.start_node]
    
    def get_worker_nodes(self) -> List[str]:
        return []
    
    def get_router_functions(self) -> List[str]:
        return []

@dataclass
class SingleNodeTransition:
    from_node_name: str
    to_node_name: str
    line: str
    
    def get_source_nodes(self) -> List[str]:
        return [self.from_node_name]
    
    def get_dest_nodes(self) -> List[str]:
        return [self.to_node_name]
    
    def get_worker_nodes(self) -> List[str]:
        return []
    
    def get_router_functions(self) -> List[str]:
        return []

@dataclass
class MultiSourceTransition:
    from_nodes: List[str]
    to_node_name: str
    line: str
    
    def get_source_nodes(self) -> List[str]:
        return self.from_nodes
    
    def get_dest_nodes(self) -> List[str]:
        return [self.to_node_name]
    
    def get_worker_nodes(self) -> List[str]:
        return []
    
    def get_router_functions(self) -> List[str]:
        return []

@dataclass
class MultiTargetTransition:
    from_node_name: str
    to_nodes: List[str]
    line: str
    
    def get_source_nodes(self) -> List[str]:
        return [self.from_node_name]
    
    def get_dest_nodes(self) -> List[str]:
        return self.to_nodes
    
    def get_worker_nodes(self) -> List[str]:
        return []
    
    def get_router_functions(self) -> List[str]:
        return []

@dataclass
class RoutingTransition:
    from_node_name: str
    to_routing_function: str
    to_nodes: List[str]
    line: str
    
    def get_source_nodes(self) -> List[str]:
        return [self.from_node_name]
    
    def get_dest_nodes(self) -> List[str]:
        return self.to_nodes
    
    def get_worker_nodes(self) -> List[str]:
        return []
    
    def get_router_functions(self) -> List[str]:
        return [self.to_routing_function]

@dataclass
class WorkerTransition:
    from_node_name: str
    to_worker: str
    state_class_name: str
    field_name: str
    line: str
    
    def get_source_nodes(self) -> List[str]:
        return [self.from_node_name]
    
    def get_dest_nodes(self) -> List[str]:
        return [self.to_worker]
    
    def get_worker_nodes(self) -> List[str]:
        return [self.to_worker]
    
    def get_router_functions(self) -> List[str]:
        return []

def parse_transition(line, is_first_line=False):
    """
    Parse a line of text in one of the specified formats and convert it directly
    into the appropriate transition class.
    
    Args:
        line (str): A line of text in one of the supported formats
        
    Returns:
        Union[SingleNodeTransition, MultiSourceTransition, MultiTargetTransition, 
              RoutingTransition, WorkerTransition]: The appropriate transition object
    """
    # First parse the line into a dictionary
    parsed_dict = parse_line(line, is_first_line)

    # Then convert the dictionary to the appropriate transition class
    # Single node to single node
    if "state_class_name" in parsed_dict and "to_worker" not in parsed_dict:
        return StartGraphTransition(
            state_class_name=parsed_dict["state_class_name"],
            start_node=parsed_dict["start_node"],
            line=parsed_dict["line"]
        )
    elif "from_node_name" in parsed_dict and "to_node_name" in parsed_dict:
        return SingleNodeTransition(
            from_node_name=parsed_dict["from_node_name"],
            to_node_name=parsed_dict["to_node_name"],
            line=parsed_dict["line"]
        
        )
    
    # Multiple source nodes to single node
    elif "from_nodes" in parsed_dict and "to_node_name" in parsed_dict:
        return MultiSourceTransition(
            from_nodes=parsed_dict["from_nodes"],
            to_node_name=parsed_dict["to_node_name"],
            line=parsed_dict["line"]
        )
    
    # Single node to multiple target nodes
    elif "from_node_name" in parsed_dict and "to_nodes" in parsed_dict and "to_routing_function" not in parsed_dict:
        return MultiTargetTransition(
            from_node_name=parsed_dict["from_node_name"],
            to_nodes=parsed_dict["to_nodes"],
            line=parsed_dict["line"]
        
        )
    
    # Routing function
    elif "from_node_name" in parsed_dict and "to_routing_function" in parsed_dict:
        return RoutingTransition(
            from_node_name=parsed_dict["from_node_name"],
            to_routing_function=parsed_dict["to_routing_function"],
            to_nodes=parsed_dict["to_nodes"],
            line=parsed_dict["line"]
        
        )
    
    # Worker
    elif "from_node_name" in parsed_dict and "to_worker" in parsed_dict:
        return WorkerTransition(
            from_node_name=parsed_dict["from_node_name"],
            to_worker=parsed_dict["to_worker"],
            state_class_name=parsed_dict["state_class_name"],
            field_name=parsed_dict["field_name"],
            line=parsed_dict["line"]
        
        )
    
    else:
        raise ValueError(f"Unrecognized transition format: {parsed_dict}")

def parse_graph(graph_text):
    """
    Parse an entire graph in DSL format into a list of transition objects.
    
    Args:
        graph_text (str): The complete graph text in DSL format
        
    Returns:
        List[Union[SingleNodeTransition, MultiSourceTransition, MultiTargetTransition, 
                  RoutingTransition, WorkerTransition]]: List of transition objects
    """
    transitions = []
    lines = graph_text.strip().split('\n')
    
    # Skip comment lines and process valid transitions
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        # Skip comment lines (starting with #)
        if line.strip().startswith('#'):
            continue
            
        # Parse the transition line
        try:
            transition = parse_transition(line, is_first_line = len(transitions)==0)
            transitions.append(transition)
        except ValueError as e:
            print(f"Warning: Could not parse line '{line}': {e}")
    
    return transitions

from dataclasses import dataclass
from typing import List, Set, Optional, Tuple


@dataclass
class GraphValidationResult:
    """Represents the result of validating a graph."""
    is_valid: bool
    state_class_name: Optional[str] = None
    start_field: Optional[str] = None
    start_node: Optional[str] = None
    source_nodes: Set[str] = None
    dest_nodes: Set[str] = None
    worker_nodes: Set[str] = None
    router_functions: Set[str] = None
    validation_messages: List[str] = None
    orphan_source_nodes: Set[str] = None
    orphan_dest_nodes: Set[str] = None
    
    def __post_init__(self):
        # Initialize any None collections as empty
        if self.source_nodes is None:
            self.source_nodes = set()
        if self.dest_nodes is None:
            self.dest_nodes = set()
        if self.worker_nodes is None:
            self.worker_nodes = set()
        if self.router_functions is None:
            self.router_functions = set()
        if self.validation_messages is None:
            self.validation_messages = []
        if self.orphan_source_nodes is None:
            self.orphan_source_nodes = set()
        if self.orphan_dest_nodes is None:
            self.orphan_dest_nodes = set()

    # human readable format with one line per field
    def __str__(self):
        return f"""
Graph Validation Result:
    is_valid: {self.is_valid}
    validation_messages: {self.validation_messages}
    
Graph State:
    state_class_name: {self.state_class_name}
    start_field: {self.start_field}
Nodes:
    start_node: {self.start_node}
    source_nodes: {self.source_nodes}
    dest_nodes: {self.dest_nodes}
    worker_nodes: {self.worker_nodes}
Conditional Edges:
    router_functions: {self.router_functions}

        """

def validate_graph(transitions):
    """
    Validates a graph represented by a list of transitions.
    
    Args:
        transitions: List of transition objects
        
    Returns:
        GraphValidationResult: Object containing validation results
    """
    if not transitions:
        return GraphValidationResult(
            is_valid=False,
            validation_messages=["Graph is empty"]
        )
    
    result = GraphValidationResult(is_valid=True)
    
    # Extract state class name and starting node
    result.state_class_name = transitions[0].state_class_name
    result.start_node = transitions[0].start_node
    result.dest_nodes.add(transitions[0].start_node)
    
    # Check if state class name contains a field
    if '.' in result.state_class_name:
        result.state_class_name, result.start_field = result.state_class_name.split('.')
    
    # Collect all nodes and functions
    for transition in transitions[1:]:
        result.source_nodes.update(transition.get_source_nodes())
        result.dest_nodes.update(transition.get_dest_nodes())
        result.worker_nodes.update(transition.get_worker_nodes())
        result.router_functions.update(transition.get_router_functions())
    
    # Find orphan nodes
    result.orphan_source_nodes = result.source_nodes - result.dest_nodes
    result.orphan_dest_nodes = result.dest_nodes - result.source_nodes - {'END'}
    
    # Add validation messages for orphan nodes
    if result.orphan_source_nodes:
        print("FOUND ORPHAN SOURCE NODES")
        print(result.source_nodes, result.dest_nodes, result.orphan_source_nodes)
        result.validation_messages.append(f"Orphan source nodes: {result.orphan_source_nodes}")
        result.is_valid = False
    
    if result.orphan_dest_nodes:
        result.validation_messages.append(f"Orphan destination nodes: {result.orphan_dest_nodes}")
        result.is_valid = False
    
    return result

if __name__ == "__main__":
    #for pg in graph_examples:
    #    print(validate_graph(parse_graph(pg)))

    # test with jokester
    parsed_graph = parse_graph(jokester)
    print(parsed_graph)
    validated_graph = validate_graph(parsed_graph)
    print(validated_graph)
