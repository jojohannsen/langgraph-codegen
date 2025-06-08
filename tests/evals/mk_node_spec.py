import sys

from langchain_core.prompts import ChatPromptTemplate
from pathlib import Path
from colorama import init, Fore, Style
from mk_utils import read_file_and_get_subdir
from gen_node_spec import *

if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_node_spec.py graph_spec_file")
        sys.exit(1)

    file_path = sys.argv[1]
    graph_name, graph_spec = read_file_and_get_subdir(file_path)
    
    # Create the working directory if it doesn't exist
    Path(graph_name).mkdir(parents=True, exist_ok=True)
    print(f"{Fore.GREEN}Graph folder: {Fore.BLUE}{graph_name}{Style.RESET_ALL}")
    
    # Check if node-spec.md already exists
    node_spec_file = Path(graph_name) / "node-spec.md"
    if node_spec_file.exists():
        print(f"{Fore.GREEN}Node spec file exists: {Fore.BLUE}{node_spec_file}{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}Node spec file does not exist: {Fore.BLUE}{node_spec_file}{Style.RESET_ALL}")
    
    # Use the generate_node_spec function
    try:
        content = generate_node_spec(graph_name, graph_spec)
        print(f"{Fore.GREEN}Node spec generated successfully{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Successfully generated: {Fore.BLUE}{node_spec_file}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error generating node spec: {e}{Style.RESET_ALL}")
        sys.exit(1)
