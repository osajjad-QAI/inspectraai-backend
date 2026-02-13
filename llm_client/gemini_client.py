from dotenv import load_dotenv
from google import genai
import os

load_dotenv()


def generate_gemini_response(
    model_name: str,
    api_key: str,
    system_prompt: str = "",
    user_prompt: str = "",
    temperature: float = 0.7,
    top_p: float = 0.95,
    top_k: int = 40,
    max_output_tokens: int = 2048,
) -> str:
    """
    Generate response using Google Gemini API.
    
    Args:
        model_name: Model name (e.g., "gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash")
        api_key: Google API key
        system_prompt: System instructions for the model
        user_prompt: User's input prompt
        temperature: Controls randomness (0.0 to 2.0)
        top_p: Controls diversity via nucleus sampling (0.0 to 1.0)
        top_k: Controls diversity via top-k sampling
        max_output_tokens: Maximum tokens in response
    
    Returns:
        Generated response text
    """
    try:
        if not api_key:
            raise ValueError("API key is required")
        
        # Create the Gemini client
        client = genai.Client(api_key=api_key)
        
        # Build contents - can be a string or list of parts
        if system_prompt:
            contents = [
                {"role": "system", "parts": [{"text":system_prompt}]},
                {"role": "user", "parts": [{"text": user_prompt}]}
            ]
        else:
            contents = user_prompt
        
        # Generate content
        print("Generating content with Gemini...")

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=genai.types.GenerateContentConfig(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_output_tokens=max_output_tokens,
            )
        )
        print(response)
        
        return response.text
    except Exception as e:
        raise Exception(f"Error generating content with Gemini: {str(e)}")
