from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os

load_dotenv()


def get_groq_llm():
    return ChatGroq(
        model="openai/gpt-oss-120b",   # or llama3-70b, gemma2-9b-it, etc.
        temperature=0.2,
        # max_tokens=2048,
        groq_api_key=os.getenv("GROQ_API_KEY")
    )