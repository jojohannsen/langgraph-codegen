#!/usr/bin/env python3

import os
import yaml
import subprocess
import sys
from pathlib import Path

def run_command(command):
    """Run a shell command and print its output"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0

def main():
    # Load config
    with open('default.yaml', 'r') as file:
        config = yaml.safe_load(file)
    
    # Get list of OpenRouter models
    models = config.get('openrouter_models', [])
    
    if not models:
        print("No OpenRouter models found in config file")
        return
    
    # Get list of txt files
    txt_files = list(Path('.').glob('*.txt'))
    
    if not txt_files:
        print("No .txt files found in current directory")
        return
    
    # Print available files
    print("Available .txt files:")
    for i, file in enumerate(txt_files):
        print(f"{i+1}. {file.name}")
    
    # Prompt for file selection
    try:
        selection = int(input("Enter number of file to process: "))
        if selection < 1 or selection > len(txt_files):
            print("Invalid selection. Exiting.")
            return
    except ValueError:
        print("Invalid input. Please enter a number. Exiting.")
        return
    
    # Get selected file
    selected_file = txt_files[selection-1]
    base_name = selected_file.stem  # Get filename without extension
    
    print(f"Selected file: {selected_file}")
    print(f"Base name: {base_name}")
    
    # Set provider to OpenRouter in config
    config['provider'] = "openrouter"
    
    # Process each model
    for model in models:
        model_short_name = model.split('/')[-1].split(':')[0]  # Extract model name without provider
        folder_name = f"{base_name}_{model_short_name}"
        
        print(f"\n{'='*60}")
        print(f"Processing model: {model}")
        print(f"Output folder will be: {folder_name}")
        print(f"{'='*60}\n")
        
        # Create the directory if it doesn't exist
        config_dir = Path(base_name)
        config_dir.mkdir(exist_ok=True)
        
        # Update config with current model
        temp_config = config.copy()
        temp_config['models']['openrouter'] = model
        
        # Write config to the expected location
        config_path = config_dir / f"{base_name}.yaml"
        with open(config_path, 'w') as file:
            yaml.dump(temp_config, file)
        
        # Run evaluation for this model
        success = True
        success &= run_command(f"rm -rf {base_name}")
        success &= run_command(f"mkdir -p {base_name}")  # Recreate the directory
        
        # Write config file again (since we just removed and recreated the directory)
        with open(config_path, 'w') as file:
            yaml.dump(temp_config, file)
            
        success &= run_command(f"python mk_state_spec.py {selected_file}")
        #success &= run_command(f"python mk_state_code.py {selected_file}")
        #success &= run_command(f"python mk_node_spec.py {selected_file}")
        #success &= run_command(f"python mk_node_code.py {selected_file}")
        #success &= run_command(f"python mk_graph_spec.py {selected_file}")
        #success &= run_command(f"python mk_graph_code.py {selected_file}")
        
        # If successful, rename the output directory
        if success and os.path.exists(base_name):
            run_command(f"mv {base_name} {folder_name}")
            print(f"Successfully processed {model} and created {folder_name} directory")
        else:
            print(f"Error processing {model}")
    
    print("\nAll models processed.")

if __name__ == "__main__":
    main()
