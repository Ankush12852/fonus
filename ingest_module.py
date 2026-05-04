import os
import re
import json
import pickle
import logging
import shutil
import argparse
from pathlib import Path

# Suppress noisy pypdf xref warnings from scanned govt PDFs
logging.getLogger("pypdf").setLevel(logging.ERROR)
logging.getLogger("pypdf._reader").setLevel(logging.ERROR)
from llama_index.core import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    StorageContext,
    Settings
)
from llama_index.core.node_parser import (
    SentenceSplitter
)
from llama_index.embeddings.huggingface import (
    HuggingFaceEmbedding
)
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.core.query_engine import RetrieverQueryEngine

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data" / "books"
MODULES_DIR = PROJECT_ROOT / "data" / "Modules"
INDEXES_DIR = PROJECT_ROOT / "indexes"
DGCA_INDEX_DIR = PROJECT_ROOT / "dgca_index_store"

# Module tag applied to all DGCA regulatory documents
DGCA_MODULE = "M10"

def init_settings():
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="BAAI/bge-small-en-v1.5"
    )
    Settings.chunk_size = 512
    Settings.chunk_overlap = 100

def extract_rule_metadata(text, filename):
    """Extract rule numbers and section info 
    from regulatory document chunks."""
    metadata = {}
    
    # Detect document type
    if "1937" in filename:
        metadata["doc_type"] = "regulation"
        metadata["doc_year"] = "1937"
        metadata["doc_name"] = "Aircraft Rules 1937"
    elif "1994" in filename:
        metadata["doc_type"] = "regulation"
        metadata["doc_year"] = "1994"
        metadata["doc_name"] = "Aircraft Rules 1994"
    elif "2003" in filename:
        metadata["doc_type"] = "regulation"
        metadata["doc_year"] = "2003"
        metadata["doc_name"] = "Aircraft Rules 2003"
    elif "2011" in filename:
        metadata["doc_type"] = "regulation"
        metadata["doc_year"] = "2011"
        metadata["doc_name"] = "Aircraft Rules 2011"
    elif "2025" in filename:
        metadata["doc_type"] = "regulation"
        metadata["doc_year"] = "2025"
        metadata["doc_name"] = "Aircraft Rules 2025"
    elif "CAR" in filename.upper():
        metadata["doc_type"] = "car_section"
        metadata["doc_name"] = filename
    elif "APM" in filename.upper():
        metadata["doc_type"] = "apm"
        metadata["doc_name"] = filename
    else:
        metadata["doc_type"] = "textbook"
        metadata["doc_name"] = filename

    # Extract rule numbers from text
    rule_matches = re.findall(
        r'Rule\s+(\d+[A-Za-z]?)', text
    )
    if rule_matches:
        metadata["rule_numbers"] = ",".join(
            set(rule_matches)
        )
        metadata["primary_rule"] = rule_matches[0]

    # Extract CAR section references
    car_matches = re.findall(
        r'CAR[-\s](\d+)', text, re.IGNORECASE
    )
    if car_matches:
        metadata["car_refs"] = ",".join(
            set(car_matches)
        )

    # Extract form numbers
    form_matches = re.findall(
        r'CA\s*Form\s*(\d+[A-Za-z]?)', 
        text, re.IGNORECASE
    )
    if form_matches:
        metadata["form_numbers"] = ",".join(
            set(form_matches)
        )

    return metadata

def is_already_indexed(module_id, files_to_index):
    """Check if module needs reindexing."""
    
    if module_id == "DGCA":
        index_dir = DGCA_INDEX_DIR
    else:
        index_dir = INDEXES_DIR / module_id
    
    # Check if index exists
    report_path = index_dir / "index_report.json"
    if not report_path.exists():
        return False
    
    # Read existing report
    with open(report_path) as f:
        report = json.load(f)
    
    # Compare file lists
    existing_files = set(report.get("files_indexed", []))
    current_files = set(files_to_index)
    
    if existing_files == current_files:
        print(f"[SKIP] {module_id} already indexed "
              f"with same files. Use --force to rebuild.")
        return True
    
    new_files = current_files - existing_files
    if new_files:
        print(f"[UPDATE] {module_id} has new files:")
        for f in new_files:
            print(f"  + {Path(f).name}")
    
    return False

def load_books_for_module(module_id, books_json):
    """Get list of book files for a module."""
    modules = books_json.get("modules", {})
    module_data = modules.get(module_id, {})
    books = module_data.get("books", [])
    return [b.get("file", "") for b in books]

def ingest_module(module_id, force=False):
    """Build index for a single module."""
    print(f"\n{'='*50}")
    print(f"Indexing {module_id}...")
    print(f"{'='*50}")

    init_settings()

    # Load books.json
    books_json_path = DATA_DIR.parent / "books.json"
    with open(books_json_path, "r", 
              encoding="utf-8") as f:
        books_json = json.load(f)

    # Get files for this module
    book_files = load_books_for_module(
        module_id, books_json
    )

    if not book_files:
        print(f"No books found for {module_id}")
        return False

    # Collect all files to index
    files_to_index = []
    
    for book_file in book_files:
        # Check data/books/ first
        book_path = DATA_DIR / book_file
        if book_path.exists():
            files_to_index.append(str(book_path))
            print(f"  [OK] Found: {book_file}")
        else:
            # Check for .txt version
            txt_name = Path(book_file).stem + ".txt"
            txt_path = DATA_DIR / txt_name
            if txt_path.exists():
                files_to_index.append(str(txt_path))
                print(f"  [OK] Found TXT: {txt_name}")
            else:
                print(f"  [X] Missing: {book_file}")

    # Also add PYQ files from data/Modules/
    module_questions_dir = (
        MODULES_DIR / module_id / "questions"
    )
    if module_questions_dir.exists():
        pyq_files = list(
            module_questions_dir.glob("*.pdf")
        ) + list(
            module_questions_dir.glob("*.docx")
        ) + list(
            module_questions_dir.glob("*.txt")
        )
        for pyq in pyq_files:
            files_to_index.append(str(pyq))
            print(f"  [OK] PYQ: {pyq.name}")

    if not files_to_index:
        print(f"No files found to index for {module_id}")
        return False

    # Check if already indexed
    if not force and is_already_indexed(
        module_id, files_to_index
    ):
        return True

    print(f"\nTotal files to index: {len(files_to_index)}")

    # Load documents
    print("Loading documents...")
    try:
        reader = SimpleDirectoryReader(
            input_files=files_to_index,
            filename_as_id=True
        )
        documents = reader.load_data()
        print(f"Loaded {len(documents)} document pages")
    except Exception as e:
        print(f"Error loading documents: {e}")
        return False

    # Add metadata to each document
    for doc in documents:
        filename = doc.metadata.get(
            "file_name", ""
        )
        extra_meta = extract_rule_metadata(
            doc.text, filename
        )
        doc.metadata.update(extra_meta)
        doc.metadata["module"] = module_id

    # Parse into nodes with better chunking
    print("Chunking documents...")
    splitter = SentenceSplitter(
        chunk_size=512,
        chunk_overlap=100,
        paragraph_separator="\n\n",
        secondary_chunking_regex=r"Rule\s+\d+"
    )
    nodes = splitter.get_nodes_from_documents(
        documents
    )
    print(f"Created {len(nodes)} chunks")

    # Add metadata to nodes
    for node in nodes:
        extra_meta = extract_rule_metadata(
            node.text,
            node.metadata.get("file_name", "")
        )
        node.metadata.update(extra_meta)

    # Build index
    print("Building vector index...")
    try:
        index = VectorStoreIndex(
            nodes,
            show_progress=True
        )
    except Exception as e:
        print(f"Error building index: {e}")
        return False

    # Save index
    output_dir = INDEXES_DIR / module_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    storage_context = index.storage_context
    storage_context.persist(
        persist_dir=str(output_dir)
    )
    
    print(f"[OK] Index saved to indexes/{module_id}/")

    # Also save nodes for BM25 retriever
    bm25_path = output_dir / "bm25_nodes.pkl"
    with open(bm25_path, "wb") as f:
        pickle.dump(nodes, f)
    print(f"[OK] BM25 nodes saved")

    # Save index report
    report = {
        "module": module_id,
        "files_indexed": files_to_index,
        "total_pages": len(documents),
        "total_chunks": len(nodes),
        "chunk_size": 512,
        "chunk_overlap": 100
    }
    report_path = output_dir / "index_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"[OK] Report saved")
    return True

def ingest_dgca_store(force=False):
    """Rebuild the dgca_index_store with 
    better chunking and metadata."""
    print(f"\n{'='*50}")
    print("Rebuilding DGCA Index Store...")
    print(f"{'='*50}")

    init_settings()

    print(f"DATA_DIR: {DATA_DIR}")
    print(f"DATA_DIR exists: {DATA_DIR.exists()}")
    print(f"Files in DATA_DIR: {len(list(DATA_DIR.glob('*')))}")

    # Find all DGCA regulatory files
    dgca_files = []
    seen = set()
    
    # Search in data/books/ for regulatory docs
    regulatory_patterns = [
        # Aircraft Rules by year
        "*1937*", "*1994*", "*2003*", "*2011*",
        # 2025 rules — targeted prefixes to avoid false positives
        "DGCA_*2025*", "RTR*2025*", "AAC*2025*", "APM*2025*",
        # CAR sections and APM
        "CAR_*", "APM_*",
        # DGCA-prefixed documents
        "DGCA_*",
        # Advisory circulars and handbooks
        "AAC*", "AD AC*", "ADVISORY*",
        "Handbook of Procedures*", "AIR SAFETY*",
        "Aircraft Engineering*", "Aerodrome Advisory*",
        "AC_65*", "Principles of Flight*", "RTR*"
    ]
    
    for pattern in regulatory_patterns:
        found = list(DATA_DIR.glob(pattern))
        for f in found:
            if f.suffix.lower() in ['.pdf', '.txt']:
                if str(f) not in seen:
                    seen.add(str(f))
                    dgca_files.append(str(f))
                    print(f"  [OK] Added: {f.name}")

    print(f"\nTotal DGCA files: {len(dgca_files)}")

    if not dgca_files:
        print("No DGCA files found")
        return False

    # Check if already indexed
    if not force and is_already_indexed(
        "DGCA", dgca_files
    ):
        return True

    # Load documents
    reader = SimpleDirectoryReader(
        input_files=dgca_files,
        filename_as_id=True
    )
    documents = reader.load_data()
    print(f"Loaded {len(documents)} pages")

    # Add regulatory metadata
    for doc in documents:
        filename = doc.metadata.get("file_name","")
        extra_meta = extract_rule_metadata(
            doc.text, filename
        )
        doc.metadata.update(extra_meta)
        doc.metadata["module"] = DGCA_MODULE
        doc.metadata["index_type"] = "dgca_regulatory"

    # Use smaller chunks for regulatory docs
    # so rule boundaries are preserved better
    splitter = SentenceSplitter(
        chunk_size=384,
        chunk_overlap=128,
        paragraph_separator="\n\n",
        secondary_chunking_regex=r"Rule\s+\d+"
    )
    nodes = splitter.get_nodes_from_documents(
        documents
    )
    
    # Add metadata to nodes
    for node in nodes:
        extra_meta = extract_rule_metadata(
            node.text,
            node.metadata.get("file_name", "")
        )
        node.metadata.update(extra_meta)

    print(f"Created {len(nodes)} regulatory chunks")

    # Build index
    index = VectorStoreIndex(
        nodes, show_progress=True
    )

    # Save — overwrite existing dgca_index_store
    DGCA_INDEX_DIR.mkdir(
        parents=True, exist_ok=True
    )
    index.storage_context.persist(
        persist_dir=str(DGCA_INDEX_DIR)
    )

    print(f"[OK] DGCA index saved to dgca_index_store/")

    # Also save nodes for BM25 retriever
    # Backup existing pkl before overwriting
    bm25_path = DGCA_INDEX_DIR / "bm25_nodes.pkl"
    bm25_backup = DGCA_INDEX_DIR / "bm25_nodes.pkl.bak"
    if bm25_path.exists():
        shutil.copy2(bm25_path, bm25_backup)
    with open(bm25_path, "wb") as f:
        pickle.dump(nodes, f)
    print(f"[OK] DGCA BM25 nodes saved")
    
    # Save indexed files list
    indexed_list = [
        Path(f).name for f in dgca_files
    ]
    with open(
        DGCA_INDEX_DIR / "indexed_files.txt", 
        "w"
    ) as f:
        f.write("\n".join(indexed_list))

    # Save index report
    report = {
        "module": "DGCA",
        "files_indexed": dgca_files,
        "total_pages": len(documents),
        "total_chunks": len(nodes),
        "chunk_size": 384,
        "chunk_overlap": 128
    }
    report_path = DGCA_INDEX_DIR / "index_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return True

def ingest_all(force=False):
    """Index all modules + rebuild dgca store."""
    modules = [
        "M1", "M2", "M3", "M4", "M5",
        "M6", "M7A", "M7B", "M8", "M9",
        "M11A", "M11B", "M11C", "M12",
        "M13", "M14", "M15", "M16",
        "M17A", "M17B"
    ]
    
    results = {}
    
    # Rebuild DGCA store first
    print("\n[1/2] Rebuilding DGCA Index Store")
    dgca_ok = ingest_dgca_store(force=force)
    results["dgca_index_store"] = dgca_ok
    
    # Then all modules
    print(f"\n[2/2] Indexing {len(modules)} modules")
    for i, module in enumerate(modules):
        print(f"\n[{i+1}/{len(modules)}] {module}")
        ok = ingest_module(module, force=force)
        results[module] = ok
    
    # Final report
    print(f"\n{'='*50}")
    print("FINAL INDEXING REPORT")
    print(f"{'='*50}")
    success = [k for k,v in results.items() if v]
    failed = [k for k,v in results.items() if not v]
    print(f"[OK] Success ({len(success)}): {success}")
    print(f"[X] Failed ({len(failed)}): {failed}")
    print(f"{'='*50}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "module",
        nargs="?",
        help="Module to index or 'all' or 'dgca'"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if already indexed"
    )
    args = parser.parse_args()

    if not args.module or args.module == "all":
        ingest_all(force=args.force)
    elif args.module == "dgca":
        ingest_dgca_store(force=args.force)
    else:
        ingest_module(
            args.module.upper(), 
            force=args.force
        )
