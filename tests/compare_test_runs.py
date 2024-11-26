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
                if line1 != line2:
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
