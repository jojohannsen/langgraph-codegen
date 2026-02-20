"""Tests for orchestrator-worker (Send/fan-out) code generation patterns."""

try:
    from langgraph_codegen.gen_graph import (
        gen_graph, gen_state, gen_nodes, gen_conditions,
        gen_worker_functions, gen_assignment_functions,
        parse_graph_spec, find_worker_functions, find_assignment_functions,
        transform_graph_spec,
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from langgraph_codegen.gen_graph import (
        gen_graph, gen_state, gen_nodes, gen_conditions,
        gen_worker_functions, gen_assignment_functions,
        parse_graph_spec, find_worker_functions, find_assignment_functions,
        transform_graph_spec,
    )

ORCHESTRATOR_WORKER_SPEC = """\
START(State) => orchestrator
orchestrator -> llm_call(State.sections)
llm_call -> synthesizer
synthesizer -> END
"""


class TestFindWorkerFunctions:
    def test_finds_worker_pattern(self):
        workers = find_worker_functions(ORCHESTRATOR_WORKER_SPEC)
        assert len(workers) == 1
        assert workers[0] == ("llm_call", "State.sections")

    def test_no_workers_in_regular_spec(self):
        spec = "START(State) => node1\nnode1 => END\n"
        assert find_worker_functions(spec) == []


class TestFindAssignmentFunctions:
    def test_finds_assignment_in_transformed_spec(self):
        transformed = transform_graph_spec(ORCHESTRATOR_WORKER_SPEC)
        assignments = find_assignment_functions(transformed)
        assert len(assignments) == 1
        assert assignments[0] == ("assign_workers_llm_call", "sections", "llm_call")


class TestGenStateWorkerFields:
    def test_includes_worker_field(self):
        state_code = gen_state(ORCHESTRATOR_WORKER_SPEC)
        assert "sections: Annotated[list, add_to_list]" in state_code
        assert "'sections': []" in state_code

    def test_regular_spec_no_extra_fields(self):
        spec = "START(State) => node1\nnode1 => END\n"
        state_code = gen_state(spec)
        assert "sections" not in state_code


class TestGenConditionsSkipsAssignment:
    def test_no_boolean_conditions_for_worker_spec(self):
        conditions = gen_conditions(ORCHESTRATOR_WORKER_SPEC)
        assert conditions == "# Conditional Edge Functions: None"

    def test_regular_conditions_still_generated(self):
        spec = """\
START(State) => node1
node1
  is_done => END
  => node1
"""
        conditions = gen_conditions(spec)
        assert "def is_done" in conditions
        assert "-> bool" in conditions


class TestGenNodesExcludesWorkers:
    def test_excludes_worker_function_nodes(self):
        graph_dict, _ = parse_graph_spec(ORCHESTRATOR_WORKER_SPEC)
        worker_names = {f[0] for f in find_worker_functions(ORCHESTRATOR_WORKER_SPEC)}
        nodes_code = gen_nodes(graph_dict, worker_func_names=worker_names)
        assert "def llm_call" not in nodes_code
        assert "def orchestrator" in nodes_code
        assert "def synthesizer" in nodes_code

    def test_no_exclusion_without_worker_names(self):
        graph_dict, _ = parse_graph_spec(ORCHESTRATOR_WORKER_SPEC)
        nodes_code = gen_nodes(graph_dict)
        # Without worker_func_names, llm_call would be generated
        assert "def llm_call" in nodes_code


class TestGenGraphWorkerPattern:
    def test_uses_list_based_conditional_edges(self):
        graph_code = gen_graph("test_ow", ORCHESTRATOR_WORKER_SPEC)
        assert "add_conditional_edges('orchestrator', assign_workers_llm_call, ['llm_call'])" in graph_code

    def test_no_routing_function_for_worker_node(self):
        graph_code = gen_graph("test_ow", ORCHESTRATOR_WORKER_SPEC)
        # Should NOT contain a def llm_call routing function
        assert "def llm_call(state" not in graph_code

    def test_no_dict_conditional_edges_for_worker_node(self):
        graph_code = gen_graph("test_ow", ORCHESTRATOR_WORKER_SPEC)
        assert "orchestrator_conditional_edges" not in graph_code

    def test_regular_nodes_still_have_normal_edges(self):
        graph_code = gen_graph("test_ow", ORCHESTRATOR_WORKER_SPEC)
        # llm_call -> synthesizer should be a normal edge
        assert "add_edge('llm_call', 'synthesizer')" in graph_code
        # synthesizer -> END should be a normal edge
        assert "add_edge('synthesizer', END)" in graph_code


class TestNonWorkerSpecsUnchanged:
    """Ensure regular (non-worker) specs still generate correctly."""

    SIMPLE_SPEC = """\
START(State) => plan_step
plan_step => execute_step
execute_step => replan_step
replan_step
  is_done => END
  => execute_step
"""

    def test_conditions_generated(self):
        conditions = gen_conditions(self.SIMPLE_SPEC)
        assert "def is_done" in conditions

    def test_graph_has_routing_function(self):
        graph_code = gen_graph("simple", self.SIMPLE_SPEC)
        # replan_step has a conditional edge, so it should have routing
        assert "is_done(state)" in graph_code

    def test_nodes_all_present(self):
        graph_dict, _ = parse_graph_spec(self.SIMPLE_SPEC)
        nodes_code = gen_nodes(graph_dict)
        assert "def plan_step" in nodes_code
        assert "def execute_step" in nodes_code
        assert "def replan_step" in nodes_code

    def test_state_no_extra_fields(self):
        state_code = gen_state(self.SIMPLE_SPEC)
        assert "sections" not in state_code
