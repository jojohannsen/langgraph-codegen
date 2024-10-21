from langgraph_codegen.gen_graph import gen_graph

def test_unconditional_edge():
    graph_spec = """
START(MyState) => first_node
first_node => second_node
second_node => END
"""
    graph_code = gen_graph("my_graph", graph_spec)

