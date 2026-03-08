# agents/agent1_memory.py
from langchain_core.prompts import PromptTemplate
from core.build_rag import load_vectorstore
from rich.console import Console
from rich.markdown import Markdown
from dynamic_testing.progress import set_progress

console = Console()
memory_db = load_vectorstore()
docs = None

def agent1( state):

    set_progress(status="running", current_agent="agent1", message="Retrieving related code context")

    prompt = PromptTemplate.from_template("""
    You are given Logs indicating error or warning or any other problem in code. Your Task is to get the Logs and Related code to provide solution for that code.

    Logs:
    {query}
                                          
    Related Code is:
    {context}

    Provide a helpful solution.
    """)

    query = state["query"]

    print("Agent 1 with Memory Called")
    print("User Query:", query)
    print("Decision: ", state["decision"])

    # retrieve memory from FAISS
    docs = memory_db.similarity_search(query, k=2)
    # print(docs)
    # md = Markdown(docs)
    # console.print(md)
    context = "\n".join([d.page_content for d in docs])

    final_prompt = prompt.format(context=context, query=query)
    # print("Agent 1 Output:\n", final_prompt)
    return {"agent1_output": final_prompt}

