import json
import os
import sys
from pathlib import Path

from llama_index.core import SimpleDirectoryReader, Settings, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq
from llama_index.core.node_parser import SentenceSplitter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
BOOKS_JSON   = PROJECT_ROOT / "data" / "books.json"
BOOKS_DIR    = PROJECT_ROOT / "data" / "books"
INDEXES_DIR  = PROJECT_ROOT / "indexes"
MODULES_DIR  = PROJECT_ROOT / "data" / "Modules"
ENV_PATH     = PROJECT_ROOT / ".env"

# M10 already lives in its own store – never rebuild it here
SKIP_MODULES = {"M10"}


# ---------------------------------------------------------------------------
# Helpers
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
    """Configure LlamaIndex global settings."""
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


def load_books_json():
    try:
        with open(BOOKS_JSON, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {BOOKS_JSON} not found.")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Core builder
# ---------------------------------------------------------------------------
def build_module(module_name: str) -> str:
    """Build the vector index for a single module. Returns 'done'/'skipped'/'failed'."""
    index_path = INDEXES_DIR / module_name

    # Skip if index already exists
    if index_path.exists():
        print(f"{module_name}: Skipped - index already exists at {index_path}")
        return "skipped"

    # ---- Prefer pre-extracted .txt files (e.g. M8, M9 processed by Marker) ----
    txt_dir = MODULES_DIR / module_name / "processed" / "raw_text"
    if txt_dir.exists() and list(txt_dir.glob("*.txt")):
        txt_files = sorted(txt_dir.glob("*.txt"))
        print(f"{module_name}: Loading {len(txt_files)} txt file(s) from {txt_dir} ...")
        documents = SimpleDirectoryReader(
            input_files=[str(f) for f in txt_files]
        ).load_data()

    # ---- Fall back to reading PDFs directly via books.json ----
    else:
        books_data = load_books_json()
        modules = books_data.get("modules", {})
        if module_name not in modules:
            print(f"{module_name}: Not found in books.json - skipping")
            return "failed"

        module_books = modules[module_name].get("books", [])
        pdf_paths = []
        for book in module_books:
            fname = book.get("file", "")
            if not fname or fname == "ALL_CAR_SECTIONS":
                continue
            pdf_path = BOOKS_DIR / fname
            if pdf_path.exists():
                pdf_paths.append(pdf_path)
            else:
                print(f"  WARNING: Not found: {fname}")

        if not pdf_paths:
            print(f"{module_name}: No valid PDF files found - skipping")
            return "failed"

        print(f"{module_name}: Loading {len(pdf_paths)} PDF(s) directly ...")
        documents = SimpleDirectoryReader(
            input_files=[str(p) for p in pdf_paths]
        ).load_data()

    # ---- Build and persist the index ----
    print(f"{module_name}: Building index ({len(documents)} document fragment(s)) ...")
    index = VectorStoreIndex.from_documents(documents, show_progress=True)

    index_path.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(index_path))
    print(f"{module_name}: Done ✅  →  {index_path}")
    return "done"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python build_index.py <MODULE_NAME | ALL>")
        print("  Examples:  python build_index.py M9")
        print("             python build_index.py ALL")
        sys.exit(1)

    load_env()
    configure_settings()

    target = sys.argv[1].strip().upper()

    if target == "ALL":
        books_data = load_books_json()
        all_modules = sorted(books_data.get("modules", {}).keys())
        to_build = [m for m in all_modules if m not in SKIP_MODULES]
        print(f"Building indexes for: {to_build}")
        print(f"Skipping (handled elsewhere): {sorted(SKIP_MODULES)}\n")
    else:
        to_build = [target]

    results = {"done": [], "skipped": [], "failed": []}
    for module in to_build:
        status = build_module(module)
        results[status].append(module)
        print()

    # ---- Summary ----
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"  Built   ({len(results['done'])}):   {results['done']}")
    print(f"  Skipped ({len(results['skipped'])}): {results['skipped']}")
    print(f"  Failed  ({len(results['failed'])}):  {results['failed']}")


if __name__ == "__main__":
    main()
