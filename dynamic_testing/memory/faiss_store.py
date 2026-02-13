# memory/faiss_store.py
from langchain_community.vectorstores import FAISS
import os
from langchain_huggingface import HuggingFaceEmbeddings

embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def load_faiss_store(path="./../memory/vector_store"):
    """
    Load FAISS vector store completely offline.
    No embeddings required if you only want retrieval.
    """

    # Ensure folder exists
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ FAISS folder not found at {path}")

    print("📌 Loading FAISS store from local folder (offline)...")
    db = FAISS.load_local(
        folder_path=path,
        embeddings=embedding,  # Important: offline, no embeddings needed
        allow_dangerous_deserialization=True
    )

    print("✅ FAISS store loaded successfully!")
    return db


# load_faiss_store()
