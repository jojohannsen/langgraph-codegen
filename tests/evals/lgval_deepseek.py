import re
from typing import List, Dict, Set, Optional
import yaml

class GraphData:
    def __init__(self):
        self.state_class_name: str = ""
        self.node_function_names: Set[str] = set()
        self.router_function_names: Set[str] = set()
        self.worker_function_names: Set[str] = set()
        self.node_to_node: Dict[str, List[str]] = {}
        self.node_to_worker: Dict[str, List[str]] = {}
        self.worker_to_node: Dict[str, List[str]] = {}
        self.defined_nodes: Set[str] = set()
        self.referenced_nodes: Set[str] = set()

    def to_yaml(self) -> str:
        data = {
            'state_class_name': self.state_class_name,
            'node_function_names': sorted(list(self.node_function_names)),
            'router_function_names': sorted(list(self.router_function_names)),
            'worker_function_names': sorted(list(self.worker_function_names)),
            'node_to_node_transitions': self.node_to_node,
            'node_to_worker_transitions': self.node_to_worker,
            'worker_to_node_transitions': self.worker_to_node,
        }
        return yaml.dump(data, sort_keys=False)

class GraphValidator:
    def __init__(self):
        self.graph_data = GraphData()
        self.lines: List[str] = []
        self.current_line_num: int = 0
        self.errors: List[str] = []
        self.defined_nodes: Set[str] = set()
        self.node_definitions: Dict[str, int] = {}  # node name to line number

    def validate_graph(self, input_text: str) -> bool:
        self._reset()
        self.lines = input_text.splitlines()
        
        for line_num, line in enumerate(self.lines, 1):
            self.current_line_num = line_num
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if not self._process_line(line):
                return False
        
        return self._validate_node_references()

    def _reset(self):
        self.graph_data = GraphData()
        self.lines = []
        self.current_line_num = 0
        self.errors = []
        self.defined_nodes = set()
        self.node_definitions = {}

    def _process_line(self, line: str) -> bool:
        if not self.graph_data.state_class_name:
            return self._process_first_line(line)
        return self._process_regular_line(line)

    def _process_first_line(self, line: str) -> bool:
        pattern = r'^([A-Za-z_]\w*)\s*->\s*([A-Za-z_]\w*)$'
        match = re.fullmatch(pattern, line)
        if not match:
            self.errors.append(f"Line {self.current_line_num}: First line must be in format 'StateClassName -> first_node'")
            return False
        
        state_class, first_node = match.groups()
        self.graph_data.state_class_name = state_class
        self._add_defined_node(first_node)
        self.graph_data.node_function_names.add(first_node)
        return True

    def _process_regular_line(self, line: str) -> bool:
        if '->' not in line:
            self.errors.append(f"Line {self.current_line_num}: Missing '->' in line")
            return False
        
        lhs, rhs = line.split('->', 1)
        lhs_nodes = self._parse_lhs(lhs.strip())
        if not lhs_nodes:
            return False
        
        for node in lhs_nodes:
            if node in self.defined_nodes:
                self.errors.append(f"Line {self.current_line_num}: Node '{node}' is already defined on line {self.node_definitions[node]}")
                return False
            self._add_defined_node(node)
        
        return self._parse_rhs(rhs.strip(), lhs_nodes)

    def _parse_lhs(self, lhs: str) -> List[str]:
        nodes = [n.strip() for n in lhs.split(',')]
        nodes = [n for n in nodes if n]  # remove empty
        
        for node in nodes:
            if not self._is_valid_identifier(node):
                self.errors.append(f"Line {self.current_line_num}: Invalid node name '{node}' in LHS")
                return []
        
        return nodes

    def _parse_rhs(self, rhs: str, lhs_nodes: List[str]) -> bool:
        # Check for worker function
        worker_match = re.fullmatch(r'([A-Za-z_]\w*)\(([A-Za-z_]\w*)\.([A-Za-z_]\w*)\)', rhs)
        if worker_match:
            worker_fn, state_class, state_field = worker_match.groups()
            if state_class != self.graph_data.state_class_name:
                self.errors.append(f"Line {self.current_line_num}: State class in worker function must be '{self.graph_data.state_class_name}'")
                return False
            
            self.graph_data.worker_function_names.add(worker_fn)
            for node in lhs_nodes:
                self.graph_data.node_to_worker.setdefault(node, []).append(f"{worker_fn}({state_class}.{state_field})")
            return True
        
        # Check for router function
        router_match = re.fullmatch(r'([A-Za-z_]\w*)\(([^)]+)\)', rhs)
        if router_match:
            router_fn, params = router_match.groups()
            param_nodes = [p.strip() for p in params.split(',')]
            param_nodes = [p for p in param_nodes if p]  # remove empty
            
            if len(param_nodes) < 2:
                self.errors.append(f"Line {self.current_line_num}: Router function must have at least 2 parameters")
                return False
            
            for node in param_nodes:
                if not self._is_valid_identifier(node):
                    self.errors.append(f"Line {self.current_line_num}: Invalid node name '{node}' in router parameters")
                    return False
                self.graph_data.referenced_nodes.add(node)
            
            self.graph_data.router_function_names.add(router_fn)
            for node in lhs_nodes:
                self.graph_data.node_to_node.setdefault(node, []).append(f"{router_fn}({', '.join(param_nodes)})")
            return True
        
        # Simple node references
        nodes = [n.strip() for n in rhs.split(',')]
        nodes = [n for n in nodes if n]  # remove empty
        
        for node in nodes:
            if not self._is_valid_identifier(node):
                self.errors.append(f"Line {self.current_line_num}: Invalid node name '{node}' in RHS")
                return False
            self.graph_data.referenced_nodes.add(node)
        
        for node in lhs_nodes:
            self.graph_data.node_to_node.setdefault(node, []).extend(nodes)
        
        return True

    def _add_defined_node(self, node: str):
        self.defined_nodes.add(node)
        self.graph_data.node_function_names.add(node)
        self.node_definitions[node] = self.current_line_num

    def _validate_node_references(self) -> bool:
        # Check all referenced nodes are defined (except END)
        undefined_nodes = self.graph_data.referenced_nodes - self.defined_nodes - {'END'}
        if undefined_nodes:
            for node in undefined_nodes:
                self.errors.append(f"Node '{node}' is referenced but not defined")
            return False
        
        # Check no worker-to-worker transitions
        worker_nodes = set()
        for node in self.defined_nodes:
            if node in self.graph_data.worker_function_names:
                worker_nodes.add(node)
        
        for worker in worker_nodes:
            if worker in self.graph_data.node_to_node:
                self.errors.append(f"Worker '{worker}' cannot have node-to-node transitions")
                return False
            if worker in self.graph_data.node_to_worker:
                self.errors.append(f"Worker '{worker}' cannot have worker-to-worker transitions")
                return False
        
        return True

    @staticmethod
    def _is_valid_identifier(name: str) -> bool:
        return re.fullmatch(r'[A-Za-z_]\w*', name) is not None

def validate_and_process_graph(input_text: str) -> Optional[str]:
    validator = GraphValidator()
    if not validator.validate_graph(input_text):
        for error in validator.errors:
            print(f"Error: {error}")
        return None
    
    return validator.graph_data.to_yaml()

# Example usage:
if __name__ == "__main__":
    example_graph = """
# This is a comment
MyState -> Start
Start -> router1(NodeA, NodeB)
NodeA -> worker1(MyState.field1)
NodeB -> worker2(MyState.field2)
worker1, worker2 -> END
"""
    
    yaml_output = validate_and_process_graph(example_graph)
    if yaml_output:
        print("Validation successful. YAML output:")
        print(yaml_output)