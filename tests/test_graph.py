from langgraph_codegen.gen_graph import gen_graph, gen_state
from code_snippet_analyzer import CodeSnippetAnalyzer

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
    defined_variables, used_variables, undefined_variables, import_statements = analyzer.analyze_code(graph_code)
    assert defined_variables == {"my_graph"}
    undefined_variables = {var for var in used_variables 
                           if var not in defined_variables and 
                           var not in [x.split(' ')[-1] for x in import_statements]}
    assert undefined_variables == {"MyState", "first_node", "second_node"}

def test_conditional_edge():
    graph_code = gen_graph("test_2", tests["conditional_edge"])
    analyzer = CodeSnippetAnalyzer()
    defined_variables, used_variables, undefined_variables, import_statements = analyzer.analyze_code(graph_code)
    assert defined_variables == {"test_2"}
    undefined_variables = {var for var in used_variables 
                           if var not in defined_variables and 
                           var not in [x.split(' ')[-1] for x in import_statements]}
    assert undefined_variables == {"MyState", "first_node", "second_node", "condition_1", "condition_2"}
    #assert analyzer.get_snippet_summary("first_node") == (["MyState"], [], [])

def test_multiple_nodes():
    graph_code = gen_graph("multiple_nodes", tests["multiple_nodes"])
    analyzer = CodeSnippetAnalyzer()
    defined_variables, used_variables, undefined_variables, import_statements = analyzer.analyze_code(graph_code)
    assert defined_variables == {"multiple_nodes"}
    assert undefined_variables == {"MyState", "first_node", "second_node", "third_node"}

def test_gen_state():
    mock_graph_state = gen_state(tests["conditional_edge"])
    graph_code = gen_graph("test_gs", tests["conditional_edge"])
    print("mock_graph_state", mock_graph_state)
    print("graph_code", graph_code)
    analyzer = CodeSnippetAnalyzer()
    code = mock_graph_state + graph_code
    defined_variables, used_variables, undefined_variables, import_statements = analyzer.analyze_code(code)
    print("defined_variables", defined_variables)
    assert defined_variables == {"test_gs", "ConditionalEdgeTestState"}
    undefined_variables = {var for var in used_variables 
                           if var not in defined_variables and 
                           var not in [x.split(' ')[-1] for x in import_statements]}
    assert undefined_variables == {"first_node", "second_node", "condition_1", "condition_2"}
