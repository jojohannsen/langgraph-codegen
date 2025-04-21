from pathlib import Path
import sys
from colorama import init, Fore, Style
from mk_utils import get_config,read_file_and_get_subdir, mk_agent, get_single_prompt, parse_graph, validate_graph, OpenRouterAgent

if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_state_spec.py graph_spec_file")
        sys.exit(1)

    file_path = sys.argv[1]
    graph_name, graph_spec = read_file_and_get_subdir(file_path)
    parsed_graph = parse_graph(graph_spec)
    validated_graph = validate_graph(parsed_graph)
    print(validated_graph)
    # create the working_dir if it does not exist
    Path(graph_name).mkdir(parents=True, exist_ok=True)
    config = get_config(graph_name)
    print(f"{Fore.GREEN}Graph folder: {Fore.BLUE}{graph_name}{Style.RESET_ALL}")
    agent = mk_agent(graph_name, config)
    # get the state_spec_prompt from the config
    state_spec_prompt = get_single_prompt(config, 'state_spec')
    graph_spec_description = get_single_prompt(config, 'graph_spec_description')
    prompt = state_spec_prompt.format(
        graph_spec_description=graph_spec_description,
        graph_spec=graph_spec,
        model_name=agent.model.id
    )
    print("STATE_SPEC_PROMPT: ", prompt)
    result = agent.run(prompt)
    print("RESULT: ", result)
    state_spec_file = f"{graph_name}/state-spec.md"
    # if the agent is an OpenRouterAgent, we need to write the response to the graph_name/state_spec.md file
    if isinstance(agent, OpenRouterAgent):
        with open(state_spec_file, "w") as f:
            f.write(result.choices[0].message.content)
    else:
        pass # the Agno agent writes the response to the correct file
    # verify that the state_spec.md file exists
    if not Path(state_spec_file).exists():
        print(f"{Fore.RED}State spec file does not exist{Style.RESET_ALL}")
        sys.exit(1)
    # verify that the state_spec.md file is not empty
    if Path(state_spec_file).stat().st_size == 0:
        print(f"{Fore.RED}State spec file is empty{Style.RESET_ALL}")
        sys.exit(1)



