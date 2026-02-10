from collections import namedtuple

# Named tuple to hold a block of comments and an important line.
ConfigUnit = namedtuple("ConfigUnit", ["context", "graph_line"])

def parse_units(filepath):
    """
    Generator that yields ConfigUnit tuples.
    Each tuple contains:
      - context: a list of comment strings (without '#') preceding an important line.
      - graph_line: the non-comment line.
      
    Empty lines reset the comment buffer.
    """
    with open(filepath, 'r') as file:
        comments = []
        for line in file:
            line = line.strip()
            if not line:
                # Blank line indicates a break; reset comment accumulation.
                comments = []
                continue
            if line.startswith('#'):
                # Remove the '#'
                comments.append(line[1:])
            else:
                # Yield the unit and keep the comments for further important lines in the same block.
                yield ConfigUnit(context="\n".join(comments), graph_line=line)
                comments = []

# Example usage:
import sys
if __name__ == '__main__':
    file_name = sys.argv[1]
    print(f"{file_name=}")
    for unit in parse_units(file_name):
        print("******" + unit.graph_line + "******")
        print(unit.context)
