"""
Fonus Learning - M10 Ingest Pipeline (LlamaIndex)
Builds or updates vector index from data/books/ (.pdf and .txt), persists to dgca_index_store.
Tracks indexed files in dgca_index_store/indexed_files.txt for incremental updates.
Use --fresh to force a full rebuild.
"""

import argparse
import os
import shutil
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings,
    StorageContext,
    load_index_from_storage,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq
from llama_index.core.node_parser import SentenceSplitter

# --- Configuration (relative to project root = directory containing this script) ---
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data" / "books"
INDEX_PERSIST_DIR = PROJECT_ROOT / "dgca_index_store"
INDEXED_FILES_PATH = INDEX_PERSIST_DIR / "indexed_files.txt"
ENV_PATH = PROJECT_ROOT / ".env"


def load_env():
    """Load API keys from .env file into os.environ."""
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def get_all_source_files():
    """Return list of all .pdf and .txt file paths under DATA_DIR (relative to DATA_DIR for portability)."""
    if not DATA_DIR.exists():
        return []
    paths = []
    for ext in (".pdf", ".txt"):
        paths.extend(DATA_DIR.rglob(f"*{ext}"))
    return sorted(paths)


def read_indexed_files():
    """Return set of relative path strings already recorded in indexed_files.txt."""
    if not INDEXED_FILES_PATH.exists():
        return set()
    with open(INDEXED_FILES_PATH, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def write_indexed_files(relative_paths):
    """Write all indexed relative paths to indexed_files.txt (one per line)."""
    INDEX_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEXED_FILES_PATH, "w", encoding="utf-8") as f:
        for p in sorted(relative_paths):
            f.write(p + "\n")


def append_indexed_files(relative_paths):
    """Append new relative paths to indexed_files.txt."""
    with open(INDEXED_FILES_PATH, "a", encoding="utf-8") as f:
        for p in sorted(relative_paths):
            f.write(p + "\n")


def configure_settings():
    """Set LlamaIndex embedding model, LLM, and text splitter."""
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.llm = Groq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
    )
    Settings.text_splitter = SentenceSplitter(chunk_size=256, chunk_overlap=20)
    print("    Embeddings: HuggingFace (BAAI/bge-small-en-v1.5)")
    print("    LLM: Groq (llama-3.3-70b-versatile)")


def build_dgca_index(fresh=False):
    """
    Build or update the vector index.
    - If --fresh or dgca_index_store does not exist: build from scratch.
    - If dgca_index_store exists and not --fresh: load index and only add new files; track in indexed_files.txt.
    """
    if not ENV_PATH.exists():
        print(f"ERROR: .env not found at {ENV_PATH}")
        return
    load_env()

    if not os.getenv("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY not found in .env")
        return

    if not DATA_DIR.exists() or not list(DATA_DIR.iterdir()):
        print(f"ERROR: {DATA_DIR} is missing or empty.")
        return

    all_paths = get_all_source_files()
    if not all_paths:
        print(f"No .pdf or .txt files found in {DATA_DIR}")
        return

    # --- Fresh rebuild: delete store and build all ---
    if fresh or not INDEX_PERSIST_DIR.exists():
        if INDEX_PERSIST_DIR.exists():
            print(f"--- --fresh: Removing existing index {INDEX_PERSIST_DIR} ---")
            shutil.rmtree(INDEX_PERSIST_DIR)

        print("--- 1. Configuring LlamaIndex Settings ---")
        configure_settings()

        print("--- 2. Loading all documents from data/books/ ---")
        documents = SimpleDirectoryReader(
            input_dir=str(DATA_DIR),
            required_exts=[".pdf", ".txt"],
        ).load_data()
        print(f"    Loaded {len(documents)} document(s)")

        print("--- 3. Building vector index (fresh) ---")
        index = VectorStoreIndex.from_documents(documents, show_progress=True)

        INDEX_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        index.storage_context.persist(persist_dir=str(INDEX_PERSIST_DIR))

        # Record all indexed files by relative path
        relative_paths = [str(p.relative_to(DATA_DIR)) for p in all_paths]
        write_indexed_files(relative_paths)
        print(f"--- 4. Index saved to {INDEX_PERSIST_DIR}; recorded {len(relative_paths)} file(s) in indexed_files.txt ---")
        print("DONE. Run query.py to chat with Fonus.")
        return

    # --- Incremental: load index and add only new files ---
    indexed_set = read_indexed_files()
    # New files = paths whose relative form is not in indexed_set
    new_paths = [p for p in all_paths if str(p.relative_to(DATA_DIR)) not in indexed_set]

    if not new_paths:
        print("No new files to index. Index is up to date.")
        return

    print("--- 1. Configuring LlamaIndex Settings ---")
    configure_settings()

    print(f"--- 2. Found {len(new_paths)} new file(s) to index ---")
    for p in new_paths:
        print(f"    + {p.relative_to(DATA_DIR)}")

    print("--- 3. Loading new documents ---")
    new_documents = SimpleDirectoryReader(
        input_files=[str(p) for p in new_paths],
    ).load_data()
    print(f"    Loaded {len(new_documents)} document(s)")

    print("--- 4. Loading existing index ---")
    storage_context = StorageContext.from_defaults(persist_dir=str(INDEX_PERSIST_DIR))
    index = load_index_from_storage(storage_context=storage_context)

    print("--- 5. Inserting new nodes into index ---")
    new_nodes = Settings.text_splitter.get_nodes_from_documents(new_documents)
    index.insert_nodes(new_nodes)

    print("--- 6. Persisting updated index ---")
    index.storage_context.persist(persist_dir=str(INDEX_PERSIST_DIR))

    new_relative = [str(p.relative_to(DATA_DIR)) for p in new_paths]
    append_indexed_files(new_relative)
    print(f"--- 7. Updated indexed_files.txt with {len(new_relative)} new file(s) ---")
    print("DONE. Run query.py to chat with Fonus.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build or update DGCA M10 vector index.")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Force full rebuild: delete dgca_index_store and re-index all files.",
    )
    args = parser.parse_args()
    build_dgca_index(fresh=args.fresh)
