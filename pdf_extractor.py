"""
pdf_extractor.py  –  Extract text from PDF books using Gemini Vision API.

Usage:
    python pdf_extractor.py --pdf "path/to/book.pdf" --output "path/to/output.txt"
    python pdf_extractor.py --module M8
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import fitz  # PyMuPDF
import google.genai as genai
from google.genai import types

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"
BOOKS_JSON_PATH = PROJECT_ROOT / "data" / "books.json"
DATA_BOOKS_DIR = PROJECT_ROOT / "data" / "books"
MODULES_DIR = PROJECT_ROOT / "data" / "Modules"

# ---------------------------------------------------------------------------
# Gemini model
# ---------------------------------------------------------------------------
GEMINI_MODEL = "gemini-2.5-flash"

EXTRACT_PROMPT = (
    "Extract all text from this page exactly as it appears. "
    "Preserve structure, headings, and paragraphs. "
    "If double column read left column first then right column."
)


# ---------------------------------------------------------------------------
# .env loader  (same pattern as ingest.py)
# ---------------------------------------------------------------------------

def load_env():
    """Load variables from .env into os.environ."""
    if not ENV_PATH.exists():
        print(f"ERROR: .env not found at {ENV_PATH}")
        sys.exit(1)
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


# ---------------------------------------------------------------------------
# Key rotation
# ---------------------------------------------------------------------------

class KeyRotator:
    """
    Cycles through 13 Gemini keys then Groq index keys (GROQ_INDEX_KEY_1 … _23).
    Up to 36 keys when all env vars are set (13 Gemini + 23 Groq).
    If the full pool fails, waits 60 seconds and repeats.
    """

    GEMINI_KEYS = [f"GEMINI_API_KEY_{i}" for i in range(1, 26)]
    GROQ_KEYS = [f"GROQ_INDEX_KEY_{i}" for i in range(1, 11)]
    WAIT_SECONDS = 60

    def __init__(self):
        self.pool = [] # List of {'type': 'gemini'|'groq', 'key': '...'}
        
        # Load Gemini keys
        for name in self.GEMINI_KEYS:
            val = os.getenv(name, "").strip()
            if val:
                self.pool.append({'type': 'gemini', 'key': val})
        
        # Load Groq keys
        for name in self.GROQ_KEYS:
            val = os.getenv(name, "").strip()
            if val:
                self.pool.append({'type': 'groq', 'key': val})

        if not self.pool:
            print("ERROR: No API keys (Gemini or Groq) found in .env")
            sys.exit(1)

        print(f"Loaded {len([k for k in self.pool if k['type']=='gemini'])} Gemini keys "
              f"and {len([k for k in self.pool if k['type']=='groq'])} Groq keys.")
        
        self._index = 0
        self._setup_client()

    def _setup_client(self):
        current = self.pool[self._index]
        if current['type'] == 'gemini':
            self._client = genai.Client(api_key=current['key'])
        else:
            from groq import Groq
            self._client = Groq(api_key=current['key'])

    def rotate(self):
        """Move to the next key. Returns True if all were exhausted once."""
        self._index += 1
        if self._index >= len(self.pool):
            self._index = 0
            self._setup_client()
            return True
        
        curr = self.pool[self._index]
        print(f"  Switching to {curr['type']} key {self._index + 1} of {len(self.pool)}.")
        self._setup_client()
        return False

    def generate(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """
        Attempts to generate text using the current key.
        If it fails, rotates and tries the next.
        If all fail, waits and restarts.
        """
        while True:
            current = self.pool[self._index]
            try:
                if current['type'] == 'gemini':
                    response = self._client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=[
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                            EXTRACT_PROMPT,
                        ],
                    )
                    return response.text or ""
                else:
                    import base64
                    b64 = base64.b64encode(image_bytes).decode()
                    response = self._client.chat.completions.create(
                        model="meta-llama/llama-4-scout-17b-16e-instruct",
                        messages=[{
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{b64}"}
                                },
                                {
                                    "type": "text",
                                    "text": "Extract all text from this book page exactly as written. Return plain text only, no formatting."
                                }
                            ]
                        }],
                        max_tokens=2000
                    )
                    return response.choices[0].message.content or ""

            except Exception as exc:
                msg = str(exc)
                print(f"  {current['type'].capitalize()} key {self._index + 1} failed: {msg[:120]}")
                exhausted = self.rotate()
                if exhausted:
                    print(f"  All {len(self.pool)} keys failed. Waiting {self.WAIT_SECONDS}s before retry...")
                    time.sleep(self.WAIT_SECONDS)


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def extract_pdf_to_text(pdf_path: Path, output_txt_path: Path, rotator: KeyRotator):
    """Extract all pages of a PDF via Gemini or Groq Vision and write to output_txt_path."""
    doc = fitz.open(str(pdf_path))
    total = len(doc)
    
    # Progress tracking JSON path
    progress_path = output_txt_path.with_suffix(".json")
    page_texts_map = {} # { "1": "text...", "2": "text..." }
    
    if progress_path.exists():
        try:
            with open(progress_path, "r", encoding="utf-8") as f:
                page_texts_map = json.load(f)
            print(f"  Resuming from existing progress: {len(page_texts_map)}/{total} pages done.")
        except Exception as e:
            print(f"  WARNING: Could not load progress file: {e}. Starting fresh.")
            page_texts_map = {}

    for page_num, page in enumerate(doc, start=1):
        page_key = str(page_num)
        
        # Check if already processed
        if page_key in page_texts_map and page_texts_map[page_key].strip():
            print(f"  Skipping page {page_num}/{total} (already processed).")
            continue
            
        print(f"  Processing page {page_num}/{total}...")
        # Render page to PNG bytes at 150 DPI
        mat = fitz.Matrix(150 / 72, 150 / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")

        text = rotator.generate(img_bytes, mime_type="image/png")
        
        # Save progress immediately
        page_texts_map[page_key] = text
        try:
            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump(page_texts_map, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  WARNING: Could not save progress: {e}")

    doc.close()

    # Final assembly: Sort by page number and write .txt
    final_texts = [
        page_texts_map[str(i)] 
        for i in range(1, total + 1)
        if str(i) in page_texts_map
    ]
    
    if len(final_texts) < total:
        print(f"  ERROR: Only {len(final_texts)}/{total} pages were processed. Not writing final .txt.")
        return

    output_txt_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(final_texts))

    print(f"  Successfully finished: {output_txt_path}")
    
    # Optional: cleanup json after successful final write
    try:
        progress_path.unlink()
    except:
        pass


# ---------------------------------------------------------------------------
# Module mode helpers
# ---------------------------------------------------------------------------

def get_module_files(module_name: str):
    """Return list of (pdf_path, output_txt_path) tuples for a module."""
    module_name = module_name.strip().upper()

    try:
        with open(BOOKS_JSON_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: {BOOKS_JSON_PATH} not found.")
        sys.exit(1)

    modules = data.get("modules", {})
    if module_name not in modules:
        print(f"ERROR: Module '{module_name}' not found in data/books.json")
        sys.exit(1)

    books_list = modules[module_name].get("books", [])
    if not books_list:
        print(f"ERROR: No books listed for module {module_name}")
        sys.exit(1)

    raw_text_dir = MODULES_DIR / module_name / "processed" / "raw_text"
    pairs = []
    for book in books_list:
        fname = book.get("file", "")
        if not fname or fname == "ALL_CAR_SECTIONS":
            continue
        pdf_path = DATA_BOOKS_DIR / fname
        if not pdf_path.exists():
            print(f"  WARNING: Not found: {fname} – skipping.")
            continue
        out_path = raw_text_dir / f"{pdf_path.stem}.txt"
        pairs.append((pdf_path, out_path))

    return pairs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract text from PDF books using Gemini Vision API."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pdf", help="Path to a single PDF file.")
    group.add_argument("--module", help="Module name (e.g. M8, M10).")
    parser.add_argument(
        "--output",
        help="Output .txt path (only used with --pdf).",
    )
    args = parser.parse_args()

    # Load environment variables
    load_env()

    # Build key rotator once (shared across all files)
    rotator = KeyRotator()

    if args.pdf:
        # Single-file mode
        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            print(f"ERROR: PDF not found: {pdf_path}")
            sys.exit(1)

        if args.output:
            output_txt_path = Path(args.output)
        else:
            output_txt_path = pdf_path.with_suffix(".txt")

        if output_txt_path.exists():
            print(f"Skipping (already exists): {output_txt_path}")
            return

        print(f"\nExtracting: {pdf_path.name} → {output_txt_path}")
        extract_pdf_to_text(pdf_path, output_txt_path, rotator)
        print("\nDone.")

    else:
        # Module mode
        module_name = args.module.strip().upper()
        print(f"\n--- Extracting PDFs for module {module_name} ---")
        pairs = get_module_files(module_name)

        if not pairs:
            print("ERROR: No valid PDF files found for this module.")
            sys.exit(1)

        extracted = 0
        for pdf_path, out_path in pairs:
            if out_path.exists():
                print(f"Skipping (already exists): {out_path.name}")
                continue
            print(f"\nExtracting: {pdf_path.name} → {out_path.name}")
            try:
                extract_pdf_to_text(pdf_path, out_path, rotator)
                extracted += 1
            except Exception as e:
                print(f"  ERROR: {e}")

        print(f"\n--- Done. Extracted {extracted}/{len(pairs)} file(s). ---")


if __name__ == "__main__":
    main()
