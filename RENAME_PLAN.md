# Plan: Rename PyPI package from `langgraph-codegen` to `lgcodegen`

## Context

The package is currently published on PyPI as `langgraph-codegen` but the CLI command is already `lgcodegen`. We want the PyPI name to match: `pip install lgcodegen`. The Python import name (`langgraph_codegen`) and source directory (`src/langgraph_codegen/`) will also be renamed to `lgcodegen` for consistency.

## Three areas of work

### 1. PyPI (manual, outside codebase)

- **You cannot rename a package on PyPI.** `langgraph-codegen` will continue to exist as-is.
- Register the new name by publishing `lgcodegen` (the first `v*` tag push after the codebase changes will do this automatically via the existing GitHub Actions workflow).
- **Trusted Publishing config**: In PyPI account settings, add a new "pending publisher" for `lgcodegen` with repository `jojohannsen/langgraph-codegen`, workflow `publish-to-pypi.yml`, environment `pypi`. (This must be done **before** the first publish, since the package doesn't exist on PyPI yet.)
- Optionally: publish a final version of `langgraph-codegen` that's just a wrapper depending on `lgcodegen`, so existing users get a migration path. (Can be done later.)

### 2. GitHub (manual, outside codebase)

- Optionally rename the GitHub repo from `langgraph-codegen` to `lgcodegen`. GitHub auto-redirects the old URL, and the Actions workflow will keep working. This is cosmetic and can be done later.
- **Required**: Ensure the PyPI trusted publisher config (above) matches the repo name at publish time.

### 3. Codebase changes

#### 3a. Rename source directory

```
src/langgraph_codegen/  →  src/lgcodegen/
```

All contents stay the same; only the directory name changes.

#### 3b. `setup.py` — update package name + references

- `name="langgraph-codegen"` → `name="lgcodegen"`
- `package_data` key: `'langgraph_codegen'` → `'lgcodegen'`
- `entry_points`: `'lgcodegen=langgraph_codegen.lgcodegen:main'` → `'lgcodegen=lgcodegen.lgcodegen:main'`
- `url` — update if repo is renamed (optional)

#### 3c. `MANIFEST.in` — update path

```
recursive-include src/langgraph_codegen/data/examples ...
→
recursive-include src/lgcodegen/data/examples ...
```

#### 3d. Internal imports — update `langgraph_codegen` → `lgcodegen`

Files with internal imports to update:

| File | What changes |
|------|-------------|
| `src/lgcodegen/__init__.py` | `from .gen_graph import ...` (no change, relative import) |
| `src/lgcodegen/lgcodegen.py` | `from langgraph_codegen.gen_graph import ...` → `from lgcodegen.gen_graph import ...` |
| `src/lgcodegen/gen_graph.py` | `from langgraph_codegen.graph import Graph` → `from lgcodegen.graph import Graph`; `import langgraph_codegen` → `import lgcodegen` (in `list_examples` and `get_example_path`) |

#### 3e. Test files — update imports

| File | What changes |
|------|-------------|
| `tests/test_gen_graph.py` | `from langgraph_codegen...` → `from lgcodegen...` |
| `tests/test_graph_validation.py` | `from langgraph_codegen...` → `from lgcodegen...` |

#### 3f. Scripts — update paths/names

| File | What changes |
|------|-------------|
| `runlocal` | `pip uninstall langgraph-codegen` → `pip uninstall lgcodegen` |
| `runit` | Update `src/langgraph_codegen/` paths to `src/lgcodegen/` |
| `tests/testit` | Update `EXAMPLES_DIR` path from `langgraph_codegen` to `lgcodegen` |

#### 3g. Documentation

| File | What changes |
|------|-------------|
| `README.md` | Update package name references, `pip install` command, import examples |
| `CLAUDE.md` | Update all `langgraph_codegen` / `langgraph-codegen` references |

#### 3h. `.claude/agents/*.md` — update references

Several agent definition files reference `langgraph_codegen`. Update all of them.

#### 3i. Clean up build artifacts

- Delete `src/langgraph_codegen.egg-info/` (will be regenerated)
- Delete `build/` directory (stale build artifacts)
- Delete `dist/` directory (old distributions)

## Files modified (summary)

- `src/langgraph_codegen/` → rename to `src/lgcodegen/`
- `setup.py`
- `MANIFEST.in`
- `src/lgcodegen/lgcodegen.py` (import)
- `src/lgcodegen/gen_graph.py` (imports)
- `tests/test_gen_graph.py` (imports)
- `tests/test_graph_validation.py` (imports)
- `runlocal`, `runit`, `tests/testit` (paths)
- `README.md`, `CLAUDE.md`
- `.claude/agents/*.md` (references)

## Verification

```bash
# 1. Clean install
pip uninstall langgraph-codegen lgcodegen 2>/dev/null; pip install -e .

# 2. Verify import works
python -c "from lgcodegen import gen_graph, list_examples; print(list_examples())"

# 3. Verify CLI works
lgcodegen --help
lgcodegen simple --stdout | head -20

# 4. Run tests
pytest tests/test_gen_graph.py tests/test_graph_validation.py

# 5. Verify package builds
python setup.py sdist bdist_wheel
# Check that dist/ contains lgcodegen-*.tar.gz
```

## Order of operations

1. **Before any code changes**: Go to PyPI → "Publishing" → add pending publisher for `lgcodegen`
2. Make all codebase changes (section 3 above)
3. Bump version, commit, tag, push — GitHub Actions publishes `lgcodegen` to PyPI
4. (Optional, later) Rename GitHub repo
5. (Optional, later) Publish a final `langgraph-codegen` that depends on `lgcodegen`
