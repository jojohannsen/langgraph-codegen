from collections import defaultdict

class Graph:
    def __init__(self):
        self.nodes = set()
        self.edges = defaultdict(list)
        self.start_node = None
        self.end_node = None

    def add_node(self, node):
        self.nodes.add(node)

    def set_start_node(self, node):
        self.start_node = node
        self.add_node(node)

    def set_end_node(self, node):
        self.end_node = node
        self.add_node(node)

    def add_edge(self, from_node, to_node, condition="true"):
        self.add_node(from_node)
        self.add_node(to_node)
        self.edges[from_node].append((to_node, condition))

    def is_structurally_equivalent(self, other):
        if len(self.nodes) != len(other.nodes) or len(self.edges) != len(other.edges):
            return False
        self_mapping = self._create_structural_mapping()
        other_mapping = other._create_structural_mapping()
        return self_mapping == other_mapping

    def _create_structural_mapping(self):
        mapping = defaultdict(list)
        visited = set()

        def dfs(node, depth, path):
            if node in visited:
                return
            visited.add(node)
            edge_conditions = tuple(sorted(
                ("true" if condition == "true" else "named")
                for _, condition in self.edges[node]
            ))
            node_repr = (
                depth,
                "start" if node == self.start_node else "end" if node == self.end_node else "middle",
                len(self.edges[node]),
                edge_conditions
            )
            mapping[node_repr].append(path)
            for next_node, condition in self.edges[node]:
                dfs(next_node, depth + 1, path + ["true" if condition == "true" else "named"])

        dfs(self.start_node, 0, [])
        return dict(mapping)
