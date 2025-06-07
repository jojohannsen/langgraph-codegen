
import sys
from colorama import init, Fore, Style
from pathlib import Path
from mk_utils import read_file_and_get_subdir
from gen_graph_code import *

if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_graph_code.py graph_spec_file")
        sys.exit(1)

    file_path = sys.argv[1]
    graph_name, graph_spec = read_file_and_get_subdir(file_path)
    
    # Create the working directory if it doesn't exist
    Path(graph_name).mkdir(parents=True, exist_ok=True)
    print(f"{Fore.GREEN}Graph folder: {Fore.BLUE}{graph_name}{Style.RESET_ALL}")
    
    # Use the generate_graph_code function
    try:
        content = generate_graph_code(graph_name, graph_spec)
        print(f"{Fore.GREEN}Graph code generated successfully{Style.RESET_ALL}")
        
        graph_code_file = Path(graph_name) / "graph_code.py"
        print(f"{Fore.GREEN}Graph code file: {Fore.BLUE}{graph_code_file}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error generating graph code: {e}{Style.RESET_ALL}")
        sys.exit(1)

