Here's an example of a Graph State class. 
```python
from typing import Optional, List
from pydantic import BaseModel, Field

class SomeState(BaseModel):
    """State for a workflow."""

    # Input data fields
    doc_path: Optional[str] = Field(default=None, description="Path to the document provided by the human")

    # Content fields
    content: Optional[str] = Field(default=None, description="The main content of the document")
    modified_content: Optional[str] = Field(default=None, description="The content after applying requested modifications")

    # User interaction fields
    mod_request: Optional[str] = Field(default=None, description="The modifications requested by the human")
    user_decision: Optional[str] = Field(default=None, description="User's response for flow control (make more changes, accept changes, end)")

```

