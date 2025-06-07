import os
import sys
import questionary

from colorama import init, Fore, Style
from langchain_core.prompts import ChatPromptTemplate
from pathlib import Path
from agno.agent import Agent
from agno.tools.file import FileTools
from agno.models.anthropic import Claude
from agno.models.openai import OpenAIChat
from agno.tools.duckduckgo import DuckDuckGoTools

from mk_utils import read_file_and_get_subdir
from gen_node_code import *

if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_node_code.py graph_spec_file")
        sys.exit(1)

    file_path = sys.argv[1]
    graph_name, graph_spec = read_file_and_get_subdir(file_path)
    
    print(f"{Fore.GREEN}Graph folder: {Fore.BLUE}{graph_name}{Style.RESET_ALL}")
    
    # Use the generate_node_code function
    try:
        content = generate_node_code(graph_name, graph_spec)
        print(f"{Fore.GREEN}Node code generated successfully{Style.RESET_ALL}")
        
        node_code_file = Path(graph_name) / "node_code.py"
        print(f"{Fore.GREEN}Successfully generated: {Fore.BLUE}{node_code_file}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error generating node code: {e}{Style.RESET_ALL}")
        sys.exit(1)