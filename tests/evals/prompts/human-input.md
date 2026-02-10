To get Human Input, use the 'human_input' library.   Here are some examples:

## Basic Text Input

```python
from human_input import human_text_input

name = human_text_input("What's your name?")
print(f"Hello, {name}!")
```

## Confirmation (Yes/No)

```python
from human_input import human_yesno_input

confirm = human_yesno_input("Do you want to continue?")
if confirm:
    print("Continuing...")
else:
    print("Operation cancelled.")
```


