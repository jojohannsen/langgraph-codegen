import os

from langchain import hub
from langchain_community.chat_models import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import Tool
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful assistant"),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
)
model = ChatOpenAI()
# Define a workspace directory for file operations
workspace_dir = "./workspace"
if not os.path.exists(workspace_dir):
    os.makedirs(workspace_dir)

# Create a FileManagementToolkit
file_toolkit = FileManagementToolkit(root_dir=workspace_dir)

# Get all available tools from the toolkit (or you can select specific ones)
file_tools = file_toolkit.get_tools()

agent = create_openai_tools_agent(model, file_tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=file_tools)

result = agent_executor.invoke(
    {
        "input": "Create a text file 'test.txt', and write something nice about me in that file",
        "chat_history": [
            HumanMessage(content="hi! my name is bob"),
            AIMessage(content="Hello Bob! How can I assist you today?"),
            HumanMessage(content="Create a text file 'test.txt' and write a nice thing about me"),
        ],
    }
)
print(result)

import os
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.prompts import ChatPromptTemplate

# Set your OpenRouter API key
os.environ["OPENAI_BASE_URL"] = "https://openrouter.ai/api/v1"

# Define a workspace directory for file operations
workspace_dir = "./workspace"
if not os.path.exists(workspace_dir):
    os.makedirs(workspace_dir)

# Create a FileManagementToolkit
file_toolkit = FileManagementToolkit(root_dir=workspace_dir)

# Get all available tools from the toolkit (or you can select specific ones)
file_tools = file_toolkit.get_tools()

# Create a model through OpenRouter (access to GPT-4o)
model = ChatOpenAI(
    model="gpt-4o",  # Using GPT-4o via OpenRouter
    temperature=0,
)

# Define a system prompt template
system_prompt = """
You are an assistant with file management capabilities.
You can read files, write files, search through files, and perform other file system operations.
Always work within the designated workspace directory for safety.

When writing files:
1. Make sure the content is well-formatted
2. Confirm the operation was successful
3. Provide the path to the file

When reading files:
1. Summarize long content if needed
2. Format code or structured data appropriately

All your file operations will be performed in the workspace directory: {workspace_dir}
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

# Create the agent
agent = create_openai_tools_agent(model, file_tools, prompt)

# Create an agent executor
agent_executor = AgentExecutor(
    agent=agent,
    tools=file_tools,
    verbose=True,
    handle_parsing_errors=True,
)

# Example usage
if __name__ == "__main__":
    response = agent_executor.invoke(
        {"input": "Create a text file called example.txt with a short poem about AI", 
         "workspace_dir": workspace_dir}
    )
    print(response["output"])
    
    response = agent_executor.invoke(
        {"input": "Read the content of example.txt", 
         "workspace_dir": workspace_dir}
    )
    print(response["output"])
