from state_code import State
from typing import Optional, Dict, Any
from langchain_core.runnables.config import RunnableConfig
from lgcodegen_llm import node_chat_model
from human_input import human_text_input, human_yesno_input

def human_display(val):
    print(val)

# Node Function
def orchestrator(state: State, *, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    # reads: topic
    # writes: sections
    topic = state.topic
    
    # Create prompt for generating section titles
    generation_prompt = f"""Generate up to 4 section titles appropriate for a report on the topic: "{topic}".
    These should be concise, informative, and cover important aspects of the topic.
    Return only the section titles, one per line."""
    
    # Create LLM and invoke with the prompt
    llm = node_chat_model()
    response = llm.invoke(generation_prompt)
    
    # Parse the response into a list of section titles
    # Split by newlines and remove any empty lines
    sections = [section.strip() for section in response.content.split("\n") if section.strip()]
    
    # Ensure we have at most 4 sections
    sections = sections[:4]
    
    return {"sections": sections}

# Node Function
def worker(field_value: str, *, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    # Note: This is a worker node function that processes a single section
    # The field_value is a single section title from state.sections
    
    # Create prompt for generating content for this section
    generation_prompt = f"""Generate informative content for the following report section:
    
    SECTION TITLE: {field_value}
    
    The content should be comprehensive yet concise, providing relevant information and insights.
    Focus on creating meaningful, accurate content for this specific section."""
    
    # Create LLM and invoke with the prompt
    llm = node_chat_model()
    response = llm.invoke(generation_prompt)
    
    # Return the generated section content to be added to processed_sections
    return {"processed_sections": [response.content]}

# Node Function
def synthesizer(state: State, *, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    # reads: topic, processed_sections
    # writes: (final output displayed to user)
    topic = state.topic
    processed_sections = state.processed_sections
    
    # Create a prompt for synthesizing the final report
    generation_prompt = f"""Create a cohesive, well-structured final report on the topic: "{topic}".
    
    Incorporate and synthesize the following section contents:
    
    {chr(10).join([f"SECTION {i+1}:\n{content}\n" for i, content in enumerate(processed_sections)])}
    
    The final report should flow naturally between sections, have a professional tone, and include:
    - A brief introduction to the topic
    - Synthesized section contents (not just copied verbatim)
    - A concise conclusion
    """
    
    # Create LLM and invoke with the prompt
    llm = node_chat_model()
    response = llm.invoke(generation_prompt)
    
    # Display the final report to the user
    human_display("=== FINAL REPORT ===")
    human_display(f"TOPIC: {topic}\n")
    human_display(response.content)
    
    # No state updates needed as this is the final node
    return {}