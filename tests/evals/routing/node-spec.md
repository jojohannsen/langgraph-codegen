# Generated using gpt-4.1

# Node Specifications

## llm_call_router
```
BEHAVIOR: Uses LLM to route based on the 'input' value in state.
USER_PROMPT: N/A (expects 'input' to be present)
GENERATION_PROMPT: Analyze the input and determine if the user wants a story, joke, or poem.
READS: input
WRITES: (No state fields explicitly written, but output is used for routing)
```

## story
```
BEHAVIOR: Generates a story based on the topic indicated by the input.
USER_PROMPT: N/A (comes from routing)
GENERATION_PROMPT: Generate a complete story based on the provided topic.
READS: input
WRITES: (Assumed to generate output; not specified in State fields)
```

## joke
```
BEHAVIOR: Generates a joke based on the topic indicated by the input.
USER_PROMPT: N/A (comes from routing)
GENERATION_PROMPT: Generate a joke based on the provided topic.
READS: input
WRITES: (Assumed to generate output; not specified in State fields)
```

## poem
```
BEHAVIOR: Generates a poem based on the topic indicated by the input.
USER_PROMPT: N/A (comes from routing)
GENERATION_PROMPT: Generate a poem based on the provided topic.
READS: input
WRITES: (Assumed to generate output; not specified in State fields)
```

# Routing Functions

## route_decision
```
BEHAVIOR: Routes based on the 'input' value in state, determining whether to generate a story, joke, or poem.
READS: input
ROUTES_TO: story, joke, poem
```