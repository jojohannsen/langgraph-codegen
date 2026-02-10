Today we are going to convert text lines with "invoke" into properly formatted Pydantic field definitions.   Here's an example:
**Input:** `# Graph is invoked with path to graph file`
**Instructions:**

1. Extract the text after "invoked with"
2. Convert it to a valid Python field name using snake_case
3. Infer the appropriate type based on the description
4. Generate a Pydantic field with proper typing and description
**Output format:**

```python
field_name: FieldType = Field(description="Description based on original comment")

```

**Type inference rules:**
* If mentions "path", "file", "filename" → use `Path` from pathlib
* If mentions "url", "uri" → use `str` with URL validation
* If mentions "port", "number" → use `int`
* If mentions "flag", "enable", "disable" → use `bool`
* Otherwise → use `str`
**Example transformation:**
* Input: `# Graph is invoked with path to graph file`
* Field name: `path_to_graph_file`
* Type: `Path`
* Output: `path_to_graph_file: Path = Field(description="Path to graph file used when invoking Graph")`

Convert this comment, output only python code: {invoke_line}

