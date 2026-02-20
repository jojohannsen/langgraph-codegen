# Graph Notation Specification

A concise notation for defining directed graphs where nodes correspond to Python functions operating on a shared State object.

---

## 1. Basic Syntax

Each line defines one or more edges using the `->` operator:

```
source -> destination
```

Multiple transitions can be chained on a single line:

```
source -> middle -> destination
```

## 2. START and END

Every graph begins with `START` and terminates at `END`.

```
START -> node_1 -> node_2 -> END
```

### State Class

To specify the State class the graph operates on, use `START:StateClassName`:

```
START:MyState -> node_1 -> node_2 -> END
```

When no state class is needed, use plain `START`.

## 3. Multiple Destinations (Fan-Out / Fan-In)

Comma-separated nodes indicate parallel branching. When a comma group appears mid-chain, all listed nodes fan out from the preceding source **and** converge into the following destination.

```
node_1 -> node_2, node_3 -> node_4
```

This expands to:

```
node_1 -> node_2
node_1 -> node_3
node_2 -> node_4
node_3 -> node_4
```

Fan-out to END works the same way:

```
node_1 -> node_2, node_3 -> END
```

## 4. Conditional Routing

### Boolean Condition

A condition function routes to one of two nodes based on a boolean result:

```
node_1 -> condition_func ? node_if_true : node_if_false
```

`condition_func` is a Python function that receives the current State and returns `True` or `False`.

### Switch Function

A switch function routes to one of several nodes:

```
node_1 -> switch_func(node_2, node_3, node_4)
```

`switch_func` is a Python function that receives the current State and returns the name of the next node to execute.

## 5. Worker Functions

A worker function operates on a specific field of the State:

```
node_1 -> worker_func(state_field_name)
```

Workers can chain to a subsequent node:

```
node_1 -> worker_func(state_field_name) -> another_node
```

Or the transition from the worker can be specified on a separate line:

```
node_1 -> worker_func(state_field_name)
worker_func -> another_node
```

---

## Grammar Summary

| Pattern | Meaning |
|---|---|
| `START -> node` | Graph entry point |
| `START:StateClass -> node` | Entry point with explicit State class |
| `node -> END` | Graph exit |
| `node_a -> node_b` | Simple edge |
| `node_a -> node_b, node_c -> node_d` | Fan-out then fan-in |
| `node_a -> cond ? node_t : node_f` | Boolean conditional routing |
| `node_a -> switch(n1, n2, n3)` | Switch-based routing |
| `node_a -> worker(field) -> node_b` | Worker function on a state field |

## Full Example

```
START:AgentState -> fetch_data -> validate, transform -> merge
merge -> quality_check ? publish : review
review -> editor(draft_field) -> publish
publish -> END
```