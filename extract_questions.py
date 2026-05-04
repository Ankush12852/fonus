"""
Fonus — M10 Question Extractor
Scans dated papers and question banks PDFs, DOCX, and DOC files,
uses Groq to extract MCQs, saves to questions.json.
"""

import os
import sys
import json
import re
import argparse
import time
import base64
from pathlib import Path
from datetime import date

try:
    import fitz  # PyMuPDF
except ImportError:
    print("ERROR: PyMuPDF not installed. Run: pip install PyMuPDF")
    sys.exit(1)

from openai import OpenAI
from groq import Groq
import google.generativeai as genai

# --- Configuration ---
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

parser = argparse.ArgumentParser()
parser.add_argument('module', help='Module name e.g. M6, M10, ALL')
args = parser.parse_args()
MODULE = args.module.upper()

DATED_PAPERS_DIR = PROJECT_ROOT / "data" / "Modules" / MODULE / "questions" / "dated_papers"
QUESTION_BANKS_DIR = PROJECT_ROOT / "data" / "Modules" / MODULE / "questions" / "question_banks"
OUTPUT_FILE = PROJECT_ROOT / "data" / "Modules" / MODULE / "processed" / "questions.json"

GROQ_MODEL = "llama-3.3-70b-versatile"
CHUNK_SIZE = 3000
MAX_TOKENS = 2000

EXTRACTION_PROMPT = """Extract all multiple choice questions from this text.
Return ONLY a JSON array with no other text.
Each question must follow this exact format:
[
  {
    "question": "full question text here",
    "options": {
      "a": "first option",
      "b": "second option",
      "c": "third option",
      "d": "fourth option"
    },
    "correct_answer": "a or b or c or d",
    "source_file": "FILENAME",
    "topic": "topic name"
  }
]
If no MCQ questions found in this text, return []"""

# Watermark keywords to strip from PyMuPDF text
_WATERMARK_KEYWORDS = ["www.", "amequestionpaper", "Visit our website", "download", "©", "copyright"]


def clean_pdf_text(text: str) -> str:
    """
    Remove watermark lines, very short lines, and repeated blank lines
    from PyMuPDF-extracted text before sending to LLM.
    """
    lines = text.splitlines()
    cleaned = []
    prev_blank = False
    for line in lines:
        stripped = line.strip()
        # Drop lines containing watermark keywords (case-insensitive for some)
        if any(kw.lower() in stripped.lower() for kw in _WATERMARK_KEYWORDS):
            continue
        # Drop lines shorter than 4 chars (noise)
        if len(stripped) < 4:
            # But collapse consecutive blank lines to one
            if stripped == "":
                if not prev_blank:
                    cleaned.append("")
                prev_blank = True
            continue
        prev_blank = False
        cleaned.append(line)
    return "\n".join(cleaned)


class NvidiaKeyRotator:
    """
    Cycles through up to 2 NVIDIA API keys (NVIDIA_API_KEY_1, NVIDIA_API_KEY_2).
    On a 429 rate-limit error, switches to the next key automatically.
    If all keys are exhausted, waits 60 seconds then retries from key 1.
    """

    KEY_NAMES = ["NVIDIA_API_KEY_1", "NVIDIA_API_KEY_2"]
    WAIT_SECONDS = 60

    # Updated prompt: tell vision model to ignore watermarks/marks
    _OCR_PROMPT = (
        "This is a DGCA aviation exam question paper page. "
        "Ignore any watermarks, red correction marks, highlighted colours, underlines, or handwritten marks. "
        "Extract ONLY the printed MCQ questions and their 4 options A B C D. Return clean plain text only."
    )

    def __init__(self):
        self.keys = []
        for name in self.KEY_NAMES:
            val = os.getenv(name, "").strip()
            if val:
                self.keys.append(val)

        if not self.keys:
            print(
                "WARNING: No NVIDIA API keys found in .env "
                "(expected NVIDIA_API_KEY_1, NVIDIA_API_KEY_2). "
                "Scanned PDFs will be skipped."
            )
        else:
            print(f"Loaded {len(self.keys)} NVIDIA API key(s).")
        self._index = 0

    def _current_key(self):
        return self.keys[self._index] if self.keys else None

    def rotate(self):
        """Move to the next key; wait + reset if all exhausted."""
        self._index += 1
        if self._index >= len(self.keys):
            print(
                f"  All {len(self.keys)} NVIDIA keys rate-limited. "
                f"Waiting {self.WAIT_SECONDS}s before retrying..."
            )
            time.sleep(self.WAIT_SECONDS)
            self._index = 0
        else:
            print(f"  Switching to NVIDIA key {self._index + 1} of {len(self.keys)}.")

    def ocr_page(self, img_bytes: bytes) -> str:
        import base64
        from openai import OpenAI

        while True:
            key = self._current_key()
            if not key:
                return ""
                
            try:
                client = OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=key
                )
                b64 = base64.b64encode(img_bytes).decode()
                response = client.chat.completions.create(
                    model="nvidia/nemotron-nano-12b-v2-vl",
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{b64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": self._OCR_PROMPT
                            }
                        ]
                    }],
                    max_tokens=2000,
                    temperature=0.1
                )
                return response.choices[0].message.content
            except Exception as e:
                msg = str(e)
                if "429" in msg or "rate" in msg.lower() or "quota" in msg.lower():
                    print(f"  NVIDIA rate limit hit: {msg[:100]}")
                    self.rotate()
                else:
                    print(f"  NVIDIA OCR error: {msg[:100]}")
                    return ""


class LLMKeyRotator:
    """
    Cascading API key rotator for MCQ extraction.

    Priority order:
      1. GROQ_INDEX_KEY_1 … GROQ_INDEX_KEY_5   (primary index keys)
      2. GEMINI_INDEX_KEY_1 … GEMINI_INDEX_KEY_2 (primary index keys)
      3. GROQ_API_KEY                            (legacy fallback)
      4. GROQ_API_KEY_1 … GROQ_API_KEY_7        (legacy fallback)
      5. OPENAI_API_KEY                          (legacy fallback)
      6. GEMINI_API_KEY_1 … GEMINI_API_KEY_4    (legacy fallback)

    On a 429/rate-limit/quota error, advances to the next provider.
    After all keys are exhausted, waits 60 seconds then restarts.
    """

    WAIT_SECONDS = 60
    GROQ_MODEL = "llama-3.3-70b-versatile"
    OPENAI_MODEL = "gpt-4o-mini"
    GEMINI_MODEL = "models/gemini-3.1-flash-lite-preview"

    # Slot descriptors: (env_var_name, provider_type)
    _SLOT_DEFS = (
        # --- Primary index keys ---
        [(f"GROQ_INDEX_KEY_{i}", "groq") for i in range(1, 11)] +
        [(f"GEMINI_INDEX_KEY_{i}", "gemini") for i in range(1, 3)] +
        # --- Legacy fallback keys (backward compatibility) ---
        [(f"GROQ_API_KEY_{i}", "groq") for i in range(1, 11)] +
        [(f"GEMINI_API_KEY_{i}", "gemini") for i in range(1, 26)]
    )

    def __init__(self):
        # Build list of available slots (only those with non-empty env values)
        self._slots = []  # list of (key_value, provider_type, env_var_name)
        for env_name, ptype in self._SLOT_DEFS:
            val = os.getenv(env_name, "").strip()
            if val:
                self._slots.append((val, ptype, env_name))

        if not self._slots:
            print("ERROR: No LLM API keys found in .env. "
                  "Expected at least one of GROQ_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY_1.")
            sys.exit(1)

        print(f"Loaded {len(self._slots)} LLM key slot(s): "
              f"{[s[2] for s in self._slots]}")
        self._index = 0

    def _current(self):
        return self._slots[self._index]  # (key, provider, name)

    def rotate(self):
        """Advance to the next slot; if all exhausted, wait 60s and restart."""
        self._index += 1
        if self._index >= len(self._slots):
            print(
                f"  All {len(self._slots)} LLM keys exhausted. "
                f"Waiting {self.WAIT_SECONDS}s before restarting from GROQ_API_KEY..."
            )
            time.sleep(self.WAIT_SECONDS)
            self._index = 0
        else:
            _, ptype, name = self._slots[self._index]
            print(f"  Switching to {name} ({ptype}) "
                  f"[slot {self._index + 1}/{len(self._slots)}].")

    def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call the current LLM slot with the given prompts.
        Returns the response text, or raises an exception.
        """
        key, ptype, name = self._current()

        if ptype == "groq":
            client = Groq(api_key=key)
            response = client.chat.completions.create(
                model=self.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.1,
            )
            return response.choices[0].message.content.strip()

        elif ptype == "openai":
            client = OpenAI(api_key=key)
            response = client.chat.completions.create(
                model=self.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=MAX_TOKENS,
                temperature=0.1,
            )
            return response.choices[0].message.content.strip()

        elif ptype == "gemini":
            genai.configure(api_key=key)
            model = genai.GenerativeModel(self.GEMINI_MODEL)
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            response = model.generate_content(full_prompt)
            return response.text.strip()

        raise ValueError(f"Unknown provider type: {ptype}")


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


def extract_text_from_pdf(pdf_path, nvidia_rotator: NvidiaKeyRotator | None = None):
    """Extract all text from a PDF file using PyMuPDF. Fallback to NVIDIA NIM OCR if scanned."""
    try:
        doc = fitz.open(str(pdf_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        if text and text.strip():
            # Clean watermarks before returning
            return clean_pdf_text(text)
    except Exception as e:
        print(f"  WARNING: Failed to read {pdf_path.name}: {e}")
        return None

    # Fallback for scanned PDFs (no selectable text)
    if not nvidia_rotator or not nvidia_rotator.keys:
        return None

    try:
        doc = fitz.open(str(pdf_path))
        total = len(doc)
        page_texts = []
        for page_num, page in enumerate(doc, start=1):
            print(f"  NVIDIA OCR page {page_num}/{total}...")
            mat = fitz.Matrix(150 / 72, 150 / 72)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            extracted = nvidia_rotator.ocr_page(img_bytes)
            if extracted:
                page_texts.append(extracted)
        doc.close()
        combined = "\n\n".join(page_texts)
        return combined if combined.strip() else None
    except Exception as e:
        print(f"  WARNING: NVIDIA OCR failed for {pdf_path.name}: {e}")
        return None


def extract_text_from_file(file_path, nvidia_rotator=None):
    """Extract text from a PDF, DOCX, or DOC file."""
    suffix = file_path.suffix.lower()

    if suffix in ('.docx', '.doc'):
        try:
            from docx import Document
            doc = Document(str(file_path))
            text = "\n".join([
                p.text for p in doc.paragraphs
                if p.text.strip()
            ])
            return text if text.strip() else None
        except Exception as e:
            print(f"  WARNING: Failed to read {file_path.name}: {e}")
            return None

    # --- PDF path (unchanged) ---
    return extract_text_from_pdf(file_path, nvidia_rotator=nvidia_rotator)


def chunk_text(text, chunk_size=CHUNK_SIZE):
    """Split text into chunks of roughly chunk_size characters."""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks


def extract_questions_from_chunk(llm_rotator: LLMKeyRotator, chunk, filename):
    """
    Send a text chunk to the current LLM and extract MCQ questions.
    On 429 / rate-limit / quota errors, rotates to the next key in the
    cascading order: GROQ_API_KEY → GROQ_API_KEY_1..7 → OPENAI_API_KEY
    → GEMINI_API_KEY_1..4 → wait 60s → restart.
    """
    prompt = EXTRACTION_PROMPT.replace("FILENAME", filename)
    system_prompt = "You are a precise question extractor. Return ONLY valid JSON arrays."
    user_prompt = f"{prompt}\n\nTEXT:\n{chunk}"

    while True:
        try:
            raw = llm_rotator.call_llm(system_prompt, user_prompt)

            # Try to extract JSON array from the response
            # Sometimes the model wraps it in ```json ... ```
            json_match = re.search(r'\[.*\]', raw, re.DOTALL)
            if json_match:
                questions = json.loads(json_match.group())
                if isinstance(questions, list):
                    return questions
            return []

        except json.JSONDecodeError:
            _, _, name = llm_rotator._current()
            print(f"  WARNING: Invalid JSON from {name} for chunk of {filename}, skipping")
            return []
        except Exception as e:
            msg = str(e)
            if "429" in msg or "rate" in msg.lower() or "quota" in msg.lower() or "ResourceExhausted" in msg:
                _, ptype, name = llm_rotator._current()
                print(f"  Rate limit / quota hit on {name} ({ptype}): {msg[:120]}")
                llm_rotator.rotate()
            else:
                _, _, name = llm_rotator._current()
                print(f"  WARNING: LLM API error on {name} for {filename}: {e}")
                return []


def is_incomplete_question(q: dict) -> bool:
    """
    Returns True if a question is incomplete:
    - question text shorter than 8 chars, OR
    - fewer than 2 options have non-empty text
    """
    question_text = (q.get("question") or "").strip()
    if len(question_text) < 8:
        return True
    options = q.get("options") or {}
    filled = sum(1 for v in options.values() if str(v).strip())
    if filled < 2:
        return True
    return False


def repair_incomplete_question(llm_rotator: LLMKeyRotator, q: dict, module: str) -> dict | None:
    """
    Send an incomplete question to the LLM for repair.
    Returns the repaired question dict (with source='ai_repaired'), or None on failure.
    """
    question_text = (q.get("question") or "").strip()
    options = q.get("options") or {}
    non_empty_options = {k: v for k, v in options.items() if str(v).strip()}

    system_prompt = "You are a DGCA AME exam question expert. Return ONLY valid JSON."
    user_prompt = (
        f"This is an incomplete DGCA AME {module} exam question:\n"
        f"Question: {question_text}\n"
        f"Known options: {json.dumps(non_empty_options)}\n\n"
        f"Based on DGCA CAR 66 {module} syllabus, complete this MCQ question. "
        f"Keep 80% of original concept. Add missing options that are plausible but wrong, "
        f"end with final overall verification of the question.\n"
        f"Return JSON:\n"
        f'{{ "question": "...", "options": {{"a": "...", "b": "...", "c": "...", "d": "..."}}, '
        f'"correct_answer": "a or b or c or d", "topic": "..." }}'
    )

    while True:
        try:
            raw = llm_rotator.call_llm(system_prompt, user_prompt)
            # Extract JSON object from response
            json_match = re.search(r'\{.*\}', raw, re.DOTALL)
            if json_match:
                repaired = json.loads(json_match.group())
                if isinstance(repaired, dict) and repaired.get("question"):
                    repaired["source"] = "ai_repaired"
                    repaired.setdefault("source_file", q.get("source_file", ""))
                    return repaired
            return None
        except json.JSONDecodeError:
            return None
        except Exception as e:
            msg = str(e)
            if "429" in msg or "rate" in msg.lower() or "quota" in msg.lower() or "ResourceExhausted" in msg:
                _, ptype, name = llm_rotator._current()
                print(f"  Rate limit on {name} ({ptype}) during repair: {msg[:80]}")
                llm_rotator.rotate()
            else:
                print(f"  WARNING: LLM repair error: {e}")
                return None


def repair_incomplete_questions(llm_rotator: LLMKeyRotator, questions: list, module: str) -> list:
    """
    For each incomplete question in the list, attempt LLM repair.
    Returns a new list with incomplete questions replaced (or removed if repair fails).
    """
    result = []
    repaired_count = 0
    dropped_count = 0
    for q in questions:
        if is_incomplete_question(q):
            fixed = repair_incomplete_question(llm_rotator, q, module)
            if fixed:
                result.append(fixed)
                repaired_count += 1
            else:
                dropped_count += 1
        else:
            result.append(q)
    if repaired_count:
        print(f"  Repaired {repaired_count} incomplete question(s) via LLM.")
    if dropped_count:
        print(f"  Dropped {dropped_count} unrepairable incomplete question(s).")
    return result


def run_extraction_for_module(module: str):
    global DATED_PAPERS_DIR, QUESTION_BANKS_DIR, OUTPUT_FILE
    module = module.upper()
    DATED_PAPERS_DIR = PROJECT_ROOT / "data" / "Modules" / module / "questions" / "dated_papers"
    QUESTION_BANKS_DIR = PROJECT_ROOT / "data" / "Modules" / module / "questions" / "question_banks"
    OUTPUT_FILE = PROJECT_ROOT / "data" / "Modules" / module / "processed" / "questions.json"
    main()


def main():
    print("--- Fonus Question Extractor ---\n")

    # Load environment
    load_env()
    llm_rotator = LLMKeyRotator()
    nvidia_rotator = NvidiaKeyRotator()

    all_files = (
        list(DATED_PAPERS_DIR.glob("*.pdf")) +
        list(DATED_PAPERS_DIR.glob("*.docx")) +
        list(DATED_PAPERS_DIR.glob("*.doc")) +
        list(QUESTION_BANKS_DIR.glob("*.pdf")) +
        list(QUESTION_BANKS_DIR.glob("*.docx")) +
        list(QUESTION_BANKS_DIR.glob("*.doc"))
    )
    if not all_files:
        print("\nNo PDF/DOCX/DOC files found. Nothing to process.")
        return

    total_files = len(all_files)
    all_questions = []

    # Skip logic: if output already contains questions from a file, skip that file
    existing_source_files = set()
    if OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing_questions = existing.get("questions", [])
            if isinstance(existing_questions, list):
                all_questions.extend(existing_questions)
                for q in existing_questions:
                    sf = (q or {}).get("source_file")
                    if sf:
                        existing_source_files.add(sf)
        except Exception:
            pass

    print()

    # Process each file
    for idx, file_path in enumerate(all_files, 1):
        suffix = file_path.suffix.lower()
        print(f"Processing {idx}/{total_files}: {file_path.name}")

        if file_path.name in existing_source_files:
            print("  Skipped (already extracted)")
            continue

        text = extract_text_from_file(file_path, nvidia_rotator=nvidia_rotator)

        if text is None or not text.strip():
            print("  Skipped (no text extracted)")
            continue

        chunks = chunk_text(text)
        file_questions = []

        for chunk in chunks:
            questions = extract_questions_from_chunk(llm_rotator, chunk, file_path.name)
            file_questions.extend(questions)

        # Repair incomplete questions
        file_questions = repair_incomplete_questions(llm_rotator, file_questions, MODULE)

        print(f"  Extracted {len(file_questions)} questions")
        if file_questions:
            existing_source_files.add(file_path.name)
        all_questions.extend(file_questions)

    # Save output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    output = {
        "module": MODULE,
        "total_questions": len(all_questions),
        "extracted_date": str(date.today()),
        "questions": all_questions,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nDONE. Total questions extracted: {len(all_questions)}")
    print(f"Saved to: {OUTPUT_FILE.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    if MODULE == "ALL":
        modules_dir = PROJECT_ROOT / "data" / "Modules"
        for mod_dir in sorted(modules_dir.iterdir()):
            if mod_dir.is_dir():
                papers_dir = mod_dir / "questions" / "dated_papers"
                if papers_dir.exists() and list(papers_dir.glob("*.pdf")):
                    print(f"\n=== Processing {mod_dir.name} ===")
                    run_extraction_for_module(mod_dir.name)
    else:
        main()
