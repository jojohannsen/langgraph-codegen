"""Tests for expand_chains() — expanding chained arrows into individual edges."""

from langgraph_codegen.gen_graph import (
    expand_chains, parse_graph_spec, transform_graph_spec,
    preprocess_start_syntax, gen_graph,
)


class TestSimpleChains:
    def test_two_arrows(self):
        result = expand_chains("a -> b -> c")
        assert "a -> b" in result
        assert "b -> c" in result

    def test_three_arrows(self):
        result = expand_chains("a -> b -> c -> d")
        assert "a -> b" in result
        assert "b -> c" in result
        assert "c -> d" in result

    def test_single_arrow_unchanged(self):
        result = expand_chains("a -> b")
        assert result.strip() == "a -> b"

    def test_no_arrow_unchanged(self):
        result = expand_chains("just a node")
        assert result.strip() == "just a node"

    def test_old_syntax_unchanged(self):
        result = expand_chains("node1 => node2")
        assert result.strip() == "node1 => node2"


class TestStartChains:
    def test_start_colon_chain(self):
        result = expand_chains("START:State -> a -> b")
        assert "START:State -> a" in result
        assert "a -> b" in result

    def test_start_colon_long_chain(self):
        result = expand_chains("START:AgentState -> get_docs -> format_docs -> generate -> END")
        lines = [l.strip() for l in result.strip().split('\n') if l.strip()]
        assert len(lines) == 4
        assert "START:AgentState -> get_docs" in result
        assert "get_docs -> format_docs" in result
        assert "format_docs -> generate" in result
        assert "generate -> END" in result


class TestFanOutFanIn:
    def test_basic_fan_out_fan_in(self):
        result = expand_chains("a -> b, c -> d")
        assert "a -> b, c" in result
        assert "b -> d" in result
        assert "c -> d" in result

    def test_fan_out_to_end(self):
        result = expand_chains("a -> b, c -> END")
        assert "a -> b, c" in result
        assert "b -> END" in result
        assert "c -> END" in result

    def test_fan_out_with_continuation(self):
        result = expand_chains("START:State -> call_llm_1, call_llm_2, call_llm_3 -> aggregator -> END")
        assert "START:State -> call_llm_1, call_llm_2, call_llm_3" in result
        assert "call_llm_1 -> aggregator" in result
        assert "call_llm_2 -> aggregator" in result
        assert "call_llm_3 -> aggregator" in result
        assert "aggregator -> END" in result

    def test_three_fan_out(self):
        result = expand_chains("a -> x, y, z -> b")
        assert "a -> x, y, z" in result
        assert "x -> b" in result
        assert "y -> b" in result
        assert "z -> b" in result


class TestWorkerChains:
    def test_worker_chain(self):
        result = expand_chains("a -> worker(field) -> b")
        assert "a -> worker(field)" in result
        assert "worker -> b" in result

    def test_worker_chain_to_end(self):
        result = expand_chains("orchestrator -> llm_call(sections) -> synthesizer -> END")
        assert "orchestrator -> llm_call(sections)" in result
        assert "llm_call -> synthesizer" in result
        assert "synthesizer -> END" in result


class TestConditionalEndings:
    def test_ternary_at_end(self):
        result = expand_chains("a -> b -> cond ? x : y")
        assert "a -> b" in result
        assert "b -> cond ? x : y" in result

    def test_switch_at_end(self):
        result = expand_chains("a -> b -> route(x, y, z)")
        assert "a -> b" in result
        assert "b -> route(x, y, z)" in result


class TestPassthrough:
    def test_comment_unchanged(self):
        result = expand_chains("# this is a comment")
        assert result.strip() == "# this is a comment"

    def test_blank_line_unchanged(self):
        result = expand_chains("")
        assert result == ""

    def test_indented_line_unchanged(self):
        result = expand_chains("  is_done => END")
        assert result.strip() == "is_done => END"


class TestMultiLine:
    def test_multi_line_spec(self):
        spec = "# comment\nSTART:State -> a -> b\nb -> cond ? x : y\nx -> END"
        result = expand_chains(spec)
        assert "# comment" in result
        assert "START:State -> a" in result
        assert "a -> b" in result
        assert "b -> cond ? x : y" in result
        assert "x -> END" in result


class TestIntegrationWithPipeline:
    """Test that expand_chains works correctly through the full pipeline."""

    def test_rag_chain_through_pipeline(self):
        spec = "START:AgentState -> get_docs -> format_docs -> format_prompt -> generate -> END"
        expanded = expand_chains(spec)
        preprocessed = preprocess_start_syntax(expanded, "rag")
        graph, start_node = parse_graph_spec(preprocessed)
        assert "get_docs" in graph
        assert "format_docs" in graph
        assert "format_prompt" in graph
        assert "generate" in graph

    def test_worker_chain_through_pipeline(self):
        spec = "START:State -> orchestrator\norchestrator -> llm_call(sections) -> synthesizer -> END"
        expanded = expand_chains(spec)
        preprocessed = preprocess_start_syntax(expanded, "test")
        graph, start_node = parse_graph_spec(preprocessed)
        assert "orchestrator" in graph
        assert "llm_call" in graph
        assert "synthesizer" in graph

    def test_parallelization_through_pipeline(self):
        spec = "START:State -> call_llm_1, call_llm_2, call_llm_3 -> aggregator -> END"
        expanded = expand_chains(spec)
        preprocessed = preprocess_start_syntax(expanded, "test")
        graph, start_node = parse_graph_spec(preprocessed)
        assert "aggregator" in graph
        # Check fan-in edges exist
        for node in ["call_llm_1", "call_llm_2", "call_llm_3"]:
            assert node in graph
            edges = graph[node]["edges"]
            assert any(e["destination"] == "aggregator" for e in edges)
