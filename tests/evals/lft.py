import os

from langchain import hub
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_community.agent_toolkits import FileManagementToolkit
from colorama import Fore, Style
class SimpleAgent:
    def __init__(self, agent_executor):
        self.agent_executor = agent_executor
    
    def run(self, input_text: str):
        print(f"{Fore.CYAN}Running agent{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Input: {Fore.BLUE}{input_text}{Style.RESET_ALL}")
        result = self.agent_executor.invoke({
            "input": input_text
        })
        print(f"{Fore.CYAN}Agent result: {Fore.BLUE}{result}{Style.RESET_ALL}")
        return result

def create_file_management_agent(
    provider: str,
    model: str,
    base_url: str,
    api_key: str,
    workspace_dir: str,
    system_prompt: str
) -> SimpleAgent:
    print(f"{Fore.RED}Creating file management agent{Style.RESET_ALL}")
    # Initialize the model
    if provider == "openai":
        llm = ChatOpenAI(model=model)
    elif provider == "openrouter":
        llm = ChatOpenAI(base_url=base_url, api_key=api_key, model=model)
    elif provider == "anthropic":
        llm = ChatAnthropic(model=model)
    else:
        raise ValueError(f"Provider {provider} not supported")
    tool_instructions = "\nUse the WriteFileTool to write files."
    #Create the prompt template
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt + tool_instructions),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ]
    )
    
    # Ensure workspace directory exists
    if not os.path.exists(workspace_dir):
        os.makedirs(workspace_dir)
    
    # Create toolkit and get tools
    file_toolkit = FileManagementToolkit(root_dir=workspace_dir)
    tools = file_toolkit.get_tools()
    # limit this to WriteFileTool
    tools = [tool for tool in tools if tool.name == "write_file"]
    assert len(tools) == 1
    # Create the agent and executor

    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools)
    
    # Return wrapped in SimpleAgent
    return SimpleAgent(agent_executor)


