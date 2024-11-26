import pytest
import sys
from textwrap import dedent

try:
    from langgraph_codegen.gen_graph import (
        validate_graph, 
        parse_graph_spec,
        ERROR_MISSING_IMPORTS,
        ERROR_START_NODE_NOT_FOUND
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from langgraph_codegen.gen_graph import (
        validate_graph, 
        parse_graph_spec,
        ERROR_MISSING_IMPORTS,
        ERROR_START_NODE_NOT_FOUND
    )

# Have not found a way to test this yet
#
# def test_missing_imports(monkeypatch):
#     """Test detection of missing required imports"""
#     graph_spec = """
#     START(State) => node1
    
#     node1
#         => END
#     """
    
#     # Simulate environment where required imports are missing
#     monkeypatch.delitem(sys.modules, "langchain", raising=False)
    
#     result = validate_graph(graph_spec)
#     assert "error" in result
#     assert ERROR_MISSING_IMPORTS in result["error"]
#     assert "from langgraph.graph" in result["solution"]

def test_missing_start_node():
    """Test validation of START node requirement"""
    graph_spec = """
    # This is a comment
    node1 => node2
    
    node2
        => END
    """
    
    result = validate_graph(graph_spec)
    assert "error" in result
    assert ERROR_START_NODE_NOT_FOUND in result["error"]
    assert "START(State) =>" in result["solution"]

def test_start_node_not_first():
    """Test validation that START must be the first non-comment node"""
    graph_spec = """
    # This is a comment
    node1 => node2
    
    START(State) => node1
    
    node2
        => END
    """
    
    result = validate_graph(graph_spec)
    assert "error" in result
    assert ERROR_START_NODE_NOT_FOUND in result["error"]
    assert "START(State) =>" in result["solution"]

def test_valid_start_node():
    """Test valid START node passes validation"""
    graph_spec = """
    # This is a comment
    START(State) => node1
    
    node1
        => END
    """
    
    result = validate_graph(graph_spec)
    assert "error" not in result
    assert "graph" in result
    print(result)


def test_multiple_errors(monkeypatch):
    """Test accumulation of multiple errors"""
    graph_spec = """
    # This is a comment
    node1 => node2
    
    node2
        => END
    """
    
    result = validate_graph(graph_spec)
    assert "error" in result
    assert "solution" in result
    
    # Should contain error and solution 
    assert ERROR_START_NODE_NOT_FOUND in result["error"]
    assert "START node" in result["solution"]


def test_single_error():
    """Test single error case still works"""
    graph_spec = """
    # This is a comment
    node1 => node2
    """
    
    result = validate_graph(graph_spec)
    assert "error" in result
    assert ERROR_START_NODE_NOT_FOUND in result["error"]

if __name__ == "__main__":
    pytest.main([__file__])