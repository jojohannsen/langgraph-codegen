# JokesterState Class Specification

*Generated using claude-sonnet-4-20250514*

## State Class Name
`JokesterState`

## State Fields

### topic
- **Data Type**: `str`
- **Annotation**: None
- **Description**: The topic for the joke as requested from the human user. This field stores the subject matter that the joke should be about.

### joke
- **Data Type**: `str` 
- **Annotation**: None
- **Description**: The generated joke content that will be displayed to the user. This field contains the actual joke text created based on the requested topic.

### wants_another_joke
- **Data Type**: `bool`
- **Annotation**: None
- **Description**: Boolean flag indicating whether the user wants to hear another joke. This field stores the user's response when asked if they want another joke, and is used by the routing function `tell_another` to determine whether to continue with another joke or end the conversation.

## Graph Flow Summary

The JokesterState supports a joke-telling workflow where:
1. A topic is requested from the user and stored in `topic`
2. A joke is generated based on that topic and stored in `joke`  
3. The user is asked if they want another joke, with their response stored in `wants_another_joke`
4. The routing function uses `wants_another_joke` to either restart the process or end the conversation