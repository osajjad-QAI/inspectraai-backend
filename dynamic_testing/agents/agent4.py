# agents/agent4.py
import os
import re
import subprocess
from rich.console import Console
from rich.markdown import Markdown
from dynamic_testing.agents.agent1_memory import docs
from llm_client.groq_client import generate_groq_response
from dynamic_testing.progress import set_progress


console = Console()

def agent4(state):
    set_progress(status="running", current_agent="agent4", message="Generating and running pytest")
    print("Agent 4 invoked")

    agent3_code = state["agent3_output"]
    prompt = f"""
    You are expert in generating Testing code. Extract Python Code from here: ```{agent3_code}```,
    and now write proper unit test code using pytest for the provided code snippet.
    Return **only complete pytest code** with necessary imports and must be runnable.
    Dont make any extra imports and assumptions but be stick near to original code and import functions used in this code: -> ```{docs}```.
    Dont import __safe_print.
    Code should be inside backticks ```.
    """

    llm_text = generate_groq_response(
        model_name=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        api_key=os.getenv("GROQ_API_KEY", ""),
        user_prompt=prompt,
    )
    md = Markdown(llm_text)
    # console.print(md)

    # Extract Python code from LLM response
    pattern = r"```python(.*?)```"
    match = re.search(pattern, llm_text, re.DOTALL)

    print("Extracted Code: ==========================>")
    if not match:
        print("❌ No Python code found in LLM response!")
        return {"agent4_output": "No python code extracted"}

    extracted_code = match.group(1).strip()
    # console.print(Markdown(extracted_code))

    # --- Create .inspectra folder and pytest subfolder in current working directory ---
    # inspectra_dir = os.path.join(os.getcwd(), ".inspectra")
    pytest_dir = os.path.join(os.getcwd(), "pytest")
    os.makedirs(pytest_dir, exist_ok=True)

    conda_env = os.environ.get("CONDA_DEFAULT_ENV")
    print("Current Working Directory: ",os.getcwd())
    print("🐍 Active Conda env:", conda_env if conda_env else "Not in a conda env")

    # Save as Python test file
    test_file_path = os.path.join(pytest_dir, "test_generated.py")
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(extracted_code)

    print(f"✅ Test saved to: {test_file_path}")

    # --- Run pytest using system python ---
    try:
        print("🚀 Running pytest...")
        result = subprocess.run(
            ["python", "-m", "pytest", test_file_path],
            capture_output=True,
            text=True
        )

        print("📌 PYTEST OUTPUT:")
        print(result.stdout)
        print(result.stderr)

    except Exception as e:
        print(f"❌ Error running pytest: {str(e)}")

    return {
        "agent4_output": f"pytest Tsting is completed and result is {result}"
    }
