from openai import OpenAI, APIError
from backend.utils import env_loader
import json

# env_loader automatically loads default .env files at import time

# Get OpenAI API key from environment
OPENAI_API_KEY = env_loader.get_env("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not set in environment variables.")

# Initialize the OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Default model can be overridden via settings.env → AI_MODEL
AI_MODEL = env_loader.get_env("AI_MODEL", "gpt-4o-mini")

def ask_openai(prompt: str,
               system_prompt: str = "You are a helpful assistant.",
               model: str | None = None) -> str:
    """
    Send a prompt to OpenAI's API and return the response text.
    Args:
        prompt (str): The user prompt/question.
        system_prompt (str): The system message (instructions for the assistant).
        model (str): The OpenAI model to use.
    Returns:
        str: The assistant's reply.
    Raises:
        Exception: If the API request fails.
    """
    # Use env‑defined default when caller does not specify
    if model is None:
        model = AI_MODEL
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=512,
            temperature=0.7,
        )
        response_content = response.choices[0].message.content.strip()
        try:
            return json.loads(response_content)
        except json.JSONDecodeError:
            return response_content
    except APIError as e:
        # Log or handle API errors as needed
        raise RuntimeError(f"OpenAI API request failed: {e}")