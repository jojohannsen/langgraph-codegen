Here is a language we are using to specify a graph in langgraph.

Here are three example graphs that explain this language.

#### Graph 1: tell jokes

```
JokesterState -> get_joke_topic
# first we ask for topic
get_joke_topic -> tell_joke
# then we generate a joke, and display it
tell_joke -> ask_for_another
# then we ask user if they want another joke, we route based on that result
ask_for_another -> tell_another(tell_joke, END)

```

Things demonstrated in this graph:

1. Comment lines begin with "#"
2. State Class Name -- the **first** word in the **first** non-comment line is the name of the State Class.
3. Node Function Names -- the **first** word in lines other than first line is a Node Function name
4. Routing Function Names -- a **routing function** appears on the right side of the "->" and has parentheses where parameters are the Node Function Names of destinations.  Note that 'END' is a special name denoting the graph should end execution.

**Graph Builder for Graph 1**

```python
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

checkpoint_saver = MemorySaver()
builder_jokester = StateGraph(JokesterState)
builder_jokester.add_node('get_joke_topic', get_joke_topic)
builder_jokester.add_node('tell_joke', tell_joke)
builder_jokester.add_node('ask_for_another', ask_for_another)
builder_jokester.add_edge(START, 'get_joke_topic')
builder_jokester.add_edge('get_joke_topic', 'tell_joke')
builder_jokester.add_edge('tell_joke', 'ask_for_another')
def ask_for_another(state: JokesterState):
    if tell_another_tell_joke(state):
        return 'tell_joke'
    elif tell_another_END(state):
        return 'END'
    return 'END'

ask_for_another_conditional_edges = { 'tell_joke': 'tell_joke', 'END': END }
builder_jokester.add_conditional_edges('ask_for_another', ask_for_another, ask_for_another_conditional_edges)


jokester = builder_jokester.compile(checkpointer=checkpoint_saver)
```



##### Graph 2: parallel execution

```
State -> get_topic
get_topic -> story, joke, poem
# generate a story, joke, and poem based on topic
story, joke, poem -> aggregator
# combine the results and end
aggregator -> END
```

Things demonstrated in this graph:

1. Parallel execution, when the right side of the "->" is a comma separated list, all three of these are a destination.  They all execute in parallel.
1. Multiple nodes before the "->" means these nodes independently and unconditionally going to the same destination node,

##### Graph Builder code for Graph 2

```python
from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

checkpoint_saver = MemorySaver()
builder_parallelization = StateGraph(State)
builder_parallelization.add_node('get_topic', get_topic)
builder_parallelization.add_node('story', story)
builder_parallelization.add_node('joke', joke)
builder_parallelization.add_node('poem', poem)
builder_parallelization.add_edge(START, 'get_topic')
builder_parallelization.add_edge('get_topic', 'story')
builder_parallelization.add_edge('get_topic', 'joke')
builder_parallelization.add_edge('get_topic', 'poem')
builder_parallelization.add_edge('story', END)
builder_parallelization.add_edge('joke', END)
builder_parallelization.add_edge('poem', END)

parallelization = builder_parallelization.compile(checkpointer=checkpoint_saver)
```



---



Here's another way to make sense of the graph specification language.

- Comment lines begin with '#'.

 - The first word in the first non-comment line is the name of a State class.  The State class holds
information needed during the graph execution.

For example:
```
# description of node_1 behavior
node_1 -> node_2
```
These lines are the specification for node_1.

In some cases, node_1 might need to choose its destination
```
# node_1 might go to either node_2 or node_3
node_1 -> router_function(node_2, node_3)
```
The router function is similar to the Node function in that it takes the State as a parameter.
It differs in the return value:  the router function returns a string, the name of the node function to route to.

- In all other non-comment lines, the first word in the line (excluding lines that start with white space)
is the name of a Node function.  The Node function takes the State class as a parameter.

The fields stored in State are based on what the nodes do.

Everything we ask for, any sort of user input, we save in the State, in either a field or a list.
Every response that is generated, we also save in the State.

The text in the pseudocode are function names, there are no state fields named.