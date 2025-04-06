import re
import sys
from itertools import zip_longest

def normalize_test_output(test_output):
    """
    Normalize test output by replacing variable fields with constant values
    to enable comparison between different test runs.

    Args:
        test_output (str): Raw test output string

    Returns:
        str: Normalized test output
    """
    # Split the output into lines for processing
    lines = test_output.split('\n')
    normalized_lines = []

    # Regular expressions for matching variable fields
    created_at_pattern = r"created_at='([^']+)'"
    checkpoint_id_pattern = r"checkpoint_id': '([^']+)'"

    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue

        # Replace created_at timestamps with a constant value
        line = re.sub(created_at_pattern, "created_at='NORMALIZED_TIMESTAMP'", line)

        # Replace checkpoint_ids with a constant value
        line = re.sub(checkpoint_id_pattern, "checkpoint_id': 'NORMALIZED_CHECKPOINT_ID'", line)

        normalized_lines.append(line)

    return '\n'.join(normalized_lines)

import ast
import json


import re
import ast
import json

def compare_snapshot_strings(snapshot_str1, snapshot_str2):
    """
    Compare two StateSnapshot string representations.
    
    Args:
        snapshot_str1 (str): First StateSnapshot string
        snapshot_str2 (str): Second StateSnapshot string
        
    Returns:
        bool: True if snapshots are equal (ignoring dict order), False otherwise or on error
    """
    try:
        # Validate input strings
        if not isinstance(snapshot_str1, str) or not isinstance(snapshot_str2, str):
            return False
            
        # Check if strings match the expected StateSnapshot pattern
        pattern = r"^StateSnapshot\(.*\)$"
        if not re.match(pattern, snapshot_str1) or not re.match(pattern, snapshot_str2):
            return False
        
        # Extract the content inside StateSnapshot()
        def extract_content(snapshot_str):
            content = re.match(r"StateSnapshot\((.*)\)$", snapshot_str).group(1)
            
            # Create a dictionary-like string by wrapping in braces
            dict_str = "{" + content + "}"
            
            # Now manually replace the field assignments to make it valid Python dict syntax
            # Replace fieldname= with 'fieldname':
            dict_str = re.sub(r'(\w+)=', r"'\1':", dict_str)
            
            # Try to parse with ast.literal_eval
            try:
                return ast.literal_eval(dict_str)
            except (SyntaxError, ValueError) as e:
                # If we can't parse it, raise an exception to be caught by the outer try block
                raise ValueError(f"Failed to parse snapshot: {e}")
        
        # Convert both snapshots to dictionaries
        dict1 = extract_content(snapshot_str1)
        dict2 = extract_content(snapshot_str2)
        
        # Convert to JSON with sorted keys to normalize dictionary key order
        sorted1 = json.dumps(dict1, sort_keys=True)
        sorted2 = json.dumps(dict2, sort_keys=True)
        
        # Compare the normalized JSON strings
        return sorted1 == sorted2
        
    except Exception as e:
        # Catch any exceptions and return False
        return False

def compare_files(file1_path, file2_path, context_lines=3):
    # Print comparison files on one line
    print(f"{file1_path} vs. {file2_path}")

    try:
        with open(file1_path, 'r') as f1, open(file2_path, 'r') as f2:
            content1 = normalize_test_output(f1.read())
            content2 = normalize_test_output(f2.read())

            if content1 == content2:
                print("✓ Test runs are equivalent")
                return

            # If different, find and display the differences
            print("✗ Test runs differ")
            print("\nFirst few differences:")

            lines1 = content1.split('\n')
            lines2 = content2.split('\n')
            # Compare line by line to find differences
            for i, (line1, line2) in enumerate(zip_longest(lines1, lines2, fillvalue=None)):
                if line1 != line2 and not compare_snapshot_strings(line1, line2):
                    # Print line numbers and differences
                    print(f"\nDifference at line {i + 1}:")

                    # Handle cases where one file is longer than the other
                    if line1 is None:
                        print(f"File 1: <end of file>")
                        print(f"File 2: {line2.rstrip()}")
                    elif line2 is None:
                        print(f"File 1: {line1.rstrip()}")
                        print(f"File 2: <end of file>")
                    else:
                        print(f"File 1: {line1.rstrip()}")
                        print(f"File 2: {line2.rstrip()}")

                    # Only show the first few differences
                    if i >= context_lines:
                        print("\n... additional differences omitted ...")
                        break

    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_test_runs.py <file1> <file2>")
        sys.exit(1)
        
    compare_files(sys.argv[1], sys.argv[2])
