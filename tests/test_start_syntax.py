"""Tests for bare START -> DSL syntax and helper functions."""
import pytest
from langgraph_codegen.gen_graph import (
    snake_to_state_class,
    preprocess_start_syntax,
    parse_graph_spec,
    validate_graph,
    gen_state,
    find_worker_functions,
)


# --- snake_to_state_class ---

class TestSnakeToStateClass:
    def test_basic(self):
        assert snake_to_state_class("bea_agent") == "BeaAgentState"

    def test_single_word(self):
        assert snake_to_state_class("simple") == "SimpleState"

    def test_hyphens(self):
        assert snake_to_state_class("my-graph") == "MyGraphState"

    def test_mixed_hyphens_underscores(self):
        assert snake_to_state_class("my-cool_graph") == "MyCoolGraphState"

    def test_empty(self):
        assert snake_to_state_class("") == "State"

    def test_leading_trailing_underscores(self):
        assert snake_to_state_class("_foo_bar_") == "FooBarState"

    def test_numbers(self):
        assert snake_to_state_class("agent_v2") == "AgentV2State"

    def test_already_camel(self):
        # Even CamelCase input just gets capitalized + State
        assert snake_to_state_class("MyAgent") == "MyagentState"


# --- preprocess_start_syntax ---

class TestPreprocessStartSyntax:
    def test_bare_start_arrow(self):
        spec = "START -> first_node\nfirst_node => END"
        result = preprocess_start_syntax(spec, "bea_agent")
        assert "START(BeaAgentState) => first_node" in result
        assert "first_node => END" in result

    def test_comments_before_start(self):
        spec = "# This is a comment\n# Another comment\nSTART -> first_node\nfirst_node => END"
        result = preprocess_start_syntax(spec, "my_graph")
        assert "START(MyGraphState) => first_node" in result
        assert "# This is a comment" in result

    def test_hyphenated_graph_name(self):
        spec = "START -> first_node\nfirst_node => END"
        result = preprocess_start_syntax(spec, "my-cool-graph")
        assert "START(MyCoolGraphState) => first_node" in result

    def test_empty_spec(self):
        result = preprocess_start_syntax("", "bea_agent")
        assert result == ""

    def test_only_comments(self):
        spec = "# just a comment\n# another"
        result = preprocess_start_syntax(spec, "bea_agent")
        assert result == spec

    def test_preserves_indentation(self):
        spec = "  START -> first_node\nfirst_node => END"
        result = preprocess_start_syntax(spec, "bea_agent")
        assert "START(BeaAgentState) => first_node" in result


# --- Integration: bare START through parse_graph_spec ---

class TestBareStartIntegration:
    def test_parse_bare_start(self):
        spec = "START -> first_node\nfirst_node => END"
        spec = preprocess_start_syntax(spec, "bea_agent")
        graph, start_node = parse_graph_spec(spec)
        assert graph[start_node]["state"] == "BeaAgentState"

    def test_parse_bare_start_with_arrow(self):
        spec = "START -> plan_step\nplan_step => END"
        spec = preprocess_start_syntax(spec, "plan_and_execute")
        graph, start_node = parse_graph_spec(spec)
        assert graph[start_node]["state"] == "PlanAndExecuteState"

    def test_conditional_graph(self):
        spec = (
            "START -> plan_step\n"
            "plan_step => execute_step\n"
            "execute_step => replan_step\n"
            "replan_step\n"
            "  is_done => END\n"
            "  => execute_step\n"
        )
        spec = preprocess_start_syntax(spec, "plan_and_execute")
        graph, start_node = parse_graph_spec(spec)
        assert graph[start_node]["state"] == "PlanAndExecuteState"
        assert "replan_step" in graph


# --- validate_graph accepts bare START ---

class TestValidateGraphBareStart:
    def test_validate_bare_start_arrow(self):
        spec = "START -> first_node\nfirst_node => END"
        result = validate_graph(spec)
        # Should not report START node not found
        assert "error" not in result or "START node not found" not in result.get("error", "")



