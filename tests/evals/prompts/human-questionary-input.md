To get Human Input, use the python 'questionary' library.   Here are some examples:

## Basic Text Input

```python
import questionary

name = questionary.text("What is your name?").ask()
print(f"Hello, {name}!")
```

## Confirmation (Yes/No)

```python
import questionary

confirm = questionary.confirm("Do you want to continue?").ask()
if confirm:
    print("Continuing...")
else:
    print("Operation cancelled.")
```

## Selection from a List

```python
import questionary

color = questionary.select(
    "What's your favorite color?",
    choices=["Red", "Green", "Blue", "Yellow"]
).ask()
print(f"You selected: {color}")
```

## Checkbox Selection (Multiple Choices)

```python
import questionary

selected_fruits = questionary.checkbox(
    "Select fruits you like:",
    choices=["Apple", "Banana", "Orange", "Grapes", "Watermelon"]
).ask()
print(f"You selected: {', '.join(selected_fruits)}")
```

## Auto-complete Input

```python
import questionary

language = questionary.autocomplete(
    "What programming language do you use?",
    choices=["Python", "JavaScript", "Java", "C++", "Ruby", "Go", "Rust"]
).ask()
print(f"You selected: {language}")
```



## Styling Your Prompts

```python
import questionary
from questionary import Style

custom_style = Style([
    ('qmark', '#ff5733 bold'),     # question mark
    ('question', '#5f9ea0 bold'),  # question text
    ('answer', '#00ff00 bold'),    # submitted answer
    ('pointer', '#ff5733 bold'),   # pointer used in select and checkbox prompts
    ('selected', '#00ff00 bold'),  # selected option
    ('separator', '#5f9ea0'),      # separator in lists
])

name = questionary.text(
    "What is your name?",
    style=custom_style
).ask()
print(f"Hello, {name}!")
```

## Input Validation

```python
import questionary
import re

def validate_email(email):
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "Please enter a valid email address"
    return True

email = questionary.text(
    "What is your email?",
    validate=validate_email
).ask()
print(f"Email verified: {email}")
```



