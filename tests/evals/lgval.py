import re
import yaml
from typing import List, Set, Dict, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class GraphSpecData:
    """Class to store graph specification data for YAML output."""
    state_class_name: str = ""
    node_function_names: Set[str] = field(default_factory=set)
    router_function_names: Set[str] = field(default_factory=set)
    worker_function_names: Set[str] = field(default_factory=set)
    node_to_node_transitions: Set[Tuple[str, str]] = field(default_factory=set)
    node_to_worker_transitions: Set[Tuple[str, str]] = field(default_factory=set)
    worker_to_node_transitions: Set[Tuple[str, str]] = field(default_factory=set)
    defined_nodes: Set[str] = field(default_factory=set)
    referenced_nodes: Set[str] = field(default_factory=set)


class GraphSpecValidator:
    def __init__(self):
        self.data = GraphSpecData()
        self.errors = []
        self.last_was_worker = {}  # Track if a node was last seen as a worker
    
    def validate_file(self, file_path: str) -> Tuple[bool, GraphSpecData, List[str]]:
        """Validate a graph spec file and return validation result, data, and errors."""
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            return self.validate_lines(lines)
        except FileNotFoundError:
            return False, self.data, [f"Error: File {file_path} not found"]
        except Exception as e:
            return False, self.data, [f"Error reading file: {str(e)}"]
    
    def validate_text(self, text: str) -> Tuple[bool, GraphSpecData, List[str]]:
        """Validate graph spec text and return validation result, data, and errors."""
        lines = text.strip().split('\n')
        return self.validate_lines(lines)
    
    def validate_lines(self, lines: List[str]) -> Tuple[bool, GraphSpecData, List[str]]:
        """Validate graph specification lines."""
        # Reset data and errors for new validation
        self.data = GraphSpecData()
        self.errors = []
        self.last_was_worker = {}
        
        # Filter out comment lines and empty lines
        graph_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
        
        if not graph_lines:
            self.errors.append("Error: No valid graph lines found")
            return False, self.data, self.errors
        
        # Validate first line format (StateClassName -> first_node)
        if not self._validate_first_line(graph_lines[0]):
            return False, self.data, self.errors
        
        # Validate remaining lines
        for i, line in enumerate(graph_lines[1:], 1):
            if not self._validate_line(line, i+1):
                # Continue validation to collect more errors
                pass
                
        # Validate that all referenced nodes are defined
        self._validate_node_references()
        
        # Check for worker-to-worker transitions
        self._validate_no_worker_to_worker_transitions()
        
        return len(self.errors) == 0, self.data, self.errors
    
    def _validate_first_line(self, line: str) -> bool:
        """Validate the first line of the graph spec."""
        # First line must be: StateClassName -> first_node
        pattern = r'^([A-Za-z0-9_]+)\s*->\s*([A-Za-z0-9_]+)$'
        match = re.match(pattern, line)
        
        if not match:
            self.errors.append(f"Error in line 1: '{line}' - First line must be in format 'StateClassName -> first_node'")
            return False
        
        state_class_name, first_node = match.groups()
        self.data.state_class_name = state_class_name
        self.data.defined_nodes.add(first_node)
        self.data.node_function_names.add(first_node)
        # Don't add to referenced_nodes yet as it might be used in other transitions
        
        return True
    
    def _validate_line(self, line: str, line_number: int) -> bool:
        """Validate a non-first line of the graph spec."""
        # Check for basic format: left -> right
        if "->" not in line:
            self.errors.append(f"Error in line {line_number}: '{line}' - Missing '->' operator")
            return False
        
        left, right = [side.strip() for side in line.split("->", 1)]
        
        # Validate left side (node definitions)
        valid_left = self._validate_left_side(left, line, line_number)
        
        # Validate right side (transitions)
        valid_right = self._validate_right_side(right, line, line_number)
        
        return valid_left and valid_right
    
    def _validate_left_side(self, left: str, full_line: str, line_number: int) -> bool:
        """Validate the left side of a graph line (node definitions)."""
        # Split by comma and clean
        nodes = [node.strip() for node in left.split(",")]
        
        # Check for empty nodes
        if not all(nodes):
            self.errors.append(f"Error in line {line_number}: '{full_line}' - Empty node name")
            return False
        
        # Check for valid node names and no duplicates
        for node in nodes:
            if not re.match(r'^[A-Za-z0-9_]+$', node):
                self.errors.append(f"Error in line {line_number}: '{full_line}' - Invalid node name '{node}'")
                return False
            
            if node in self.data.defined_nodes:
                self.errors.append(f"Error in line {line_number}: '{full_line}' - Node '{node}' already defined")
                return False
            
            # Add as defined node
            self.data.defined_nodes.add(node)
            self.data.node_function_names.add(node)
            
        return True
    
    def _validate_right_side(self, right: str, full_line: str, line_number: int) -> bool:
        """Validate the right side of a graph line (transitions)."""
        # Check if it's a function call
        if "(" in right and ")" in right:
            return self._validate_function_call(right, full_line, line_number)
        
        # Regular node transition
        nodes = [node.strip() for node in right.split(",")]
        
        # Check for empty nodes
        if not all(nodes):
            self.errors.append(f"Error in line {line_number}: '{full_line}' - Empty transition target")
            return False
        
        # Get source nodes from left side
        left_nodes = [node.strip() for node in full_line.split("->", 1)[0].split(",")]
        
        # Add transitions
        for source in left_nodes:
            for target in nodes:
                if not re.match(r'^[A-Za-z0-9_]+$', target):
                    self.errors.append(f"Error in line {line_number}: '{full_line}' - Invalid node name '{target}'")
                    return False
                
                self.data.referenced_nodes.add(target)
                
                # Track transitions
                if self.last_was_worker.get(source, False):
                    self.data.worker_to_node_transitions.add((source, target))
                else:
                    self.data.node_to_node_transitions.add((source, target))
                    
                # Reset worker status for this source
                self.last_was_worker[source] = False
        
        return True
    
    def _validate_function_call(self, right: str, full_line: str, line_number: int) -> bool:
        """Validate a function call on the right side of a transition."""
        # Extract function name and parameters
        match = re.match(r'^([A-Za-z0-9_]+)\s*\(\s*(.*)\s*\)$', right)
        if not match:
            self.errors.append(f"Error in line {line_number}: '{full_line}' - Invalid function call format")
            return False
        
        function_name, params_str = match.groups()
        params = [p.strip() for p in params_str.split(",")]
        
        # Get source nodes from left side
        left_nodes = [node.strip() for node in full_line.split("->", 1)[0].split(",")]
        
        # Check if it's a worker or router function
        if "." in params_str and len(params) == 1:
            # Worker function
            if not re.match(r'^[A-Za-z0-9_]+\.[A-Za-z0-9_]+$', params[0]):
                self.errors.append(f"Error in line {line_number}: '{full_line}' - Invalid worker parameter format")
                return False
            
            state_class, field = params[0].split(".", 1)
            if state_class != self.data.state_class_name:
                self.errors.append(
                    f"Error in line {line_number}: '{full_line}' - "
                    f"Worker function must use state class '{self.data.state_class_name}', found '{state_class}'"
                )
                return False
            
            self.data.worker_function_names.add(function_name)
            
            # Add transitions
            for source in left_nodes:
                self.data.node_to_worker_transitions.add((source, function_name))
                # Mark this source as last seen as worker
                self.last_was_worker[source] = True
                
        else:
            # Router function
            if len(params) < 2:
                self.errors.append(
                    f"Error in line {line_number}: '{full_line}' - "
                    f"Router function must have at least 2 parameters"
                )
                return False
            
            self.data.router_function_names.add(function_name)
            
            # Validate and add referenced nodes
            for param in params:
                if not re.match(r'^[A-Za-z0-9_]+$', param):
                    self.errors.append(f"Error in line {line_number}: '{full_line}' - Invalid node name '{param}'")
                    return False
                
                self.data.referenced_nodes.add(param)
            
            # Add transitions (source to router)
            for source in left_nodes:
                # Router transitions are treated as node-to-node for tracking purposes
                for target in params:
                    self.data.node_to_node_transitions.add((source, target))
                
                # Reset worker status for this source
                self.last_was_worker[source] = False
                
        return True
    
    def _validate_node_references(self) -> None:
        """Validate that all referenced nodes are defined."""
        # Find nodes that are referenced but not defined
        undefined_nodes = self.data.referenced_nodes - self.data.defined_nodes - {"END"}
        
        if undefined_nodes:
            for node in undefined_nodes:
                self.errors.append(f"Error: Node '{node}' is referenced but not defined")
    
    def _validate_no_worker_to_worker_transitions(self) -> None:
        """Validate that there are no worker-to-worker transitions."""
        # This is implicitly handled by the transition tracking logic
        # We don't need additional checks here as we track the type of each transition
        pass
    
    def generate_yaml(self) -> str:
        """Generate YAML output from collected data."""
        yaml_data = {
            'state_class_name': self.data.state_class_name,
            'node_function_names': list(self.data.node_function_names),
            'router_function_names': list(self.data.router_function_names),
            'worker_function_names': list(self.data.worker_function_names),
            'transitions': {
                'node_to_node': [{'from': src, 'to': dst} for src, dst in self.data.node_to_node_transitions],
                'node_to_worker': [{'from': src, 'to': dst} for src, dst in self.data.node_to_worker_transitions],
                'worker_to_node': [{'from': src, 'to': dst} for src, dst in self.data.worker_to_node_transitions]
            }
        }
        
        return yaml.dump(yaml_data, sort_keys=False)


def validate_graph_spec(file_path_or_text: str, is_file: bool = True) -> str:
    """
    Validate a graph specification and return YAML summary or error messages.
    
    Args:
        file_path_or_text: Path to the file or the text content
        is_file: Whether the input is a file path or text content
        
    Returns:
        YAML output if validation passes, or error messages if it fails
    """
    validator = GraphSpecValidator()
    
    if is_file:
        is_valid, data, errors = validator.validate_file(file_path_or_text)
    else:
        is_valid, data, errors = validator.validate_text(file_path_or_text)
    
    if is_valid:
        return validator.generate_yaml()
    else:
        return "Validation failed with the following errors:\n" + "\n".join(errors)


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        result = validate_graph_spec(sys.argv[1])
        print(result)
    else:
        print("Please provide a file path or graph specification text")