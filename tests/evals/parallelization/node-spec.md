# node-spec.md
_Generated using gpt-4.1_

# Node Functions

## get_topic
```
BEHAVIOR: The initial node, responsible for acquiring the topic for story, joke, and poem generation.
USER_PROMPT: "Please provide a topic to generate a story, joke, and poem about."
GENERATION_PROMPT: None (user provides the input, not the model).
READS: (none)
WRITES: topic
```

## story
```
BEHAVIOR: Generates a story based on the given topic, as part of parallel content creation.
USER_PROMPT: None
GENERATION_PROMPT: "Write a short story about the provided topic."
READS: topic
WRITES: story_text
```

## joke
```
BEHAVIOR: Generates a joke based on the given topic, as part of parallel content creation.
USER_PROMPT: None
GENERATION_PROMPT: "Write a joke about the provided topic."
READS: topic
WRITES: joke_text
```

## poem
```
BEHAVIOR: Generates a poem based on the given topic, as part of parallel content creation.
USER_PROMPT: None
GENERATION_PROMPT: "Write a poem about the provided topic."
READS: topic
WRITES: poem_text
```

## aggregator
```
BEHAVIOR: Combines the story, joke, and poem results into a single aggregated result; finalizes the workflow.
USER_PROMPT: None
GENERATION_PROMPT: "Combine the generated story, joke, and poem into a single result."
READS: story_text, joke_text, poem_text
WRITES: aggregated_result
```

# Routing Functions

_This graph contains no explicit routing functions (no conditional or branching routers were specified)._