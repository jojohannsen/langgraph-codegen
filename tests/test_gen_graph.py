try:
    # Try installed package first
    from langgraph_codegen.gen_graph import (
        gen_graph, gen_state, parse_graph_spec, validate_graph,
        expand_chains, preprocess_start_syntax,
    )
except ImportError:
    # Fall back to local development path
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from langgraph_codegen.gen_graph import (
        gen_graph, gen_state, parse_graph_spec, validate_graph,
        expand_chains, preprocess_start_syntax,
    )

def test_parse_graph_spec_conditions():
    # Test graph with various condition types
    graph_spec = """
START(XState) => node1
    
node1
    is_valid => node2
    is_error => error_node
    => final_node

node2 => END

error_node => END

final_node => END
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
    start(State) => node1, node2

    node1
        is_ready => final_node
        => error_node

    node2 => final_node

    final_node => END

    error_node => END
    """

    graph, start_node = parse_graph_spec(graph_spec)

    # Verify parallel edges from start
    assert graph["START"]["edges"][0] == {
        "condition": "true_fn",
        "destination": "node1, node2"
    }

    # Verify conditional edges in node1
    assert len(graph["node1"]["edges"]) == 2
    assert graph["node1"]["edges"] == [
        {"condition": "is_ready", "destination": "final_node"},
        {"condition": "true_fn", "destination": "error_node"}
    ] 

def test_parse_graph_spec_workflow():
    # Test graph representing a data processing workflow
    graph_spec = """
    START(State) => process_input

    process_input => validate_data

    validate_data
        is_valid => transform_data
        is_invalid => handle_error
        => END

    transform_data => store_result

    store_result => END

    handle_error => END
    """

    graph, start_node = parse_graph_spec(graph_spec)

    # Verify start node configuration
    assert start_node == "START"
    assert graph["START"]["state"] == "State"
    assert graph["START"]["edges"] == [
        {"condition": "true_fn", "destination": "process_input"}
    ]

    # Verify linear flow from process_input to validate_data
    assert graph["process_input"]["edges"] == [
        {"condition": "true_fn", "destination": "validate_data"}
    ]

    # Verify validate_data branching logic
    assert len(graph["validate_data"]["edges"]) == 3
    assert graph["validate_data"]["edges"] == [
        {"condition": "is_valid", "destination": "transform_data"},
        {"condition": "is_invalid", "destination": "handle_error"},
        {"condition": "true_fn", "destination": "END"}
    ]

    # Verify transform_data to store_result flow
    assert graph["transform_data"]["edges"] == [
        {"condition": "true_fn", "destination": "store_result"}
    ]

    # Verify terminal nodes
    for node in ["store_result", "handle_error"]:
        assert graph[node]["edges"] == [
            {"condition": "true_fn", "destination": "END"}
        ]

    # now just generate graph code and print it
    graph_code = gen_graph("test_graph", graph_spec)
    print(graph_code)

def test_new_notation_simple_chain():
    """Test new notation with chained arrows and START:Class syntax."""
    graph_spec = "START:State -> process_input -> validate_data\nvalidate_data -> route(transform_data, handle_error, END)\ntransform_data -> store_result -> END\nhandle_error -> END"
    graph_spec = expand_chains(graph_spec)
    graph_spec = preprocess_start_syntax(graph_spec, "simple")
    graph, start_node = parse_graph_spec(graph_spec)

    assert graph[start_node]["state"] == "State"
    assert "process_input" in graph
    assert "validate_data" in graph
    assert "transform_data" in graph
    assert "store_result" in graph
    assert "handle_error" in graph


def test_new_notation_rag_pipeline():
    """Test RAG pipeline in new notation with full chaining."""
    graph_spec = "START:AgentState -> get_docs -> format_docs -> format_prompt -> generate -> END"
    graph_spec = expand_chains(graph_spec)
    graph_spec = preprocess_start_syntax(graph_spec, "rag")
    graph, start_node = parse_graph_spec(graph_spec)

    assert graph[start_node]["state"] == "AgentState"
    for node in ["get_docs", "format_docs", "format_prompt", "generate"]:
        assert node in graph

    # Verify linear flow
    assert graph["get_docs"]["edges"][0]["destination"] == "format_docs"
    assert graph["format_docs"]["edges"][0]["destination"] == "format_prompt"
    assert graph["format_prompt"]["edges"][0]["destination"] == "generate"
    assert graph["generate"]["edges"][0]["destination"] == "END"


def test_new_notation_gen_graph():
    """Test gen_graph output with new notation spec."""
    graph_spec = "START:State -> call_model\ncall_model -> should_call_tool ? tool_node : END\ntool_node -> call_model"
    graph_spec = expand_chains(graph_spec)
    graph_spec = preprocess_start_syntax(graph_spec, "react_agent")
    graph_code = gen_graph("react_agent", graph_spec)
    assert "StateGraph(State)" in graph_code
    assert "add_node('call_model'" in graph_code
    assert "add_node('tool_node'" in graph_code


if __name__ == "__main__":
    #test_parse_graph_spec_conditions()
    #test_parse_graph_spec_parallel_conditions()
    test_parse_graph_spec_workflow()
