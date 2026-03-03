import os
from datetime import datetime
from dynamic_testing.graph.llm import get_groq_llm
from dynamic_testing.graph.pipeline import build_graph
from dynamic_testing.progress import set_progress
from rich.console import Console
from rich.markdown import Markdown
import re
console = Console()

llm = get_groq_llm()
graph = build_graph()

LLM_LOG_PATH = os.path.join(".inspectra", "llm_logs.txt")



def send_to_llm(log_line: str, source: str = "stdout / normal"):
    """
    Dummy LLM function.
    Appends each log event to a file in realtime with separators.
    'source' can be primary/secondary like 'stdout / warning'
    """
    os.makedirs(".inspectra", exist_ok=True)

    result = None
    if source=="stderr / error" or source == "stderr / warning":
        result = graph.invoke({"query": log_line.rstrip() + "\n"})
        print("\nFINAL RESULT:\n")
        print(result)
        set_progress(status="completed", current_agent="agent5", message="Analysis complete for this log")
        # md = Markdown(result["agent3_output"])
        # console.print(md)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LLM_LOG_PATH, "a", encoding="utf-8") as f:
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"TIME: {timestamp}\n")
        f.write(f"SOURCE: {source}\n")
        f.write("LOG:\n")
        f.write(log_line.rstrip() + "\n")
        
        if result and result.get("decision") != 'All Clear' and (source=="stderr / error" or source == "stderr / warning"):
            code_blocks = re.findall(
                r"```(?:python)?\n(.*?)```",
                result["agent3_output"],
                re.DOTALL | re.IGNORECASE
            )

            for i, code in enumerate(code_blocks, 1):
                f.write(f"# ---- Python Block {i} ----\n")
                f.write(code.strip() + "\n\n")
        # f.write("LLM Result -->  ",result["agent3_output"])
    
    # return llm.invoke(log_line.rstrip() + "\n")
    # main.py

    
    

