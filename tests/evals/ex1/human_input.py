"""
human_input.py - Configurable human input handling

This module provides functions for getting text and yes/no input from humans,
with configurable backends (interrupt or questionary).
"""

from typing import Literal
from langgraph.types import interrupt, Command
import questionary

InputMode = Literal["interrupt", "questionary"]
_current_mode: InputMode = "interrupt"

def init_graph_state(initial_state, text, resume_value):
    return initial_state if text is None else Command(resume=resume_value)

def init_human_input(args: list[str]) -> None:
    """Initialize the human input mode based on command line arguments."""
    # check if --human is in the args, followed by questionary or interrupt
    if "--human" in args:
        if "questionary" in args:
            input_mode = "questionary"
        elif "interrupt" in args:
            input_mode = "interrupt"
        else:
            raise ValueError("Invalid argument for --human")
    else:
        input_mode = "interrupt"
    set_input_mode(input_mode)

def set_input_mode(mode: InputMode) -> None:
    """Set the input mode to either 'interrupt' or 'questionary'."""
    global _current_mode
    _current_mode = mode

def get_input_mode() -> InputMode:
    """Get the current input mode."""
    return _current_mode

def human_text_input(prompt: str) -> str:
    """Get text input from a human using the configured input mode."""
    if _current_mode == "interrupt":
        return interrupt({"text": prompt})
    else:  # questionary mode
        return questionary.text(prompt).ask()

def human_yesno_input(prompt: str) -> bool:
    """Get yes/no input from a human using the configured input mode."""
    if _current_mode == "interrupt":
        return interrupt({"confirm": prompt})
    else:  # questionary mode
        return questionary.confirm(prompt).ask() 
