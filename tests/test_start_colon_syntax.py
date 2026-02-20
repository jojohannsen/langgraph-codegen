"""Tests for START:ClassName syntax preprocessing and integration."""

from langgraph_codegen.gen_graph import (
    preprocess_start_syntax,
    parse_graph_spec,
    validate_graph,
    gen_state,
    gen_graph,
    expand_chains,
)


class TestPreprocessStartColon:
    def test_basic_start_colon(self):
        spec = "START:MyState -> first_node\nfirst_node => END"
        result = preprocess_start_syntax(spec, "test")
        assert "START(MyState) => first_node" in result

    def test_start_colon_agent_state(self):
        spec = "START:AgentState -> get_docs"
        result = preprocess_start_syntax(spec, "rag")
        assert "START(AgentState) => get_docs" in result

    def test_start_colon_preserves_rest_of_spec(self):
        spec = "START:State -> a\na -> b\nb -> END"
        result = preprocess_start_syntax(spec, "test")
        assert "a -> b" in result
        assert "b -> END" in result

    def test_start_colon_with_comments(self):
        spec = "# Comment\nSTART:PlanExecute -> plan_step"
        result = preprocess_start_syntax(spec, "test")
        assert "# Comment" in result
        assert "START(PlanExecute) => plan_step" in result

    def test_bare_start_still_works(self):
        spec = "START -> first_node"
        result = preprocess_start_syntax(spec, "my_graph")
        assert "START(MyGraphState) => first_node" in result


class TestStartColonIntegration:
    def test_parse_through_full_pipeline(self):
        spec = "START:PlanExecute -> plan_step\nplan_step => END"
        spec = preprocess_start_syntax(spec, "test")
        graph, start_node = parse_graph_spec(spec)
        assert graph[start_node]["state"] == "PlanExecute"

    def test_with_expand_chains(self):
        spec = "START:AgentState -> get_docs -> format_docs -> generate -> END"
        spec = expand_chains(spec)
        spec = preprocess_start_syntax(spec, "rag")
        graph, start_node = parse_graph_spec(spec)
        assert graph[start_node]["state"] == "AgentState"
        assert "get_docs" in graph
        assert "generate" in graph

    def test_gen_state_with_start_colon(self):
        spec = "START:MyState -> node1\nnode1 => END"
        spec = preprocess_start_syntax(spec, "test")
        state_code = gen_state(spec)
        assert "MyState" in state_code

    def test_gen_graph_with_start_colon(self):
        spec = "START:State -> call_model\ncall_model -> should_call_tool ? tool_node : END\ntool_node -> call_model"
        spec = preprocess_start_syntax(spec, "react_agent")
        graph_code = gen_graph("react_agent", spec)
        assert "StateGraph(State)" in graph_code
        assert "add_node('call_model'" in graph_code


class TestStartColonValidation:
    def test_validate_accepts_start_colon(self):
        spec = "START:State -> first_node\nfirst_node => END"
        result = validate_graph(spec)
        assert "error" not in result or "START node not found" not in result.get("error", "")

    def test_validate_accepts_start_colon_no_space(self):
        spec = "START:MyState -> a\na -> END"
        result = validate_graph(spec)
        assert "error" not in result or "START node not found" not in result.get("error", "")
