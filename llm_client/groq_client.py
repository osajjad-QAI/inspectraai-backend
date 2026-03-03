from groq import Groq
import os


def generate_groq_response(
    model_name: str,
    api_key: str,
    system_prompt: str = "",
    user_prompt: str = "",
    temperature: float = 1.0,
    top_p: float = 1.0,
    max_tokens: int = 8192,
) -> str:
    """
    Generate response using Groq API.
    
    Args:
        model_name: Model name (e.g., "mixtral-8x7b-32768", "llama-3.3-70b-versatile")
        api_key: Groq API key
        system_prompt: System instructions for the model
        user_prompt: User's input prompt
        temperature: Controls randomness (0.0 to 2.0)
        top_p: Controls diversity via nucleus sampling (0.0 to 1.0)
        max_tokens: Maximum tokens in response
    
    Returns:
        Generated response text
    """
    try:
        client = Groq(api_key=api_key)
        
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_prompt})

        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=False,
        )

        return completion.choices[0].message.content
    except Exception as e:
        raise Exception(f"Error generating content with Groq: {str(e)}")
