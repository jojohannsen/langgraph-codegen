#!/bin/bash

# List all text files and add to array
txt_files=($(ls *.txt))

# Print the list with numbers
echo "Available .txt files:"
for i in "${!txt_files[@]}"; do
    echo "$((i+1)). ${txt_files[$i]}"
done

# Prompt user to select a file
echo -n "Enter number of file to process: "
read selection

# Validate input
if ! [[ "$selection" =~ ^[0-9]+$ ]] || [ "$selection" -lt 1 ] || [ "$selection" -gt "${#txt_files[@]}" ]; then
    echo "Invalid selection. Exiting."
    exit 1
fi

# Get the selected file
selected_file="${txt_files[$((selection-1))]}"
echo "Processing $selected_file..."

# Extract base name without extension
base_name="${selected_file%.txt}"

# Run the commands from lg_testit with the selected file
set -x
rm -rf "$base_name"
python mk_state_spec.py "$selected_file"
python mk_state_code.py "$selected_file"
python mk_node_spec.py "$selected_file"
python mk_node_code.py "$selected_file"
python mk_graph_spec.py "$selected_file" 2>/dev/null || echo "Note: mk_graph_spec.py not found or failed"
python mk_graph_code.py "$selected_file" 2>/dev/null || echo "Note: mk_graph_code.py not found or failed"