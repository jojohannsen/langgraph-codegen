from mk_utils import parse_graph, validate_graph
import os
import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lgload.py file.txt")
        exit(0)

    file_name = sys.argv[1]
    
    if not os.path.exists(file_name):
        print(f"Error: File {file_name} does not exist")
        exit(1)
        
    with open(file_name, 'r') as f:
        file_contents = f.read()
    
    parsed_graph = parse_graph(file_contents)
    validation_result = validate_graph(parsed_graph)
    
    print(validation_result)
