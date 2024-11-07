# langgraph-codegen
##### Quick Start

To generate a graph from text:

```bash
lgcodegen my_graph simple.graph
```



##### Use function

Generates python code for parts of langgraph

```python
from langgraph_codegen import gen_graph

graph_spec = """
# required: start with StateClass and first_node
START(StateClass) => first_node

first_node
  should_go_to_second => second_node
  => third_node

second_node => third_node

third_node => END
"""

graph_code = gen_graph("my_graph", graph_spec)
print(graph_code)
```

Output is:
```python
# GENERATED code, creates compiled graph: my_graph
my_graph = StateGraph(StateClass)
my_graph.add_node('first_node', first_node)
my_graph.add_node('should_go_to_second', should_go_to_second)
my_graph.add_node('second_node', second_node)
my_graph.add_node('third_node', third_node)
my_graph.add_edge(START, 'first_node')
my_graph.add_edge('should_go_to_second', 'second_node')
my_graph.add_edge('should_go_to_second', 'third_node')
my_graph.add_edge('second_node', 'third_node')
my_graph.add_edge('third_node', END)

my_graph = my_graph.compile()
```

#### Syntax

```START(StateClass) => first_node``` required

```# anything after pound sign is ignored```

```node_1 => node_2``` unconditional edge

```python
node_X
  condition_A => node_Y
  condition_B => node_Z
  => END  # unconditional if all above conditions fail
```

```node_1 => node_2, node_3``` ok to transition to multiple nodes.

##### Why This DSL Was Made

The main thing I want to do is condense larger patterns into the DSL, to make it easier to experiment with and evaluate graph architectures.

The thing I like about the code with the DSL is that both Nodes and Conditional Edges are represented by functions that take the Graph State as a parameter.  The second thing I like about it is that Nodes have a single name, it's in the text graph, and there's a function with that name.

The langgraph graph GraphBuilder is way more flexible, but in many cases an equivalent DSL version is easier to understand and easier to modify, and easier to experiment with different graph architectures.
