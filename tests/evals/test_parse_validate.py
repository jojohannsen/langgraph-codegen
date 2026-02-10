import os
import sys
from pathlib import Path
from langgraph_DSL import graph_examples, evaluator_optimizer, jokester, md_consensus, orchestrator_worker, parallelization, prompt_chaining, routing
from mk_utils import parse_graph, validate_graph

def test_parse_validate():
    # Create directories if they don't exist
    Path("actual_results").mkdir(exist_ok=True)
    expected_dir = Path("expected_results")
    actual_dir = Path("actual_results")
    
    # Dictionary to map graph names to their examples
    graph_dict = {
        "evaluator_optimizer": evaluator_optimizer,
        "jokester": jokester,
        "md_consensus": md_consensus,
        "orchestrator_worker": orchestrator_worker,
        "parallelization": parallelization,
        "prompt_chaining": prompt_chaining,
        "routing": routing
    }
    
    # Process each graph example
    for name, graph in graph_dict.items():
        # Parse and validate the graph
        parsed_graph = parse_graph(graph)
        validated_graph = validate_graph(parsed_graph)
        
        # Save the result to actual_results folder
        result_path = actual_dir / f"{name}.txt"
        with open(result_path, "w") as f:
            f.write(str(validated_graph))
        
        print(f"Processed: {name}")
    
    # Check if expected_results directory exists
    assert expected_dir.exists(), f"Expected results directory '{expected_dir}' does not exist."
    
    # Compare actual results with expected results
    matching = []
    different = []
    missing_expected = []
    
    for actual_file in actual_dir.glob("*.txt"):
        name = actual_file.stem
        expected_file = expected_dir / actual_file.name
        
        if not expected_file.exists():
            missing_expected.append(name)
            continue
        
        with open(actual_file, "r") as f1, open(expected_file, "r") as f2:
            actual_content = f1.read()
            expected_content = f2.read()
            
            if actual_content == expected_content:
                matching.append(name)
            else:
                different.append(name)
    
    # Print results
    print("\n===== RESULTS =====")
    print(f"MATCHING ({len(matching)}): {', '.join(matching)}")
    print(f"DIFFERENT ({len(different)}): {', '.join(different)}")
    if missing_expected:
        print(f"MISSING EXPECTED ({len(missing_expected)}): {', '.join(missing_expected)}")
    
    # Use pytest assertions instead of exit codes
    assert not different, f"Found differences between actual and expected results: {', '.join(different)}"
    print("\n✅ TEST PASSED: All actual results match expected results")

if __name__ == "__main__":
    test_parse_validate()