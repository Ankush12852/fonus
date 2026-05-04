import argparse
import json
import os
import sys
from pathlib import Path
import re
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser

# LlamaIndex imports
from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq
from llama_index.core.node_parser import SentenceSplitter

# Configuration paths
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"
BOOKS_JSON_PATH = PROJECT_ROOT / "data" / "books.json"
DATA_BOOKS_DIR = PROJECT_ROOT / "data" / "books"
MODULES_DIR = PROJECT_ROOT / "data" / "Modules"
INDEXES_DIR = PROJECT_ROOT / "indexes"

def load_env():
    """Load API keys from .env into os.environ."""
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
    """Configure LlamaIndex settings matching ingest.py"""
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("ERROR: GROQ_API_KEY not found in .env")
        sys.exit(1)

    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.llm = Groq(
        model="llama-3.3-70b-versatile",
        api_key=groq_api_key,
    )
    Settings.text_splitter = SentenceSplitter(chunk_size=256, chunk_overlap=20)
    Settings.context_window = 6000
    Settings.num_output = 512


_converter = None


def get_converter():
    global _converter
    if _converter is None:
        config_parser = ConfigParser({'output_format': 'markdown'})
        _converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=create_model_dict(),
        )
    return _converter


def extract_pdf_to_text(pdf_path, output_txt_path):
    if output_txt_path.exists():
        print(f'  Skipping (already exists): {output_txt_path.name}')
        return

    converter = get_converter()
    rendered = converter(str(pdf_path))

    # Strip image references like ![](_page_0_Figure.jpeg)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', rendered.markdown)

    # Clean up extra blank lines
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    output_txt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_txt_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'  Saved: {output_txt_path}')


def process_module(module_name: str):
    """Extract and index documents using Docling and LlamaIndex."""
    module_name = module_name.strip().upper()
    print(f"Loading {module_name} books...")
    
    # 1. Read books list from data/books.json
    try:
        with open(BOOKS_JSON_PATH, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {BOOKS_JSON_PATH} not found.")
        sys.exit(1)

    modules = data.get('modules', {})
    if module_name not in modules:
        print(f"ERROR: Module {module_name} not found in data/books.json")
        sys.exit(1)

    module_data = modules[module_name]
    books_list = module_data.get('books', [])

    if not books_list:
        print(f"ERROR: No books found for module {module_name}")
        sys.exit(1)

    # Resolve target files to extract
    files_to_extract = []
    for book in books_list:
        fname = book.get('file', '')
        if fname == 'ALL_CAR_SECTIONS':
            continue
            
        fpath = DATA_BOOKS_DIR / fname
        if fpath.exists():
            files_to_extract.append(fpath)
            print(f"  Found: {fname}")
        else:
            print(f"  WARNING: Not found: {fname}")
            
    if not files_to_extract:
        print(f"ERROR: No valid existing files found to index for {module_name}")
        sys.exit(1)
        
    print(f"Found {len(files_to_extract)} files to extract")

    # 2. Extract with Docling
    raw_text_dir = MODULES_DIR / f"{module_name}" / "processed" / "raw_text"
    raw_text_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n--- Starting PDF Extraction ---")
    
    extracted_count = 0
    for fpath in files_to_extract:
        out_txt_path = raw_text_dir / f"{fpath.stem}.txt"
        print(f"Extracting: {fpath.name} -> {out_txt_path.name}")
        
        try:
            extract_pdf_to_text(fpath, out_txt_path)
            extracted_count += 1
        except Exception as e:
            print(f"  ERROR extracting {fpath.name}: {e}")
            
    print(f"Extracted {extracted_count}/{len(files_to_extract)} files to {raw_text_dir}")
    
    if extracted_count == 0:
        print("ERROR: No files successfully extracted. Aborting index step.")
        sys.exit(1)

    # 3. Build Index with LlamaIndex
    print(f"\n--- Starting LlamaIndex ingestion from extracted text ---")
    configure_settings()
    
    print(f"Loading documents from {raw_text_dir} using SimpleDirectoryReader")
    try:
        documents = SimpleDirectoryReader(input_dir=str(raw_text_dir)).load_data()
        print(f"Loaded {len(documents)} document fragments")
        
        print(f"Building VectorStoreIndex...")
        index = VectorStoreIndex.from_documents(documents, show_progress=True)
        
        index_dir = INDEXES_DIR / module_name
        index_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"Persisting index to {index_dir}")
        index.storage_context.persist(persist_dir=str(index_dir))
        
        print(f"\n{module_name} index complete")
        print(f"Files processed: {extracted_count}")
        print(f"Index saved to indexes/{module_name}/")
        
    except Exception as e:
        print(f"ERROR during indexing: {e}")
        sys.exit(1)

        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract PDFs using Docling and ingest into LlamaIndex for a module.")
    parser.add_argument("module", help="Module name (e.g. M9, M10)")
    args = parser.parse_args()
    
    load_env()
    process_module(args.module)
