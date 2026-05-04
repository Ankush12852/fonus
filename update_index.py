import argparse
import json
import os
import sys
from pathlib import Path

from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
)
from llama_index.core.schema import Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq
from llama_index.core.node_parser import SentenceSplitter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
INDEXES_DIR  = PROJECT_ROOT / "indexes"
ENV_PATH     = PROJECT_ROOT / ".env"

# M10 lives in its own dedicated store
M10_INDEX_DIR = PROJECT_ROOT / "dgca_index_store"


# ---------------------------------------------------------------------------
# Helpers  (mirrors build_index.py)
# ---------------------------------------------------------------------------
def load_env():
    """Load key=value pairs from .env into os.environ."""
    if not ENV_PATH.exists():
        print(f"ERROR: .env not found at {ENV_PATH}")
        sys.exit(1)
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def configure_settings():
    """Configure LlamaIndex global settings (same as build_index.py)."""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("ERROR: GROQ_API_KEY not found in .env")
        sys.exit(1)

    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.llm = Groq(
        model="llama-3.3-70b-versatile",
        api_key=groq_api_key,
    )
    Settings.text_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    Settings.context_window = 6000
    Settings.num_output = 512


def resolve_index_path(module_name: str) -> Path:
    """Return the persist directory for a given module."""
    if module_name.upper() == "M10":
        return M10_INDEX_DIR
    return INDEXES_DIR / module_name


def load_existing_index(index_path: Path):
    """Load an existing VectorStoreIndex from disk."""
    if not index_path.exists():
        print(f"ERROR: Index directory not found at {index_path}")
        print("       Run build_index.py first to create the index.")
        sys.exit(1)

    storage_context = StorageContext.from_defaults(persist_dir=str(index_path))
    index = load_index_from_storage(storage_context)
    return index


def count_index_docs(index) -> int:
    """Return the number of documents (nodes) currently in the index."""
    try:
        return len(index.docstore.docs)
    except Exception:
        return -1  # unknown — non-fatal


# ---------------------------------------------------------------------------
# Document loaders
# ---------------------------------------------------------------------------
def load_from_file(file_path: str) -> list:
    """Load documents from a single file."""
    path = Path(file_path)
    if not path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)
    return SimpleDirectoryReader(input_files=[str(path)]).load_data()


def load_from_dir(dir_path: str) -> list:
    """Load all supported documents from a directory."""
    path = Path(dir_path)
    if not path.exists():
        print(f"ERROR: Directory not found: {dir_path}")
        sys.exit(1)
    return SimpleDirectoryReader(input_dir=str(path)).load_data()


def load_from_questions(questions_path: str) -> list:
    """
    Load questions from a JSON file and wrap each as a LlamaIndex Document.

    Expected JSON format (list of objects):
        [{"question": "...", "answer": "...", ...}, ...]
    or a plain list of strings:
        ["question text", ...]
    """
    path = Path(questions_path)
    if not path.exists():
        print(f"ERROR: Questions file not found: {questions_path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    # Handle {"questions": [...]} wrapper format
    if isinstance(data, dict):
        # Try common wrapper keys
        for key in ["questions", "data", "items", "results"]:
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            # If no known key found, take the first list value
            for v in data.values():
                if isinstance(v, list):
                    data = v
                    break

    if isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, str):
                text = item
            elif isinstance(item, dict):
                # Build a readable text block from all key-value pairs
                parts = []
                for k, v in item.items():
                    parts.append(f"{k}: {v}")
                text = "\n".join(parts)
            else:
                text = str(item)

            doc = Document(
                text=text,
                metadata={"source": str(path), "question_index": i},
            )
            documents.append(doc)
    else:
        print(f"ERROR: Expected a JSON array in {questions_path}, got {type(data).__name__}")
        sys.exit(1)

    return documents


# ---------------------------------------------------------------------------
# Core updater
# ---------------------------------------------------------------------------
def update_index(module_name: str, new_documents: list):
    """Insert new_documents into the existing module index and persist."""
    module_name = module_name.upper()
    index_path  = resolve_index_path(module_name)

    print(f"Adding {len(new_documents)} new document(s) to {module_name} index...")

    # Load existing index
    index = load_existing_index(index_path)

    # Count docs before insertion
    before_count = count_index_docs(index)

    # Insert every document
    for doc in new_documents:
        index.insert(doc)

    # Persist back to the same location
    index.storage_context.persist(persist_dir=str(index_path))

    # Count docs after insertion
    after_count = count_index_docs(index)

    print(f"{module_name} index updated successfully")
    if after_count >= 0:
        print(f"Total documents now: {after_count}")
    else:
        print(f"Documents added: {len(new_documents)} (total count unavailable)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Add new documents to an existing LlamaIndex module index."
    )
    parser.add_argument(
        "--module", "-m",
        required=True,
        help="Module name, e.g. M6 or M10",
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--file",
        metavar="PATH",
        help="Path to a single file (PDF, TXT, etc.) to add",
    )
    source_group.add_argument(
        "--dir",
        metavar="PATH",
        help="Path to a folder — all supported files inside will be added",
    )
    source_group.add_argument(
        "--questions",
        metavar="PATH",
        help="Path to a JSON file containing questions to add as text documents",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    load_env()
    configure_settings()

    # Load new documents based on the chosen source
    if args.file:
        new_docs = load_from_file(args.file)
    elif args.dir:
        new_docs = load_from_dir(args.dir)
    else:  # args.questions
        new_docs = load_from_questions(args.questions)

    if not new_docs:
        print("No documents found — nothing to add.")
        sys.exit(0)

    update_index(args.module, new_docs)


if __name__ == "__main__":
    main()
