# node-spec.md

*This file was generated using gpt-4.1*

---

## Node Functions

### get_joke_topic
```
BEHAVIOR: first we ask for topic
USER_PROMPT: Please provide a topic for a joke (e.g., cats, computers, physics).
GENERATION_PROMPT: None (waits for user input)
READS: None
WRITES: topic
```

### tell_joke
```
BEHAVIOR: then we generate a joke, and display it
USER_PROMPT: None (the system will generate a joke and present it)
GENERATION_PROMPT: Generate a joke based on the topic: {topic}
READS: topic
WRITES: joke
```

### ask_for_another
```
BEHAVIOR: then we ask user if they want another joke, we route based on that result
USER_PROMPT: Would you like to hear another joke? (yes/no)
GENERATION_PROMPT: None (waits for user input)
READS: None (may also want to use latest joke for context)
WRITES: wants_another
```


## Routing Functions

### tell_another
```
BEHAVIOR: determines, based on user's input (wants_another), whether to start another joke or end the conversation
READS: wants_another
ROUTES_TO: get_joke_topic, END
```