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
        assert "START(BeaAgentState) -> first_node" in result
        assert "first_node => END" in result

    def test_bare_start_fat_arrow(self):
        spec = "START => first_node\nfirst_node => END"
        result = preprocess_start_syntax(spec, "bea_agent")
        assert "START(BeaAgentState) => first_node" in result

    def test_start_with_parens_unchanged(self):
        spec = "START(MyState) => first_node\nfirst_node => END"
        result = preprocess_start_syntax(spec, "bea_agent")
        assert result == spec

    def test_old_classname_syntax_rewritten(self):
        spec = "MyState -> first_node\nfirst_node => END"
        result = preprocess_start_syntax(spec, "bea_agent")
        assert "START(BeaAgentState) => first_node" in result
        assert "first_node => END" in result

    def test_comments_before_start(self):
        spec = "# This is a comment\n# Another comment\nSTART -> first_node\nfirst_node => END"
        result = preprocess_start_syntax(spec, "my_graph")
        assert "START(MyGraphState) -> first_node" in result
        assert "# This is a comment" in result

    def test_hyphenated_graph_name(self):
        spec = "START -> first_node\nfirst_node => END"
        result = preprocess_start_syntax(spec, "my-cool-graph")
        assert "START(MyCoolGraphState) -> first_node" in result

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
        assert "START(BeaAgentState) -> first_node" in result


# --- Integration: bare START through parse_graph_spec ---

class TestBareStartIntegration:
    def test_parse_bare_start(self):
        spec = "START -> first_node\nfirst_node => END"
        spec = preprocess_start_syntax(spec, "bea_agent")
        graph, start_node = parse_graph_spec(spec)
        assert graph[start_node]["state"] == "BeaAgentState"

    def test_parse_bare_start_fat_arrow(self):
        spec = "START => plan_step\nplan_step => END"
        spec = preprocess_start_syntax(spec, "plan_and_execute")
        graph, start_node = parse_graph_spec(spec)
        assert graph[start_node]["state"] == "PlanAndExecuteState"

    def test_conditional_graph(self):
        spec = (
            "START => plan_step\n"
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

    def test_validate_bare_start_fat_arrow(self):
        spec = "START => first_node\nfirst_node => END"
        result = validate_graph(spec)
        assert "error" not in result or "START node not found" not in result.get("error", "")

    def test_validate_start_with_parens_still_works(self):
        spec = "START(State) => first_node\nfirst_node => END"
        result = validate_graph(spec)
        assert "graph" in result


# --- Old ClassName -> syntax rewriting ---

class TestOldSyntaxPreprocessing:
    def test_state_arrow_rewritten(self):
        """State -> orchestrator becomes START(GeneratedName) => orchestrator"""
        spec = "State -> orchestrator\norchestrator => END"
        result = preprocess_start_syntax(spec, "bea_orchestrator_worker")
        assert "START(BeaOrchestratorWorkerState) => orchestrator" in result

    def test_messages_state_rewritten(self):
        """MessagesState -> llm_call becomes START(BeaAgentState) => llm_call"""
        spec = "MessagesState -> llm_call\nllm_call => END"
        result = preprocess_start_syntax(spec, "bea_agent")
        assert "START(BeaAgentState) => llm_call" in result

    def test_state_dot_references_replaced(self):
        """State.field references are updated to match the new class name."""
        spec = (
            "State -> orchestrator\n"
            "orchestrator -> llm_call(State.sections)\n"
            "llm_call -> synthesizer\n"
            "synthesizer -> END\n"
        )
        result = preprocess_start_syntax(spec, "bea_orchestrator_worker")
        assert "BeaOrchestratorWorkerState.sections" in result
        # The old bare "State." (not as suffix of the new name) should be gone
        assert "llm_call(State.sections)" not in result

    def test_messages_state_dot_references_replaced(self):
        """MessagesState.field references are updated too."""
        spec = (
            "MessagesState -> orchestrator\n"
            "orchestrator -> llm_call(MessagesState.items)\n"
            "llm_call -> END\n"
        )
        result = preprocess_start_syntax(spec, "my_workflow")
        assert "MyWorkflowState.items" in result
        assert "MessagesState.items" not in result

    def test_comment_before_old_syntax(self):
        """Comments before old syntax are preserved."""
        spec = "# Orchestrator Worker\nState -> orchestrator\norchestrator => END"
        result = preprocess_start_syntax(spec, "bea_orchestrator_worker")
        assert "# Orchestrator Worker" in result
        assert "START(BeaOrchestratorWorkerState) => orchestrator" in result

    def test_explicit_start_parens_unchanged(self):
        """START(ExplicitName) is never rewritten."""
        spec = "START(ExplicitName) => first_node\nfirst_node => END"
        result = preprocess_start_syntax(spec, "bea_agent")
        assert result == spec

    def test_fat_arrow_old_syntax(self):
        """Old syntax with => arrow also works."""
        spec = "State => orchestrator\norchestrator => END"
        result = preprocess_start_syntax(spec, "my_graph")
        assert "START(MyGraphState) => orchestrator" in result

    def test_old_syntax_full_pipeline(self):
        """Old syntax produces correct state class through full parse."""
        spec = (
            "# Orchestrator Worker\n"
            "State -> orchestrator\n"
            "orchestrator -> llm_call(State.sections)\n"
            "llm_call -> synthesizer\n"
            "synthesizer -> END\n"
        )
        spec = preprocess_start_syntax(spec, "bea_orchestrator_worker")
        graph, start_node = parse_graph_spec(spec)
        assert graph[start_node]["state"] == "BeaOrchestratorWorkerState"

    def test_old_syntax_worker_pattern_preserved(self):
        """Worker pattern (State.field) still works after rewriting."""
        spec = (
            "State -> orchestrator\n"
            "orchestrator -> llm_call(State.sections)\n"
            "llm_call -> synthesizer\n"
            "synthesizer -> END\n"
        )
        spec = preprocess_start_syntax(spec, "bea_orchestrator_worker")
        workers = find_worker_functions(spec)
        assert len(workers) == 1
        assert workers[0][0] == "llm_call"
        assert workers[0][1] == "BeaOrchestratorWorkerState.sections"

    def test_old_syntax_gen_state_has_extra_field(self):
        """Worker pattern's iterable field appears in generated state."""
        spec = (
            "State -> orchestrator\n"
            "orchestrator -> llm_call(State.sections)\n"
            "llm_call -> synthesizer\n"
            "synthesizer -> END\n"
        )
        spec = preprocess_start_syntax(spec, "bea_orchestrator_worker")
        state_code = gen_state(spec)
        assert "BeaOrchestratorWorkerState" in state_code
        assert "sections" in state_code
