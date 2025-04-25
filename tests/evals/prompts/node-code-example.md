#### Node Functions

Node functions always take the same parameters:
```python
from langchain_core.runnables.config import RunnableConfig

def node_1(state: MyState, *, config:Optional[RunnableConfig] = None):
    mk_node_code.py
    read_field = state.read_field
    if read_field:
        write_field = "address"
        write_value = "123 Athens Street"
        # always return the fields that should be updated in State
        return { write_field: write_value }
    else:
        return {} # must return something
```

Sometimes the Node Function is supposed to GENERATE something.  In cases like these, the Node specification will have a description of the GENERATE PROMPT, and it often uses values in state as part of the prompt.

#### Using LLM within a Node Function

When we use an LLM within a Node Function, the actual LLM we create depends on the configuration.  
We use the model returned by the "node_chat_function" that we import from lgcodegen_llm.


```python
from lgcodegen_llm import node_chat_model

def generate_joke(state: State):
    """First LLM call to generate initial joke"""
    # then we get the prompt to use based on the Node Specification
    generate_joke_prompt = f"Write a short joke about {state['topic']}"
    # First we create the LLM, this function takes no parameters
    llm = node_chat_model()
    # Then we invoke the LLM with our prompt, result in msg.content
    msg = llm.invoke(generate_joke_prompt)
    # in this example, we are updating the "joke" field of State
    return {"joke": msg.content}
```
