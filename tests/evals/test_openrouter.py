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
        test_mistral_completion(client_instance)
        test_qwen_coder_completion(client_instance)
        test_perplexity_sonar_completion(client_instance)
        test_perplexity_company_info(client_instance)
        test_direct_api_request(api_key_value)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)