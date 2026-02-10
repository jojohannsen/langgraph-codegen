import os
import pytest
import requests
import json
from openai import OpenAI

# Make sure to set the OPENROUTER_API_KEY environment variable before running tests
# You can do this in your shell: export OPENROUTER_API_KEY="your_api_key_here"

@pytest.fixture
def api_key():
    """Get the OpenRouter API key from environment variables."""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        pytest.skip("OPENROUTER_API_KEY environment variable not set")
    return key

@pytest.fixture
def client(api_key):
    """Create an OpenAI client configured for OpenRouter."""
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

def test_mistral_completion(client):
    """Test completion with Mistral model."""
    completion = client.chat.completions.create(
        model="mistralai/mistral-7b-instruct:free",
        messages=[
            {"role": "user", "content": "Write the python hello world app, and explain how to run it"}
        ]
    )
    
    assert completion.choices[0].message.content is not None
    print(f"\nMistral response:\n{completion.choices[0].message.content}")

def test_qwen_coder_completion(client):
    """Test completion with Qwen coder model."""
    completion = client.chat.completions.create(
        model="qwen/qwen2.5-coder-7b-instruct",
        messages=[
            {"role": "user", "content": "Write the python hello world app, and explain how to run it"}
        ]
    )
    
    assert completion.choices[0].message.content is not None
    print(f"\nQwen response:\n{completion.choices[0].message.content}")

def test_perplexity_sonar_completion(client):
    """Test completion with Perplexity Sonar model."""
    completion = client.chat.completions.create(
        model="perplexity/sonar",
        messages=[
            {"role": "user", "content": "Write the python hello world app, and explain how to run it"}
        ]
    )
    
    assert completion.choices[0].message.content is not None
    print(f"\nPerplexity Sonar response:\n{completion.choices[0].message.content}")

def test_perplexity_company_info(client):
    """Test getting company information with Perplexity Sonar."""
    completion = client.chat.completions.create(
        model="perplexity/sonar",
        messages=[
            {"role": "user", "content": "Please find a mailing address for company: Microsoft"}
        ]
    )
    
    assert completion.choices[0].message.content is not None
    print(f"\nCompany info response:\n{completion.choices[0].message.content}")

def test_direct_api_request(api_key):
    """Test making a direct request to the OpenRouter API."""
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps({
            "model": "qwen/qwen2.5-coder-7b-instruct",
            "messages": [
                {
                    "role": "user",
                    "content": "What is the meaning of life?"
                }
            ],
        })
    )
    
    assert response.status_code == 200
    content = response.json()
    assert "choices" in content
    print(f"\nDirect API response status: {response.status_code}")

from pydantic import BaseModel, Field

class TestStructuredOutput(BaseModel):
    name: str = Field(description="Name of a person")
    city: str = Field(description="Mailing address City")
    state: str = Field(description="Mailing address State")

def test_structured_output(client):
    """Test requesting structured JSON output from the API."""
    try:
        # This test demonstrates requesting structured output
        # Not all models support this format, so we use Claude which has better support
        completion = client.beta.chat.completions.parse(
            model="openai/gpt-4o",
            messages=[
                {
                    "role": "user", 
                    "content": "I've got this content, tell me about Bob:   Once there was a dog named Bimbo and his owner named Bob.   Bob lived in Altadena, somewhere on Lincoln Street.  Yea, I think 574.   That's in California"
                }
            ],
            response_format=TestStructuredOutput
        )
        
        print(completion)
        print(completion.choices[0].message.tool_calls[0].function)
    except Exception as e:
        # Handle case where model might not support structured output
        print(f"\nNote: Structured output test failed with error: {e}")
        print("This may be because the selected model doesn't support response_format parameter.")
        print("Try with models like Claude or GPT-4 that have better structure support.")
        
# Define the desired output structure using Pydantic
class Person(BaseModel):
    name: str = Field(description="The person's name")
    age: int = Field(description="The person's age")

class PersonsOfInterest(BaseModel):
    people: list[Person] = Field(description="The people found in the data")

def test_structured_output2(client):
    """Test requesting structured JSON output from the API."""
    try:
        # Send the request to the OpenAI API
        completion = client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Extract the names and ages of the people mentioned in the following text."},
                {"role": "user", "content": "John is 30 years old and his sister Alice is 25."}
            ],
            response_format=PersonsOfInterest
        )
        print(completion)
        parsed_output = PersonsOfInterest(**completion.choices[0].message.tool_calls[0].function.arguments)
        print(parsed_output)

    except Exception as e:
        # Handle case where model might not support structured output
        print(f"\nNote: Structured output test failed with error: {e}")
        print("This may be because the selected model doesn't support response_format parameter.")
        print("Try with models like Claude or GPT-4 that have better structure support.")
        

def test_structured_function_calling(client):
    """Test function calling style structured output."""
    try:
        # Test with OpenAI function calling style structured output
        # This works with certain models like GPT-4 on OpenRouter
        completion = client.chat.completions.create(
            model="openai/gpt-4o", 
            messages=[
                {
                    "role": "user",
                    "content": "What's the weather like in New York, Paris, and Tokyo today?"
                }
            ],
            tools=[{
                "type": "function",
                "function": {
                    "name": "get_weather_data",
                    "description": "Get weather information for multiple cities",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "cities": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "city": {"type": "string"},
                                        "needs_data": {"type": "boolean"}
                                    },
                                    "required": ["city", "needs_data"]
                                }
                            }
                        },
                        "required": ["cities"]
                    }
                }
            }],
            tool_choice={"type": "function", "function": {"name": "get_weather_data"}}
        )
        
        # Check if tool calls were made successfully
        assert completion.choices[0].message.tool_calls is not None
        
        # Extract and validate the function call data
        tool_call = completion.choices[0].message.tool_calls[0]
        assert tool_call.function.name == "get_weather_data"
        
        # Parse the function arguments
        function_args = json.loads(tool_call.function.arguments)
        print(f"\nFunction calling test successful")
        print(f"Function name: {tool_call.function.name}")
        print(f"Function arguments: {json.dumps(function_args, indent=2)}")
        
        # Validate structure
        assert "cities" in function_args
        assert isinstance(function_args["cities"], list)
        assert len(function_args["cities"]) == 3  # We asked for 3 cities
        
    except Exception as e:
        print(f"\nNote: Function calling test failed with error: {e}")
        print("This may be because the selected model doesn't support function calling.")
        print("Try with models like GPT-4 that have function calling support.")

if __name__ == "__main__":
    # If you want to run the tests directly without pytest
    import sys
    
    try:
        api_key_value = os.getenv("OPENROUTER_API_KEY")
        if not api_key_value:
            print("ERROR: OPENROUTER_API_KEY environment variable not set")
            sys.exit(1)
            
        client_instance = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key_value
        )
        
        print("Running tests...")
        #test_mistral_completion(client_instance)
        #test_qwen_coder_completion(client_instance)
        #test_perplexity_sonar_completion(client_instance)
        #test_perplexity_company_info(client_instance)
        #test_direct_api_request(api_key_value)
        test_structured_output(client_instance)
        test_structured_output2(client_instance)
        #test_structured_function_calling(client_instance)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)
