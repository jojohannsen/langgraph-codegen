# node-spec.md

*This file was generated using gpt-4.1*

---

## llm_call_generator

```
BEHAVIOR: Generates a joke based on the provided topic (State.topic) and shows it to the human.
USER_PROMPT: None. (Joke is displayed as output, not input requested from user here.)
GENERATION_PROMPT: "Generate a joke about: {topic}."
READS: topic
WRITES: joke
```

## llm_call_evaluator

```
BEHAVIOR: Evaluates whether the current joke (State.joke) is funny, and randomly assigns funny/not funny (True/False) 50% of the time.
USER_PROMPT: None. (No user input requested; decision is automated/random.)
GENERATION_PROMPT: "Is this joke funny? Decide randomly."
READS: joke
WRITES: is_funny
```

---

# Routing Functions

## route_joke

```
BEHAVIOR: Routes execution based on the outcome of joke evaluation. If further jokes should be generated (e.g. user or system requests more), returns 'llm_call_generator', otherwise returns 'END'.
READS: is_funny (and potentially any user feedback, if State is extended)
ROUTES_TO: llm_call_generator, END
```