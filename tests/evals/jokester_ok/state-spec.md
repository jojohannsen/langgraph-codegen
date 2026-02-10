# State Class Specification: JokesterState

This document specifies the design of the `JokesterState` class and its required fields, as inferred from the provided graph specification.

## State Class Name
- **JokesterState**

## Fields

### 1. topic
- **Type:** `str`
- **Description:** The topic for the joke, as provided by user input during the `get_joke_topic` step.

### 2. joke
- **Type:** `str`
- **Description:** The joke generated based on the user's topic, created in the `tell_joke` step.

### 3. wants_another
- **Type:** `bool`
- **Description:** Stores the user's response (yes/no) from the `ask_for_another` step, indicating if the bot should tell another joke.


## Field Reference Table
| Field Name    | Type   | Description                                                      |
|---------------|--------|------------------------------------------------------------------|
| topic         | str    | The user-requested topic for the joke.                           |
| joke          | str    | The generated joke text.                                         |
| wants_another | bool   | User's input: whether they want to hear another joke (yes/no).   |