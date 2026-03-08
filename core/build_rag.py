import os
import ast
from typing import List
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
import fnmatch

# ========================================================
# CONFIGURATION
# ========================================================

INSPECTRA_FOLDER = ".inspectra"
VECTOR_STORE_SUBDIR = "vector_store"
DEFAULT_PROJECT_PATH = os.getenv("PROJECT_PATH", "E:/FYP/fyp")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CODE_FILE_EXTENSIONS = [".py", ".js", ".java", ".txt", ".ts", ".go", ".cpp"]


def load_ignore_rules(base_path):
    rules = {
        "folders": set(),
        "files": set(),
        "patterns": []
    }

    ignore_path = os.path.join(base_path, ".ignore")
    if not os.path.exists(ignore_path):
        return rules

    with open(ignore_path, "r") as f:
        for line in f:
            rule = line.strip()
            if not rule or rule.startswith("#"):
                continue

            if rule.endswith("/"):
                rules["folders"].add(rule.rstrip("/"))
            elif "*" in rule or "?" in rule:
                rules["patterns"].append(rule)
            else:
                rules["files"].add(rule)

    return rules


def should_ignore_dir(dir_name, rules):
    return dir_name in rules["folders"]


def should_ignore_file(filename, rules):
    if filename in rules["files"]:
        return True

    for pattern in rules["patterns"]:
        if fnmatch.fnmatch(filename, pattern):
            return True

    return False


# ========================================================
# 🔹 Embedding Model
# ========================================================
def get_embedding_model():
    # Force a concrete device to avoid meta tensor issues during loading.
    device = os.getenv("EMBEDDING_DEVICE", "cpu")
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": device}
    )


# ========================================================
# 🔹 Extract Python Functions (name + params)
# ========================================================
def extract_python_functions(code: str) -> List[str]:
    """
    Extract function signatures from Python code.
    Returns list like: ['func(a, b=1)', 'main()']
    """
    functions = []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return functions

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            args = []

            for arg in node.args.args:
                args.append(arg.arg)

            if node.args.vararg:
                args.append(f"*{node.args.vararg.arg}")

            for kw in node.args.kwonlyargs:
                args.append(kw.arg)

            if node.args.kwarg:
                args.append(f"**{node.args.kwarg.arg}")

            signature = f"{node.name}({', '.join(args)})"
            functions.append(signature)

    return functions


# ========================================================
# 🔹 Load Code Files as Documents
# ========================================================
def load_code_documents(folder_path: str, inspectra_dir: str = None) -> List[Document]:
    documents = []

    ignore_rules = load_ignore_rules(folder_path)

    inspectra_root = None
    if inspectra_dir:
        inspectra_root = os.path.abspath(inspectra_dir)

    for root, dirnames, files in os.walk(folder_path):
        # ❌ Skip .inspectra entirely
        if inspectra_root and os.path.abspath(root).startswith(inspectra_root):
            continue

        # ❌ Remove ignored directories (important!)
        dirnames[:] = [
            d for d in dirnames
            if not should_ignore_dir(d, ignore_rules)
        ]

        for file in files:
            # ❌ Ignore files based on .ignore
            if should_ignore_file(file, ignore_rules):
                continue

            # ❌ Only index allowed code extensions
            if not any(file.endswith(ext) for ext in CODE_FILE_EXTENSIONS):
                continue

            file_path = os.path.join(root, file)

            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()

                if not content:
                    continue

                functions = []
                if file.endswith(".py"):
                    functions = extract_python_functions(content)

                documents.append(
                    Document(
                        page_content=content,
                        metadata={
                            "source": file_path,
                            "language": "python" if file.endswith(".py") else "other",
                            "functions": functions,
                            "full_code": content
                        }
                    )
                )

            except Exception as e:
                print(f"⚠ Skipping {file_path}: {e}")

    return documents


# ========================================================
# 🔹 Build & Save FAISS Vector Store
# ========================================================
def build_and_save_vectorstore(base_path: str = None):
    print("📌 Loading embedding model...")
    embeddings = get_embedding_model()

    if not base_path:
        base_path = DEFAULT_PROJECT_PATH

    inspectra_dir = os.path.join(base_path, INSPECTRA_FOLDER)
    vector_store_dir = os.path.join(inspectra_dir, VECTOR_STORE_SUBDIR)

    print(f"📌 Scanning code from: {base_path}")

    documents = load_code_documents(base_path, inspectra_dir=inspectra_dir)

    if not documents:
        print("⚠ No code files found to index.")
        return

    print(f"📚 Indexed {len(documents)} files")

    print("🔨 Creating FAISS vector store...")
    vector_store = FAISS.from_documents(documents, embeddings)

    os.makedirs(vector_store_dir, exist_ok=True)
    vector_store.save_local(vector_store_dir)

    print(f"✅ Vector store saved to: {vector_store_dir}")


# ========================================================
# 🔹 Wrapper: Load Vector Store
# ========================================================
def load_vectorstore(base_path: str = None):
    if not base_path:
        base_path = DEFAULT_PROJECT_PATH

    vector_store_dir = os.path.join(base_path, INSPECTRA_FOLDER, VECTOR_STORE_SUBDIR)

    if not os.path.exists(vector_store_dir):
        raise FileNotFoundError("❌ Vector store not found. Build it first.")

    print("📌 Loading FAISS vector store...")
    embeddings = get_embedding_model()
    vector_store = FAISS.load_local(
        folder_path=vector_store_dir,
        embeddings=embeddings,
        allow_dangerous_deserialization=True
    )

    print("✅ Vector store loaded")
    return vector_store


# ========================================================
# 🔹 Example Usage
# ========================================================
# if __name__ == "__main__":
    # build_and_save_vectorstore()

    # vs = load_vectorstore()
    # results = vs.similarity_search("function that loads files", k=3)

    # for r in results:
    #     print("\n📄 Source:", r.metadata["source"])
    #     print("🧠 Functions:", r.metadata["functions"])
    #     print("📌 Snippet:", r.page_content[:200], "...")
