from utils.setup_venv import setup_environment
from core.build_rag import build_and_save_vectorstore, load_vectorstore
from core.get_files import get_files
from core.run_project import run_with_watch
import os
import sys
# from langgraph import main




if __name__ == "__main__":
    # get_files()
    setup_environment(env_type="conda", env_name="obaidenv", install_deps="Yes")


    build_and_save_vectorstore()

    # vs = load_vectorstore()
    # results = vs.similarity_search("function that loads files", k=1)

    # for r in results:
    #     print("\n📄 Source:", r.metadata["source"])
    #     print("🧠 Functions:", r.metadata["functions"])
    #     print("📌 Snippet:", r.page_content, "...")



    # ======================================================
    # CLI usage (BAT / shell friendly)
    # ======================================================
    # if len(sys.argv) < 2:
    #     print("❌ Usage:")
    #     print("   python run_and_capture.py \"python main.py\"")
    #     print("   python run_and_capture.py \"streamlit run app.py\"")
    #     sys.exit(1)

    cmd = "python main.py"
    run_with_watch(cmd, "conda", "obaidenv", workdir=os.getcwd())
