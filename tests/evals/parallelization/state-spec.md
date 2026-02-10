# State Class Specification

## State Class Name

`State`

---

## State Fields

### 1. `topic`
- **Type:** `str`
- **Description:** The topic provided by the user or system for which the story, joke, and poem will be generated.

### 2. `story_text`
- **Type:** `str`
- **Description:** The text output of the story generated based on the topic.

### 3. `joke_text`
- **Type:** `str`
- **Description:** The text of the joke generated based on the topic.

### 4. `poem_text`
- **Type:** `str`
- **Description:** The text of the poem generated based on the topic.

### 5. `aggregated_result`
- **Type:** `str`
- **Description:** The final, combined result from the aggregator node containing the story, joke, and poem.

---

## Field Summary Table

| Field Name          | Type   | Description                                        |
|---------------------|--------|----------------------------------------------------|
| topic               | str    | Topic for story, joke, and poem generation         |
| story_text          | str    | The generated story text                           |
| joke_text           | str    | The generated joke text                            |
| poem_text           | str    | The generated poem text                            |
| aggregated_result   | str    | Aggregated output combining all generated results  |