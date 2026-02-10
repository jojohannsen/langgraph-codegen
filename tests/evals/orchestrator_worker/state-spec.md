# State Class Design Specification

## State Class Name

`State`

---

## State Fields

### 1. topic
- **Type:** `str`
- **Description:**
    - The report topic provided upon invocation. Required for generating section titles and structuring the report content.

---

### 2. sections
- **Type:** `list[str]`
- **Description:**
    - A list of up to 4 section titles generated based on the report topic. Used as input to the worker node to generate content for each section.

---

### 3. processed_sections
- **Type:** `Annotated[list[str], operator.add]`
- **Description:**
    - The generated content for each section, one item per section. Populated by the `worker` node as it processes each item in `sections`.