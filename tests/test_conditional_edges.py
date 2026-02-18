"""Tests for conditional edge syntaxes: switch fn(A, B, C) and boolean ternary fn ? A : B."""

try:
    from langgraph_codegen.gen_graph import (
        gen_graph, gen_conditions, gen_state, gen_nodes,
        gen_worker_functions, gen_assignment_functions,
        parse_graph_spec, transform_graph_spec,
        find_switch_functions, find_worker_functions, find_assignment_functions,
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from langgraph_codegen.gen_graph import (
        gen_graph, gen_conditions, gen_state, gen_nodes,
        gen_worker_functions, gen_assignment_functions,
        parse_graph_spec, transform_graph_spec,
        find_switch_functions, find_worker_functions, find_assignment_functions,
    )


# --- Specs ---

SWITCH_SPEC = """\
START(PlanExecute) => plan_step
plan_step => execute_step
execute_step => replan_step
replan_step -> is_done(END, execute_step)
"""

TERNARY_SPEC = """\
START(PlanExecute) => plan_step
plan_step => execute_step
execute_step => replan_step
replan_step -> is_done ? END : execute_step
"""

MULTI_SWITCH_SPEC = """\
START -> research_node
research_node -> determine_next_node(chart_node, tool_node, END)
chart_node -> needs_research(research_node, tool_node, END)
tool_node -> go_back(research_node, chart_node, END)
"""

INDENTED_SPEC = """\
START(State) => plan_step
plan_step => execute_step
execute_step => replan_step
replan_step
  is_done => END
  => execute_step
"""

WORKER_SPEC = """\
START(State) => orchestrator
orchestrator -> llm_call(State.sections)
llm_call -> synthesizer
synthesizer -> END
"""


# ========== Switch syntax tests ==========

class TestSwitchTransform:
    def test_switch_transform_produces_indented_format(self):
        transformed = transform_graph_spec(SWITCH_SPEC)
        assert "replan_step" in transformed
        assert "  is_done_END => END" in transformed
        assert "  is_done_execute_step => execute_step" in transformed

    def test_switch_transform_has_switch_comment(self):
        transformed = transform_graph_spec(SWITCH_SPEC)
        assert "# SWITCH: is_done(END, execute_step)" in transformed

    def test_switch_transform_no_condition_comments(self):
        transformed = transform_graph_spec(SWITCH_SPEC)
        assert "# CONDITION:" not in transformed

    def test_find_switch_functions(self):
        transformed = transform_graph_spec(SWITCH_SPEC)
        switch_funcs = find_switch_functions(transformed)
        assert len(switch_funcs) == 1
        assert switch_funcs[0] == ("is_done", ["END", "execute_step"])


class TestSwitchGenConditions:
    def test_generates_single_switch_function(self):
        conditions = gen_conditions(SWITCH_SPEC)
        assert "def is_done(state: PlanExecute) -> str:" in conditions

    def test_no_individual_bool_conditions(self):
        conditions = gen_conditions(SWITCH_SPEC)
        assert "def is_done_END" not in conditions
        assert "def is_done_execute_step" not in conditions

    def test_switch_uses_random_choice(self):
        conditions = gen_conditions(SWITCH_SPEC)
        assert "random.choice(['END', 'execute_step'])" in conditions

    def test_switch_prints_condition(self):
        conditions = gen_conditions(SWITCH_SPEC)
        assert "CONDITION: is_done" in conditions


class TestSwitchGenGraph:
    def test_no_routing_wrapper(self):
        graph_code = gen_graph("test_switch", SWITCH_SPEC)
        assert "def after_replan_step" not in graph_code
        assert "def is_done(state" not in graph_code  # not inline in graph code

    def test_switch_used_in_conditional_edges(self):
        graph_code = gen_graph("test_switch", SWITCH_SPEC)
        assert "add_conditional_edges('replan_step', is_done," in graph_code

    def test_normal_edges_still_present(self):
        graph_code = gen_graph("test_switch", SWITCH_SPEC)
        assert "add_edge('plan_step', 'execute_step')" in graph_code
        assert "add_edge('execute_step', 'replan_step')" in graph_code


class TestSwitchMultipleNodes:
    """Test with multiple switch nodes in same graph (multi_agent_collaboration)."""

    def test_find_all_switch_functions(self):
        transformed = transform_graph_spec(MULTI_SWITCH_SPEC)
        switch_funcs = find_switch_functions(transformed)
        names = {sf[0] for sf in switch_funcs}
        assert names == {"determine_next_node", "needs_research", "go_back"}

    def test_no_individual_bools_for_any_switch(self):
        conditions = gen_conditions(MULTI_SWITCH_SPEC)
        assert "def determine_next_node_chart_node" not in conditions
        assert "def needs_research_research_node" not in conditions
        assert "def go_back_research_node" not in conditions

    def test_all_switch_functions_generated(self):
        conditions = gen_conditions(MULTI_SWITCH_SPEC)
        assert "def determine_next_node(state:" in conditions
        assert "def needs_research(state:" in conditions
        assert "def go_back(state:" in conditions
        assert "-> str:" in conditions

    def test_no_routing_wrappers_in_graph(self):
        graph_code = gen_graph("test_multi", MULTI_SWITCH_SPEC)
        assert "def after_" not in graph_code

    def test_switch_functions_used_directly(self):
        graph_code = gen_graph("test_multi", MULTI_SWITCH_SPEC)
        assert "add_conditional_edges('research_node', determine_next_node," in graph_code
        assert "add_conditional_edges('chart_node', needs_research," in graph_code
        assert "add_conditional_edges('tool_node', go_back," in graph_code


# ========== Boolean ternary tests ==========

class TestTernaryTransform:
    def test_ternary_transform_produces_indented_format(self):
        transformed = transform_graph_spec(TERNARY_SPEC)
        assert "replan_step" in transformed
        assert "  is_done => END" in transformed
        assert "  => execute_step" in transformed

    def test_ternary_no_switch_comment(self):
        transformed = transform_graph_spec(TERNARY_SPEC)
        assert "# SWITCH:" not in transformed

    def test_ternary_no_condition_comment(self):
        transformed = transform_graph_spec(TERNARY_SPEC)
        assert "# CONDITION:" not in transformed

    def test_ternary_parse_produces_correct_edges(self):
        graph, _ = parse_graph_spec(TERNARY_SPEC)
        edges = graph["replan_step"]["edges"]
        assert len(edges) == 2
        assert edges[0] == {"condition": "is_done", "destination": "END"}
        assert edges[1] == {"condition": "true_fn", "destination": "execute_step"}


class TestTernaryGenConditions:
    def test_generates_boolean_function(self):
        conditions = gen_conditions(TERNARY_SPEC)
        assert "def is_done(state: PlanExecute) -> bool:" in conditions

    def test_no_switch_function(self):
        conditions = gen_conditions(TERNARY_SPEC)
        assert "-> str:" not in conditions


class TestTernaryGenGraph:
    def test_routing_wrapper_generated(self):
        graph_code = gen_graph("test_ternary", TERNARY_SPEC)
        assert "def after_replan_step(state: PlanExecute):" in graph_code

    def test_wrapper_calls_boolean(self):
        graph_code = gen_graph("test_ternary", TERNARY_SPEC)
        assert "if is_done(state):" in graph_code

    def test_wrapper_used_in_conditional_edges(self):
        graph_code = gen_graph("test_ternary", TERNARY_SPEC)
        assert "add_conditional_edges('replan_step', after_replan_step," in graph_code

    def test_normal_edges_still_present(self):
        graph_code = gen_graph("test_ternary", TERNARY_SPEC)
        assert "add_edge('plan_step', 'execute_step')" in graph_code
        assert "add_edge('execute_step', 'replan_step')" in graph_code


# ========== Regression tests ==========

class TestIndentedConditionsUnchanged:
    """Existing indented syntax should still generate individual bools + routing wrapper."""

    def test_conditions_generated_as_bool(self):
        conditions = gen_conditions(INDENTED_SPEC)
        assert "def is_done(state: State) -> bool:" in conditions

    def test_graph_has_routing_wrapper(self):
        graph_code = gen_graph("test_indented", INDENTED_SPEC)
        assert "def after_replan_step(state: State):" in graph_code
        assert "if is_done(state):" in graph_code

    def test_nodes_all_present(self):
        graph_dict, _ = parse_graph_spec(INDENTED_SPEC)
        nodes_code = gen_nodes(graph_dict)
        assert "def plan_step" in nodes_code
        assert "def execute_step" in nodes_code
        assert "def replan_step" in nodes_code


class TestWorkerPatternUnchanged:
    """Worker pattern should still work correctly."""

    def test_worker_functions_found(self):
        workers = find_worker_functions(WORKER_SPEC)
        assert len(workers) == 1
        assert workers[0] == ("llm_call", "State.sections")

    def test_assignment_functions_found(self):
        transformed = transform_graph_spec(WORKER_SPEC)
        assignments = find_assignment_functions(transformed)
        assert len(assignments) == 1

    def test_graph_uses_list_conditional_edges(self):
        graph_code = gen_graph("test_worker", WORKER_SPEC)
        assert "add_conditional_edges('orchestrator', assign_workers_llm_call, ['llm_call'])" in graph_code

    def test_no_switch_in_worker_spec(self):
        transformed = transform_graph_spec(WORKER_SPEC)
        assert find_switch_functions(transformed) == []
