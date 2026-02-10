# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**langgraph-codegen** is a Python library that generates LangGraph Python code from a simple Domain Specific Language (DSL). It takes a DSL input file and generates three outputs: **state class**, **node function stubs**, and **graph builder** (conditions, workers, assignments, and graph wiring).

The project enables rapid prototyping of LangGraph architectures by writing simple specifications like:
```
START(State) => plan_step
plan_step => execute_step
execute_step => replan_step
replan_step
  is_done => END
  => execute_step
```

## Development Commands

### Installation & Setup
```bash
# Install in development mode
pip install -e .

# Uninstall and reinstall (for testing changes)
pip uninstall langgraph-codegen && pip install -e .
```

### Testing
```bash
# Run tests with pytest
pytest

# Run specific test file
pytest tests/test_gen_graph.py
pytest tests/test_graph_validation.py
```

### CLI Usage
```bash
# Generate all 3 files (state, nodes, graph builder)
lgcodegen my_workflow.graph

# Generate specific components
lgcodegen my_workflow.graph --state      # State class only
lgcodegen my_workflow.graph --nodes      # Node functions only
lgcodegen my_workflow.graph --graph      # Graph builder only

# Print to stdout instead of writing files
lgcodegen my_workflow.graph --stdout
lgcodegen my_workflow.graph --state --stdout
```

**Output files** (for input `my_workflow.graph`):
- `my_workflow_state.py` — state class (TypedDict)
- `my_workflow_nodes.py` — node function stubs
- `my_workflow_graph.py` — conditions + workers + assignments + graph builder

### Development Scripts
```bash
# Local development install (./runlocal)
./runlocal

# Test with example generation (./testit)
./testit

# Release script (./runit) - updates versions and publishes
./runit
```

## Code Architecture

### Core Components

**langgraph_codegen/lgcodegen.py** — CLI entry point. Reads a DSL file, calls generators, writes output files or prints to stdout. ~50 lines.

**langgraph_codegen/gen_graph.py** — Core code generation engine containing:
- DSL parsing: `parse_graph_spec`, `transform_graph_spec`
- Code generators: `gen_graph`, `gen_nodes`, `gen_conditions`, `gen_state`, `gen_worker_functions`, `gen_assignment_functions`
- Graph validation: `validate_graph`

**langgraph_codegen/graph.py** — Graph data structure and validation logic.

### DSL Syntax Processing

The DSL supports several patterns that get transformed during parsing:

1. **Basic Flow**: `node1 => node2` (unconditional edge)
2. **Conditional Flow**:
   ```
   node1
     condition1 => node2
     condition2 => node3
     => END
   ```
3. **Parallel Execution**: `node1 -> func(State.field)` (creates assignment + worker functions)
4. **Multiple Routing**: `node1 -> func(param1, param2, param3)` (creates conditional edge functions)

### Code Generation Pipeline

1. **Transform**: `transform_graph_spec()` normalizes DSL syntax
2. **Parse**: `parse_graph_spec()` creates internal graph representation
3. **Generate**: Individual generators create components:
   - State classes with TypedDict and Annotated fields
   - Mock node functions with progress tracking
   - Conditional edge functions with routing logic
   - Worker functions for parallel processing
   - Assignment functions for work distribution
   - Graph builder with node wiring and compilation

### File Organization

- **src/langgraph_codegen/** — Main package code
- **src/langgraph_codegen/data/examples/** — Example graph specifications (.graph and .txt files)
- **tests/** — Test files and evaluation examples

## Common Development Tasks

### Adding New Graph Examples
1. Create `.graph` or `.txt` file in `src/langgraph_codegen/data/examples/`
2. Use standard DSL syntax with descriptive comments
3. Test generation with `lgcodegen path/to/example.graph --stdout`

### Extending Code Generation
1. Add new generator functions to `gen_graph.py`
2. Follow existing patterns for function signatures and return types
3. Update CLI in `lgcodegen.py` if needed
4. Add corresponding test cases

### Testing Changes
1. Run existing tests: `pytest`
2. Test with example graphs: `lgcodegen src/langgraph_codegen/data/examples/simple.graph --stdout`
3. Verify generated code compiles: `python -c "compile(open('file.py').read(), 'file.py', 'exec')"`
