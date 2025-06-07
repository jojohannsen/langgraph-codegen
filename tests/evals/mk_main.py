import sys
from colorama import init, Fore, Style
from pathlib import Path
from mk_utils import read_file_and_get_subdir, FileOverwriteManager
from gen_main import *
import questionary

if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_main_code.py graph_spec_file")
        sys.exit(1)

    file_path = sys.argv[1]
    graph_name, graph_spec = read_file_and_get_subdir(file_path)
    
    # Create the working directory if it doesn't exist
    Path(graph_name).mkdir(parents=True, exist_ok=True)
    print(f"{Fore.GREEN}Graph folder: {Fore.BLUE}{graph_name}{Style.RESET_ALL}")
    
    # Check if main.py already exists and handle overwrite
    main_code_file = Path(graph_name) / "main.py"
    with FileOverwriteManager(main_code_file, file_description="main.py") as manager:
        if not manager.should_continue:
            sys.exit(1)
        
        # Use the generate_main function
        try:
            content = generate_main(graph_name, graph_spec)
            print(f"{Fore.GREEN}Main code generated successfully{Style.RESET_ALL}")
            print(f"{Fore.GREEN}Main code: {Fore.BLUE}{main_code_file}{Style.RESET_ALL}")
            
        except Exception as e:
            print(f"{Fore.RED}Error generating main code: {e}{Style.RESET_ALL}")
            sys.exit(1)

