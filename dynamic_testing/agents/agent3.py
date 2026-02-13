# agents/agent3.py

from langchain_core.prompts import ChatPromptTemplate
from rich.console import Console
from rich.markdown import Markdown
import os
from llm_client.groq_client import generate_groq_response
from dynamic_testing.progress import set_progress


console = Console()
 

def agent3(state):
    set_progress(status="running", current_agent="agent3", message="Generating fix suggestions")
    print("Agent 3 invoked")

    agent1_text = state["agent1_output"]
    # prompt = ChatPromptTemplate.from_messages([
    system = "You are Code Error solving agent. You fix or propose corrections for the code that caused the error."
    user = f"""

    Original Input from Agent1:
    {agent1_text}

    Task:
    If related:
    - Explain the fix.
    - Provide a corrected version of the code snippet in proper .py format.
    - Provide any alternative suggestions.

    If NOT related:
    - Suggest what the developer should check next.

    Return a helpful technical answer.
    """

    response = generate_groq_response(
        model_name=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        api_key=os.getenv("GROQ_API_KEY", ""),
        system_prompt=system,
        user_prompt=user,
    )
    # print(response)
    # md = Markdown(response.content)

    # console.print(md)
    # print(response.content)

    return {
        "agent3_output": response
    }
