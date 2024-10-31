try:
    # Try installed package first
    from langgraph_codegen.gen_graph import gen_graph, gen_state
except ImportError:
    # Fall back to local development path
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from langgraph_codegen.gen_graph import gen_graph, gen_state
    
from code_snippet_analyzer import CodeSnippetAnalyzer
from typing import Annotated

# Dictionary mapping test names to their graph specifications
tests = {
    "multiple_nodes": """
START(MyState) => first_node
first_node => second_node, third_node

second_node, third_node => END
""",
    "unconditional_edge": """
START(MyState) => first_node
first_node => second_node
second_node => END
""",
    "conditional_edge": """
START(ConditionalEdgeTestState) => first_node

first_node 
  condition_1 => second_node
  condition_2 => END

second_node => END
"""
}

# Test functions
def test_unconditional_edge():
    graph_code = gen_graph("my_graph", tests["unconditional_edge"])
    analyzer = CodeSnippetAnalyzer()
    defined_variables, used_variables, undefined_variables, import_statements = analyzer.analyze_code(no_import(graph_code))
    assert defined_variables == {"my_graph"}
    assert undefined_variables == {"MyState", "first_node", "second_node"}

def test_conditional_edge():
    print(":::GRAPH_SPEC:::", tests["conditional_edge"], ":::END_OF_GRAPH_SPEC:::")
    graph_code = gen_graph("test_2", tests["conditional_edge"])
    print("GRAPH CODE:::", graph_code, ":::END_OF_GRAPH_CODE:::")    #assert analyzer.get_snippet_summary("first_node") == (["MyState"], [], [])

def test_multiple_nodes():
    graph_code = gen_graph("multiple_nodes", tests["multiple_nodes"])
    analyzer = CodeSnippetAnalyzer()
    defined_variables, used_variables, undefined_variables, import_statements = analyzer.analyze_code(no_import(graph_code))
    assert defined_variables == {"multiple_nodes"}
    assert undefined_variables == {"MyState", "first_node", "second_node", "third_node"}

def no_import(code):
    return "\n".join(line for line in code.split("\n") if not line.startswith("from ") and not line.startswith("import "))

# exec doesn't do imports, so i can't put it in the code that is executed
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph
from typing import TypedDict
from typing import Annotated
from langgraph.graph import START
from langgraph.graph import END
def test_gen_state():
    mock_graph_state = gen_state(tests["conditional_edge"])
    graph_code = gen_graph("test_gs", tests["conditional_edge"])
    print("mock_graph_state", mock_graph_state)
    print("graph_code", graph_code)
    analyzer = CodeSnippetAnalyzer()
    fake_nodes_and_conditions = """
def first_node(state):
    pass

def second_node(state):
    pass

def condition_1(state):
    return True

def condition_2(state):
    return True
"""
    code = no_import(mock_graph_state) + no_import(graph_code)
    defined_variables, used_variables, undefined_variables, import_statements = analyzer.analyze_code(code)
    print("undefined_variables", undefined_variables)
    assert defined_variables == {'last_state', 'ConditionalEdgeTestState', 'states', 'test_gs', 
                                 'first_node_conditional_edges', 'after_first_node', 'state'}
    assert undefined_variables == {"first_node", "second_node", "condition_1", "condition_2"}
    # verify that code can be executed
    try:
        code = f"{fake_nodes_and_conditions}\n{code}"
        print("CODE:::", code)
        exec(code)
    except Exception as e:
        print("ERROR:::", e)
        assert False

if __name__ == "__main__":
    test_gen_state()