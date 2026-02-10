# File generated using gpt-4.1

# Node Function Specifications

## orchestrator
```
BEHAVIOR: Generate a list of report sections based on the input topic. Generates no more than 4 sections, which are stored in a list in state.
USER_PROMPT: (Prompt user for a report topic if not already supplied.)
GENERATION_PROMPT: Generate up to 4 descriptive section titles suitable for a report on the provided topic.
READS: topic
WRITES: sections
```

## worker (worker on State.sections)
```
BEHAVIOR: Generate content for each report section. Operates as a worker node, running once for each entry in the State.sections list and generating the content for that section.
USER_PROMPT: (None; internal processing per section.)
GENERATION_PROMPT: For the given section title, generate the section's content for the report on the specified topic.
READS: topic (to inform section content), section (individual string from sections list)
WRITES: processed_sections
```

## synthesizer
```
BEHAVIOR: Generate a synthesized response based on the results of all the workers, e.g., combine the individual section contents into a final report or summary output.
USER_PROMPT: (None.)
GENERATION_PROMPT: Combine the report section contents in processed_sections into a cohesive report or summary output.
READS: processed_sections
WRITES: (Final output; may update or write another field if required by an implementation, but not specified in current state definition)
```

# Routing Functions

_No custom routing functions are present in this graph specification._

- All transitions are direct or use worker-node constructs; there are no dynamic/conditional branches.