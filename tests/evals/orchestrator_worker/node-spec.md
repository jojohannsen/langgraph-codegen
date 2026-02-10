# node-spec.md
*This file was generated using gpt-4.1*

---

## orchestrator
```
BEHAVIOR: Generate a list of report sections based on the provided report topic. Generate no more than 4 sections, storing them in a list in state.
USER_PROMPT: None (typically, topic is already provided at invocation).
GENERATION_PROMPT: Generate up to 4 section titles appropriate for the report topic stored in `state.topic`.
READS: topic
WRITES: sections
```

## worker
```
BEHAVIOR: Generate content for a report section. Invoked as a worker node for each section listed in `sections`. Each invocation produces content for one section, which is aggregated into `processed_sections`.
USER_PROMPT: None
GENERATION_PROMPT: Generate the content/body for the given section title (element from `sections`), using the main report topic for guidance if needed.
READS: section (element of sections), topic (for context if needed)
WRITES: processed_sections
```

## synthesizer
```
BEHAVIOR: Generate a synthesized response/report based on the results of all worker node outputs (i.e., the generated content of all sections).
USER_PROMPT: None
GENERATION_PROMPT: Compose a final report using the topic and all items in `processed_sections`. Ensure the output is synthesized and cohesive.
READS: topic, processed_sections
WRITES: (Typically, outputs final report to user or finishes the workflow. May write to an output field or just terminate.)
```

---

## Routing Functions
There are **no explicit routing functions** in this graph—the workflow transitions are all direct or via worker expansion. All routing is deterministic.