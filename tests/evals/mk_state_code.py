import os
import sys
from pathlib import Path
from colorama import init, Fore, Style
from mk_utils import read_file_and_get_subdir
from gen_state_code import *


if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_state_spec.py graph_spec_file")
        sys.exit(1)

    file_path = sys.argv[1]
    graph_name, graph_spec = read_file_and_get_subdir(file_path)
    
    # Create the working directory if it doesn't exist
    Path(graph_name).mkdir(parents=True, exist_ok=True)
    print(f"{Fore.GREEN}Graph folder: {Fore.BLUE}{graph_name}{Style.RESET_ALL}")
    
    # Use the generate_state_code function
    try:
        content = generate_state_code(graph_name, graph_spec)
        print(f"{Fore.GREEN}State code generated successfully{Style.RESET_ALL}")
        
        # Verify that the state_code.py file exists
        state_code_file = Path(graph_name) / "state_code.py"
        if not state_code_file.exists():
            print(f"{Fore.RED}Error: state_code.py does not exist{Style.RESET_ALL}")
            sys.exit(1)
            
        print(f"{Fore.GREEN}Successfully generated: {Fore.BLUE}{state_code_file}{Style.RESET_ALL}")
        
    except Exception as e:
        print(f"{Fore.RED}Error generating state code: {e}{Style.RESET_ALL}")
        sys.exit(1)
