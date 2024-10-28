from langgraph_codegen.gen_graph import gen_graph
from code_snippet_analyzer import CodeSnippetAnalyzer

def analyze_unconditional_edge():
    graph_spec = """
START(MyState) => first_node
first_node => second_node
second_node => END
"""
    graph_code = gen_graph("my_graph", graph_spec)
    analyzer = CodeSnippetAnalyzer()
    return analyzer.analyze_code(graph_code)

def analyze_conditional_edge():
    graph_spec = """
START(MyState) => first_node

first_node 
  condition_1 => second_node
  condition_2 => END

second_node => END
"""
    graph_code = gen_graph("test_2", graph_spec)
    analyzer = CodeSnippetAnalyzer()
    return analyzer.analyze_code(graph_code)

def analyze_multiple_nodes():
    graph_spec = """
START(MyState) => first_node
first_node => second_node, third_node

second_node, third_node => END
"""
    graph_code = gen_graph("multiple_nodes", graph_spec)
    analyzer = CodeSnippetAnalyzer()
    return analyzer.analyze_code(graph_code)

# Dictionary mapping test names to their analysis functions
tests = {
    "multiple_nodes": analyze_multiple_nodes,
    "unconditional_edge": analyze_unconditional_edge,
    "conditional_edge": analyze_conditional_edge,
}

# Test functions
def test_unconditional_edge():
    defined_variables, used_variables, undefined_variables, import_statements = tests["unconditional_edge"]()
    assert defined_variables == {"my_graph"}
    undefined_variables = {var for var in used_variables 
                           if var not in defined_variables and 
                           var not in [x.split(' ')[-1] for x in import_statements]}
    assert undefined_variables == {"MyState", "first_node", "second_node"}

def test_conditional_edge():
    defined_variables, used_variables, undefined_variables, import_statements = tests["conditional_edge"]()
    assert defined_variables == {"test_2"}
    undefined_variables = {var for var in used_variables 
                           if var not in defined_variables and 
                           var not in [x.split(' ')[-1] for x in import_statements]}
    assert undefined_variables == {"MyState", "first_node", "second_node", "condition_1", "condition_2"}
    #assert analyzer.get_snippet_summary("first_node") == (["MyState"], [], [])

def test_multiple_nodes():
    defined_variables, used_variables, undefined_variables, import_statements = tests["multiple_nodes"]()
    assert defined_variables == {"multiple_nodes"}
    assert undefined_variables == {"MyState", "first_node", "second_node", "third_node"}
