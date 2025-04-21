
**Prompt: Deriving State Class and Fields from Graph Specification**

Your task is to analyze the provided graph specification snippet and determine:

1.  **The name of the State Class.**
2.  **The names and implied types of the fields required within that State Class**, based on the nodes, workers, and routing functions used.

Your task is to *write the specification for the State class* in markdown.
This includes:
1. The name of the State class
2. For each field:
   - the name of the field
   - the data type of the field
   - the (optional) annotation of the field
   - the description of the field

Use the following rules and examples to guide your analysis:

**Rule 1: State Class Name**

*   **How to find it:** The State Class name is the **first word of the first non-comment line**.
*   **Example Spec:**
</EXAMPLE_SPEC>
    # Graph for processing customer orders
    OrderState -> validate_order
    validate_order -> process_payment
</EXAMPLE_SPEC>
*   **Derived State Class Name:** `OrderState`

**Rule 2: Distinguishing Worker Nodes vs. Routing Functions**

*   Both use parentheses `(...)` on the *right side* of the `->` arrow.
*   **Worker Node Syntax:** The content inside `(...)` references a specific **State field** (e.g., `MyState.items`).
    *   *Example:* `fetch_items -> process_item_worker(OrderState.item_list)`
*   **Routing Function Syntax:** The content inside `(...)` lists **potential destination node names** or `END`.
    *   *Example:* `check_payment -> handle_result(order_confirmed, order_failed, END)`

**Rule 3: Identifying State Fields**

Analyze each line involving nodes, workers, or routing functions to infer necessary state fields:

*   **a) Fields for Worker Nodes:**
    *   **Input List Field:** The `worker_node(State.field_name)` syntax *explicitly* tells you that `field_name` must be a list field in the State Class.
        *   *Example Spec:* `prepare_tasks -> task_worker(ProjectState.pending_tasks)`
        *   *Implied State Field:* `pending_tasks: list[...]` (The type of items in the list needs context, but it *is* a list).
    *   **Processed Output Field:** A worker node *implicitly* requires a field to store results, conventionally named `processed_<input_field_name>`. This field *must* have the type `Annotated[list[<item_type>], operator.add]`.
        *   *Example Spec (same as above):* `prepare_tasks -> task_worker(ProjectState.pending_tasks)`
        *   *Implied State Field:* `processed_pending_tasks: Annotated[list[...], operator.add]`

*   **b) Fields for Routing Functions:**
    *   A routing function `router_func(dest1, dest2)` takes the *entire State* object to make its decision. The fields it *reads* depend on its internal logic. Look for comments or infer from the function's name what state information it likely needs.
        *   *Example Spec:* `verify_user -> check_auth(user_dashboard, login_page) # Checks state.is_authenticated`
        *   *Implied State Field:* `is_authenticated: bool` (or similar, based on the comment/logic).

*   **c) Fields for Regular Node Functions:**
    *   A standard node function (e.g., `node1 -> node2`) also receives the State. Infer the fields it reads or writes based on the function's name, purpose, or associated comments.
        *   *Example Spec:*
        <EXAMPLE_SPEC>
            # state.raw_text contains the input document
            load_document -> chunk_text
            # chunk_text splits state.raw_text into state.text_chunks
            chunk_text -> process_chunks
        </EXAMPLE_SPEC>
        *   *Implied State Fields:* `raw_text: str`, `text_chunks: list[str]` (Types inferred from context).

Below you are provided with a graph specification.  

Your task is to analyze the provided graph specification that follows and determine:

1.  **The name of the State Class.**
2.  **The names and implied types of the fields required within that State Class**, based on the nodes, workers, and routing functions used.

Your task is to *write the specification for the State class* in markdown.
This includes:
1. The name of the State class
2. For each field:
   - the name of the field
   - the data type of the field
   - the (optional) annotation of the field
   - the description of the field

Write the result to file 'state-spec.md'

Here is the graph specification:
<GRAPH_SPEC>

{graph_spec}

</GRAPH_SPEC>
