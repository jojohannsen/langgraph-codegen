"""Tests for cross-file imports in generated code."""

import subprocess
import sys
from pathlib import Path

try:
    from langgraph_codegen.gen_graph import (
        gen_graph, gen_nodes, gen_state, gen_conditions,
        gen_worker_functions, gen_assignment_functions,
        find_worker_functions, parse_graph_spec,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from langgraph_codegen.gen_graph import (
        gen_graph, gen_nodes, gen_state, gen_conditions,
        gen_worker_functions, gen_assignment_functions,
        find_worker_functions, parse_graph_spec,
    )


SIMPLE_SPEC = """\
START(State) => process_input
process_input => validate_data
validate_data => END
"""

CONDITIONAL_SPEC = """\
START(PlanExecute) => plan_step
plan_step => execute_step
execute_step => replan_step
replan_step
  is_done => END
  => execute_step
"""

WORKER_SPEC = """\
START(OrchestratorState) => orchestrator
orchestrator -> llm_call(OrchestratorState.sections)
llm_call => synthesizer
synthesizer => END
"""

MANY_NODES_SPEC = """\
START(BigState) => node_a
node_a => node_b
node_b => node_c
node_c => node_d
node_d => node_e
node_e => node_f
node_f => END
"""


def _build_nodes_file_content(basename, graph_spec):
    """Simulate what lgcodegen writes for _nodes.py."""
    graph_dict, start_node = parse_graph_spec(graph_spec)
    state_class = graph_dict[start_node]["state"]
    code = gen_nodes(graph_dict)
    imports_header = (
        f"from typing import Optional\n"
        f"from langchain_core.runnables.config import RunnableConfig\n"
        f"from {basename}_state import {state_class}\n\n"
    )
    return imports_header + code


def _build_graph_file_content(basename, graph_spec):
    """Simulate what lgcodegen writes for _graph.py."""
    graph_dict, start_node = parse_graph_spec(graph_spec)
    state_class = graph_dict[start_node]["state"]

    node_names = []
    for node_key in graph_dict:
        if node_key == "START":
            continue
        if "," in node_key:
            node_names.extend(n.strip() for n in node_key.split(","))
        else:
            node_names.append(node_key)
    node_names = list(dict.fromkeys(node_names))

    worker_func_names = {f[0] for f in find_worker_functions(graph_spec)}
    import_node_names = [n for n in node_names if n not in worker_func_names]

    if len(import_node_names) > 5:
        node_imports = "(\n    " + ",\n    ".join(import_node_names) + ",\n)"
    else:
        node_imports = ", ".join(import_node_names)

    parts = []
    conditions = gen_conditions(graph_spec)
    if conditions and conditions.strip() != '# Conditional Edge Functions: None':
        parts.append("import random\n\ndef random_one_or_zero():\n    return random.choice([False, True])")
        parts.append(conditions)
    workers = gen_worker_functions(graph_spec)
    if workers and not workers.startswith("# This graph has no"):
        parts.append(workers)
    assignments = gen_assignment_functions(graph_spec)
    if assignments and not assignments.startswith("# This graph has no"):
        parts.append(assignments)
    parts.append(gen_graph(basename, graph_spec))
    code = '\n\n'.join(parts)

    imports_header = (
        f"from {basename}_state import {state_class}\n"
        f"from {basename}_nodes import {node_imports}\n\n"
    )
    return imports_header + code


# --- Unit tests for import content ---

def test_nodes_imports_include_state_class():
    content = _build_nodes_file_content("simple", SIMPLE_SPEC)
    assert "from simple_state import State" in content


def test_nodes_imports_include_optional():
    content = _build_nodes_file_content("simple", SIMPLE_SPEC)
    assert "from typing import Optional" in content


def test_nodes_imports_include_runnable_config():
    content = _build_nodes_file_content("simple", SIMPLE_SPEC)
    assert "from langchain_core.runnables.config import RunnableConfig" in content


def test_graph_imports_include_state_class():
    content = _build_graph_file_content("simple", SIMPLE_SPEC)
    assert "from simple_state import State" in content


def test_graph_imports_include_node_functions():
    content = _build_graph_file_content("simple", SIMPLE_SPEC)
    assert "from simple_nodes import process_input, validate_data" in content


def test_worker_functions_excluded_from_node_imports():
    """Worker functions like llm_call are defined in graph file, not nodes."""
    graph_dict, start_node = parse_graph_spec(WORKER_SPEC)
    node_names = []
    for node_key in graph_dict:
        if node_key == "START":
            continue
        if "," in node_key:
            node_names.extend(n.strip() for n in node_key.split(","))
        else:
            node_names.append(node_key)
    node_names = list(dict.fromkeys(node_names))

    worker_func_names = {f[0] for f in find_worker_functions(WORKER_SPEC)}
    import_node_names = [n for n in node_names if n not in worker_func_names]

    assert "llm_call" not in import_node_names
    assert "orchestrator" in import_node_names
    assert "synthesizer" in import_node_names


def test_graph_imports_exclude_worker_functions():
    content = _build_graph_file_content("worker_test", WORKER_SPEC)
    # The node import line should not contain llm_call
    for line in content.splitlines():
        if line.startswith("from worker_test_nodes import"):
            assert "llm_call" not in line
            assert "orchestrator" in line
            assert "synthesizer" in line
            break
    else:
        raise AssertionError("No 'from worker_test_nodes import' line found")


def test_many_nodes_uses_parenthesized_import():
    """When >5 node names, imports should use multi-line parenthesized form."""
    content = _build_graph_file_content("big", MANY_NODES_SPEC)
    assert "from big_nodes import (\n" in content


def test_stdout_has_no_cross_file_imports(tmp_path):
    """--stdout mode should NOT contain cross-file import lines."""
    spec_file = tmp_path / "simple.lg"
    spec_file.write_text(SIMPLE_SPEC)
    result = subprocess.run(
        [sys.executable, "-m", "langgraph_codegen.lgcodegen", str(spec_file), "--stdout"],
        capture_output=True, text=True,
    )
    output = result.stdout
    assert "from simple_state import" not in output
    assert "from simple_nodes import" not in output


# --- Integration test: generate files, verify they compile ---

def test_generated_files_compile(tmp_path):
    """Generate all 3 files and verify each compiles without syntax errors."""
    basename = "simple"
    graph_spec = SIMPLE_SPEC

    state_code = gen_state(graph_spec)
    nodes_code = _build_nodes_file_content(basename, graph_spec)
    graph_code = _build_graph_file_content(basename, graph_spec)

    (tmp_path / f"{basename}_state.py").write_text(state_code + "\n")
    (tmp_path / f"{basename}_nodes.py").write_text(nodes_code + "\n")
    (tmp_path / f"{basename}_graph.py").write_text(graph_code + "\n")

    for suffix in ("state", "nodes", "graph"):
        filepath = tmp_path / f"{basename}_{suffix}.py"
        code = filepath.read_text()
        compile(code, str(filepath), "exec")


def test_conditional_graph_files_compile(tmp_path):
    """Generate files for a conditional graph and verify compilation."""
    basename = "plan"
    graph_spec = CONDITIONAL_SPEC

    state_code = gen_state(graph_spec)
    nodes_code = _build_nodes_file_content(basename, graph_spec)
    graph_code = _build_graph_file_content(basename, graph_spec)

    (tmp_path / f"{basename}_state.py").write_text(state_code + "\n")
    (tmp_path / f"{basename}_nodes.py").write_text(nodes_code + "\n")
    (tmp_path / f"{basename}_graph.py").write_text(graph_code + "\n")

    for suffix in ("state", "nodes", "graph"):
        filepath = tmp_path / f"{basename}_{suffix}.py"
        code = filepath.read_text()
        compile(code, str(filepath), "exec")


def test_worker_graph_files_compile(tmp_path):
    """Generate files for a worker graph and verify compilation."""
    basename = "worker_test"
    graph_spec = WORKER_SPEC

    state_code = gen_state(graph_spec)
    nodes_code = _build_nodes_file_content(basename, graph_spec)
    graph_code = _build_graph_file_content(basename, graph_spec)

    (tmp_path / f"{basename}_state.py").write_text(state_code + "\n")
    (tmp_path / f"{basename}_nodes.py").write_text(nodes_code + "\n")
    (tmp_path / f"{basename}_graph.py").write_text(graph_code + "\n")

    for suffix in ("state", "nodes", "graph"):
        filepath = tmp_path / f"{basename}_{suffix}.py"
        code = filepath.read_text()
        compile(code, str(filepath), "exec")
