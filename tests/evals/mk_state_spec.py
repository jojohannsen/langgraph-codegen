from pathlib import Path
import sys
from colorama import init, Fore, Style
from mk_utils import read_file_and_get_subdir, mk_agent, get_single_prompt, parse_graph, validate_graph, OpenRouterAgent, prepare_working_folder, get_tools

if __name__ == "__main__":
    # Initialize colorama (needed for Windows)
    init()
    
    if len(sys.argv) < 2:
        print("Usage: python mk_state_spec.py graph_spec_file")
        sys.exit(1)

    file_path = sys.argv[1]
    graph_name, graph_spec = read_file_and_get_subdir(file_path)
    config = prepare_working_folder(graph_name)   
    parsed_graph = parse_graph(graph_spec)
    validated_graph = validate_graph(parsed_graph)

    print(validated_graph)
    print(f"{Fore.GREEN}Graph folder: {Fore.BLUE}{graph_name}{Style.RESET_ALL}")
    agent_library, llm_provider, llm_model = get_tools(config, 'spec')

    # get the state_spec_prompt from the config
    state_spec_prompt = get_single_prompt(config, 'state_spec')
    graph_notation = get_single_prompt(config, 'graph_notation')
    state_spec_prompt = state_spec_prompt.format(
        graph_notation=graph_notation,
        model_name=llm_model
    )

    # print the prompt
    # ask user if they want to run the agent
    # save the prompt to mk_state_spec.prompt.txt
    # let user know if state-spec.md exists, and if it is not empty
    state_spec_file = f"{graph_name}/state-spec.md"
    if Path(state_spec_file).exists() and Path(state_spec_file).stat().st_size > 0:
        print(f"{Fore.RED}state-spec.md exists and is not empty{Style.RESET_ALL}")
        user_input = input(f"{Fore.CYAN}Do you want to delete it? (y/n){Style.RESET_ALL}")
        if user_input == "y":
            Path(state_spec_file).unlink()
    # ask if they want to run the agent
    user_input = input(f"{Fore.CYAN}Do you want to run the agent? (y/n){Style.RESET_ALL}")
    if user_input == "y":
        agent = mk_agent(graph_name, llm_provider, llm_model, agent_library, 
                         system_prompt="You are a technical writer, creating design documents for the development team.  You write in markdown.")
        human_request = f"""Here's the graph specification:
<GRAPH_SPEC>
{graph_spec}
</GRAPH_SPEC>

Please write the State class specification in markdown, and save it to 'state-spec.md'
"""
        with open("mk_state.spec_prompt.txt", "w") as f:
            f.write("SYSTEM_PROMPT\n" + state_spec_prompt + "\n\nUSER_PROMPT\n" + human_request)
        result = agent.run(state_spec_prompt + "\n\n" + human_request)
    else:
        exit(0)
    # write result to mk_state_spec.result.txt
    with open("mk_state_spec.result.txt", "w") as f:
        f.write(str(result))
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



