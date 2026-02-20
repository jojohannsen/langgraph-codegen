try:
    from langgraph_codegen.gen_graph import (
        parse_state_section, type_to_reducer, type_to_default,
        gen_state_class, gen_state, mock_state, parse_graph_spec,
        find_worker_functions, DEFAULT_STATE_FIELDS,
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from langgraph_codegen.gen_graph import (
        parse_state_section, type_to_reducer, type_to_default,
        gen_state_class, gen_state, mock_state, parse_graph_spec,
        find_worker_functions, DEFAULT_STATE_FIELDS,
    )


# --- Parsing tests ---

def test_parse_no_state_section():
    spec = "START(MyState) => plan_step\nplan_step => END\n"
    class_name, fields, remaining = parse_state_section(spec)
    assert class_name is None
    assert fields == []
    assert remaining == spec


def test_parse_state_section_basic():
    spec = """STATE: PlanExecute
nodes_visited: list[str]
counter: int

START => plan_step
plan_step => END
"""
    class_name, fields, remaining = parse_state_section(spec)
    assert class_name == "PlanExecute"
    assert fields == [("nodes_visited", "list[str]"), ("counter", "int")]
    assert "STATE:" not in remaining
    assert "START => plan_step" in remaining


def test_parse_state_section_comments():
    spec = """STATE: MyState
# this is a comment
name: str
# another comment
age: int

START => step1
"""
    class_name, fields, remaining = parse_state_section(spec)
    assert class_name == "MyState"
    assert fields == [("name", "str"), ("age", "int")]


def test_parse_state_section_stops_at_blank_line():
    spec = """STATE: MyState
name: str
count: int

START => step1
step1 => END
"""
    class_name, fields, remaining = parse_state_section(spec)
    assert class_name == "MyState"
    assert len(fields) == 2
    assert "START => step1" in remaining


def test_parse_state_section_stops_at_start():
    spec = """STATE: MyState
name: str
count: int
START => step1
step1 => END
"""
    class_name, fields, remaining = parse_state_section(spec)
    assert class_name == "MyState"
    assert fields == [("name", "str"), ("count", "int")]
    assert "START => step1" in remaining


def test_parse_various_types():
    spec = """STATE: BigState
names: list[str]
counter: int
title: str
metadata: dict
active: bool
score: float
steps: list[dict]

START => step1
"""
    class_name, fields, remaining = parse_state_section(spec)
    assert class_name == "BigState"
    assert len(fields) == 7
    assert fields[0] == ("names", "list[str]")
    assert fields[1] == ("counter", "int")
    assert fields[2] == ("title", "str")
    assert fields[3] == ("metadata", "dict")
    assert fields[4] == ("active", "bool")
    assert fields[5] == ("score", "float")
    assert fields[6] == ("steps", "list[dict]")


# --- Type mapping tests ---

def test_type_to_reducer():
    assert type_to_reducer("list[str]") == "add_to_list"
    assert type_to_reducer("list[dict]") == "add_to_list"
    assert type_to_reducer("list") == "add_to_list"
    assert type_to_reducer("int") == "add_int"
    assert type_to_reducer("str") is None
    assert type_to_reducer("dict") is None
    assert type_to_reducer("bool") is None
    assert type_to_reducer("float") is None
    assert type_to_reducer("SomeCustomType") is None


def test_type_to_default():
    assert type_to_default("list[str]") == "[]"
    assert type_to_default("list") == "[]"
    assert type_to_default("int") == "0"
    assert type_to_default("str") == "''"
    assert type_to_default("dict") == "{}"
    assert type_to_default("bool") == "False"
    assert type_to_default("float") == "0.0"
    assert type_to_default("SomeCustomType") == "None"


# --- Code generation tests ---

def test_gen_state_class_with_reducers():
    fields = [("visited", "list[str]"), ("count", "int")]
    code = gen_state_class("MyState", fields)
    assert "Annotated[list[str], add_to_list]" in code
    assert "Annotated[int, add_int]" in code
    assert "def add_to_list(" in code
    assert "def add_int(" in code


def test_gen_state_class_plain_fields():
    fields = [("name", "str"), ("metadata", "dict"), ("active", "bool")]
    code = gen_state_class("MyState", fields)
    assert "name: str" in code
    assert "metadata: dict" in code
    assert "active: bool" in code
    # No Annotated for plain types
    assert "Annotated[str" not in code
    assert "Annotated[dict" not in code
    assert "Annotated[bool" not in code


def test_gen_state_class_initialize_state():
    fields = [("names", "list[str]"), ("count", "int"), ("title", "str"),
              ("data", "dict"), ("flag", "bool"), ("score", "float")]
    code = gen_state_class("TestState", fields)
    assert "def initialize_state():" in code
    assert "'names': []" in code
    assert "'count': 0" in code
    assert "'title': ''" in code
    assert "'data': {}" in code
    assert "'flag': False" in code
    assert "'score': 0.0" in code


def test_gen_state_class_default_comments():
    fields = [("nodes_visited", "list[str]"), ("counter", "int")]
    code = gen_state_class("MyState", fields, is_default=True)
    assert "# default field" in code


def test_only_needed_reducers_emitted():
    # Only list fields — should not emit add_int
    fields = [("items", "list[str]"), ("name", "str")]
    code = gen_state_class("MyState", fields)
    assert "def add_to_list(" in code
    assert "def add_int(" not in code

    # Only int fields — should not emit add_to_list
    fields2 = [("count", "int"), ("name", "str")]
    code2 = gen_state_class("MyState", fields2)
    assert "def add_to_list(" not in code2
    assert "def add_int(" in code2

    # No reducer fields — no reducer functions at all
    fields3 = [("name", "str"), ("active", "bool")]
    code3 = gen_state_class("MyState", fields3)
    assert "def add_to_list(" not in code3
    assert "def add_int(" not in code3


# --- Integration tests ---

def test_gen_state_with_explicit_fields():
    spec = "START(CustomState) => step1\nstep1 => END\n"
    fields = [("plan", "str"), ("steps", "list[dict]"), ("counter", "int")]
    code = gen_state(spec, state_fields=fields)
    assert "class CustomState(TypedDict):" in code
    assert "plan: str" in code
    assert "Annotated[list[dict], add_to_list]" in code
    assert "Annotated[int, add_int]" in code
    # Should NOT have default field comments
    assert "# default field" not in code


def test_gen_state_default_backward_compat():
    spec = "START(MyState) => step1\nstep1 => END\n"
    code = gen_state(spec)
    assert "class MyState(TypedDict):" in code
    assert "nodes_visited" in code
    assert "counter" in code
    assert "add_to_list" in code
    assert "add_int" in code
    assert "def initialize_state():" in code


def test_worker_fields_added_when_missing():
    spec = """START(OrcState) => orchestrator
orchestrator -> llm_call(OrcState.sections)
llm_call => synthesize
synthesize => END
"""
    fields = [("plan", "str"), ("counter", "int")]
    code = gen_state(spec, state_fields=fields)
    assert "sections:" in code
    assert "Annotated[list, add_to_list]" in code
    assert "plan: str" in code
    assert "Annotated[int, add_int]" in code


def test_worker_fields_not_duplicated():
    spec = """START(OrcState) => orchestrator
orchestrator -> llm_call(OrcState.sections)
llm_call => synthesize
synthesize => END
"""
    fields = [("sections", "list[str]"), ("counter", "int")]
    code = gen_state(spec, state_fields=fields)
    # sections should appear exactly once in the class body
    class_section = code[code.index("class "):]
    assert class_section.count("sections:") == 1


def test_gen_state_with_state_class_name_override():
    spec = "START(WrongName) => step1\nstep1 => END\n"
    code = gen_state(spec, state_class_name="CorrectName")
    assert "class CorrectName(TypedDict):" in code
    assert "WrongName" not in code


# --- Full pipeline tests ---

def test_lg_with_state_section():
    """End-to-end: STATE section in .lg content produces correct TypedDict."""
    lg_content = """STATE: PlanExecute
plan: str
steps: list[dict]
counter: int

START => plan_step
plan_step => execute_step
execute_step => END
"""
    class_name, fields, graph_spec = parse_state_section(lg_content)
    assert class_name == "PlanExecute"
    assert len(fields) == 3

    # Simulate what lgcodegen.py does: inject class name into START
    import re
    graph_spec = graph_spec.replace("START =>", f"START({class_name}) =>")

    code = gen_state(graph_spec, state_fields=fields, state_class_name=class_name)
    assert "class PlanExecute(TypedDict):" in code
    assert "plan: str" in code
    assert "Annotated[list[dict], add_to_list]" in code
    assert "Annotated[int, add_int]" in code
    assert "'plan': ''" in code
    assert "'steps': []" in code
    assert "'counter': 0" in code


def test_lg_without_state_section():
    """End-to-end: no STATE section uses defaults (backward compatible)."""
    lg_content = """START(SimpleState) => step1
step1 => step2
step2 => END
"""
    class_name, fields, graph_spec = parse_state_section(lg_content)
    assert class_name is None
    assert fields == []
    assert graph_spec == lg_content

    code = gen_state(graph_spec)
    assert "class SimpleState(TypedDict):" in code
    assert "nodes_visited" in code
    assert "counter" in code


def test_state_section_stops_at_arrow():
    """STATE section ends when an arrow line is encountered."""
    spec = """STATE: MyState
name: str
count: int
step1 => step2
step2 => END
"""
    class_name, fields, remaining = parse_state_section(spec)
    assert class_name == "MyState"
    assert fields == [("name", "str"), ("count", "int")]
    assert "step1 => step2" in remaining


def test_mock_state_backward_compat():
    """mock_state still works and produces gen_state_class output."""
    code = mock_state("TestState")
    assert "class TestState(TypedDict):" in code
    assert "nodes_visited" in code
    assert "counter" in code
    assert "def initialize_state():" in code


def test_mock_state_with_extra_fields_no_duplication():
    """mock_state extra_fields don't duplicate defaults."""
    code = mock_state("TestState", extra_fields=[("sections", "list")])
    assert "sections: " in code
    # defaults still present
    assert "nodes_visited" in code
    assert "counter" in code
