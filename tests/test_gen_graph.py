try:
    # Try installed package first
    from langgraph_codegen.gen_graph import gen_graph, gen_state, parse_graph_spec, validate_graph
except ImportError:
    # Fall back to local development path
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from langgraph_codegen.gen_graph import gen_graph, gen_state, parse_graph_spec, validate_graph

def test_parse_graph_spec_conditions():
    # Test graph with various condition types
    graph_spec = """
START(XState) => node1
    
node1
    is_valid => node2
    is_error => error_node
    => final_node

node2
    => END

error_node
    => END

final_node
    => END
    """

    graph, start_node = parse_graph_spec(graph_spec)

    # Verify start node
    assert start_node == "START"
    assert graph["START"]["state"] == "XState"
    assert len(graph["START"]["edges"]) == 1
    assert graph["START"]["edges"][0] == {
        "condition": "true_fn",
        "destination": "node1"
    }

    # Verify node1's conditions
    assert len(graph["node1"]["edges"]) == 3
    assert graph["node1"]["edges"] == [
        {"condition": "is_valid", "destination": "node2"},
        {"condition": "is_error", "destination": "error_node"},
        {"condition": "true_fn", "destination": "final_node"}
    ]

    # Verify simple nodes with single true_fn conditions
    for node in ["node2", "error_node", "final_node"]:
        assert len(graph[node]["edges"]) == 1
        assert graph[node]["edges"][0] == {
            "condition": "true_fn",
            "destination": "END"
        }

def test_parse_graph_spec_parallel_conditions():
    # Test graph with parallel conditions (comma-separated destinations)
    graph_spec = """
    start(State)
        => node1, node2

    node1
        is_ready => final_node
        => error_node

    node2
        => final_node

    final_node
        => END

    error_node
        => END
    """

    graph, start_node = parse_graph_spec(graph_spec)

    # Verify parallel edges from start
    assert graph["start"]["edges"][0] == {
        "condition": "true_fn",
        "destination": "node1, node2"
    }

    # Verify conditional edges in node1
    assert len(graph["node1"]["edges"]) == 2
    assert graph["node1"]["edges"] == [
        {"condition": "is_ready", "destination": "final_node"},
        {"condition": "true_fn", "destination": "error_node"}
    ] 

