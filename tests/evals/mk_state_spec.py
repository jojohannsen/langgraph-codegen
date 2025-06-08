from pathlib import Path
import sys
from colorama import init, Fore, Style
from mk_utils import read_file_and_get_subdir, mk_agent, get_single_prompt, parse_graph, validate_graph, OpenRouterAgent, prepare_working_folder, get_tools
from gen_state_spec import *

if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_state_spec.py graph_spec_file")
        sys.exit(1)

    file_path = sys.argv[1]
    graph_name, graph_spec = read_file_and_get_subdir(file_path)
    
    # Check if state-spec.md already exists and is not empty
    state_spec_file = f"{graph_name}/state-spec.md"
    if Path(state_spec_file).exists() and Path(state_spec_file).stat().st_size > 0:
        print(f"{Fore.RED}state-spec.md exists and is not empty{Style.RESET_ALL}")
        user_input = input(f"{Fore.CYAN}Do you want to delete it? (y/n){Style.RESET_ALL}")
        if user_input == "y":
            Path(state_spec_file).unlink()
        else:
            print(f"{Fore.GREEN}state-spec.md already exists, skipping{Style.RESET_ALL}")
            exit(0)
    
    # Use the generate_state_spec function
    try:
        content = generate_state_spec(graph_name, graph_spec)
        print(f"{Fore.GREEN}State spec generated successfully{Style.RESET_ALL}")
        
        # Verify that the state_spec.md file exists and is not empty
        if not Path(state_spec_file).exists():
            print(f"{Fore.RED}State spec file does not exist{Style.RESET_ALL}")
            sys.exit(1)
        if Path(state_spec_file).stat().st_size == 0:
            print(f"{Fore.RED}State spec file is empty{Style.RESET_ALL}")
            sys.exit(1)
            
    except Exception as e:
        print(f"{Fore.RED}Error generating state spec: {e}{Style.RESET_ALL}")
        sys.exit(1)



