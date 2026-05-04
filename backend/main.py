# -*- coding: utf-8 -*-
import os
import json
import sys
from pathlib import Path
from datetime import date
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, Header, status, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Rate Limiting (SlowAPI) ───────────────────────────────────────────────────
# SlowAPI lets us limit how many requests a single IP can make per minute.
# This is a second layer of protection on top of Nginx rate limiting.
# Install with: pip install slowapi
# ─────────────────────────────────────────────────────────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    _SLOWAPI_AVAILABLE = True
except ImportError:
    _SLOWAPI_AVAILABLE = False
    print("[WARNING] slowapi not installed — API rate limiting disabled.")
    print("[WARNING] Run: pip install slowapi  to enable it.")
from supabase import create_client, Client
from passlib.context import CryptContext

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import re
import pickle
from llama_index.core import StorageContext, load_index_from_storage, Settings, PromptTemplate
try:
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
except ImportError:
    HuggingFaceEmbedding = None
    print("Warning: HuggingFaceEmbedding not available - using default")
from llama_index.llms.groq import Groq
from llama_index.core.node_parser import SentenceSplitter
from llama_index.retrievers.bm25 import (
    BM25Retriever
)
from llama_index.core.retrievers import (
    QueryFusionRetriever
)
from llama_index.core.query_engine import (
    RetrieverQueryEngine
)

# Import our custom modules
from config.pricing import PRICING_CONFIG
from backend.storage_config import get_pdf_url

import json, os

# ── GROUND TRUTH LAYER ─────────────────────────────────────────────────────
# Loaded once at startup from verified data files.
# These facts NEVER go through LLM retrieval — they are returned directly.

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
if not os.path.exists(os.path.join(_DATA_DIR, "books.json")):
    # Try one level up — fonus/data/
    _DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
    _DATA_DIR = os.path.normpath(_DATA_DIR)

print(f"[Ground Truth] Loading data from: {_DATA_DIR}")
print(f"[Ground Truth] books.json found: {os.path.exists(os.path.join(_DATA_DIR, 'books.json'))}")

def _load_json(filename):
    path = os.path.join(_DATA_DIR, filename)
    print(f"[_load_json] Trying: {path} | exists: {os.path.exists(path)}")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[_load_json] {filename} loaded OK — type={type(data).__name__} | keys={list(data.keys())[:5]}")
            return data
        except Exception as e:
            print(f"[_load_json] ERROR loading {filename}: {e}")
            return {}
    print(f"[_load_json] FILE NOT FOUND: {path}")
    return {}

BOOKS_DATA = _load_json("books.json")
SYLLABUS_DATA = _load_json("exam_syllabus.json")
print(f"[Ground Truth] exam_syllabus.json loaded {len(SYLLABUS_DATA)} modules: {list(SYLLABUS_DATA.keys())}")

def get_exam_facts(module_key: str, stream: str) -> dict | None:
    """
    Returns verified exam facts for a module+stream combination.
    Returns None if not found — caller must NOT guess.
    """
    mod = BOOKS_DATA.get("modules", {}).get(module_key)
    if not mod:
        return None
    if not mod.get("exam_applicable", True):
        return {
            "exam_applicable": False,
            "note": mod.get("note", "Not applicable for examination per CAR 66.")
        }
    # Resolve stream key — B1.1/B1.2/B1.3/B1.4 all map to "B1" for shared counts
    q_by_stream = mod.get("questions_by_stream", {})
    d_by_stream = mod.get("duration_mins_by_stream", {})
    # Try exact stream first, then prefix match
    q_count = q_by_stream.get(stream) or q_by_stream.get(stream.split(".")[0])
    duration = d_by_stream.get(stream) or d_by_stream.get(stream.split(".")[0])
    if q_count is None:
        return None
    topics = SYLLABUS_DATA.get(module_key, {}).get("topics", {})
    print(f"[GT TOPICS] module_key={module_key} | SYLLABUS_DATA keys={list(SYLLABUS_DATA.keys())} | topics found={len(topics)}")
    exam_rules = BOOKS_DATA.get("exam_rules", {})
    return {
        "module": module_key,
        "name": mod["name"],
        "stream": stream,
        "questions": q_count,
        "duration_mins": duration,
        "pass_mark": exam_rules.get("pass_mark_percent", 75),
        "time_per_question_sec": exam_rules.get("time_per_question_seconds", 75),
        "question_type": exam_rules.get("question_type", "multiple_choice_4_options"),
        "topics": topics,
        "exam_applicable": True
    }


SYLLABUS_TRIGGER_WORDS = [
    "how many question", "number of question", "total question",
    "syllabus", "topics for", "topic list", "what topics",
    "how long", "duration", "exam time", "time for exam",
    "passing mark", "pass mark", "pass percentage",
    "how many marks", "what is the format",
    "exam pattern", "question pattern", "retake", "attempt",
    "when can i retake", "next attempt"
]

NOTE_TRIGGER_WORDS = [
    "create note", "make note", "write note",
    "detailed note", "revision note", "study note",
    "revise", "recap", "summarise", "summarize",
    "give me a summary", "quick summary",
    "prepare me", "help me revise", "revision material",
    "key points", "important points", "cheat sheet"
]

DRILL_TRIGGER_WORDS = [
    "drill me", "drill", "test me", "quiz me",
    "give me questions", "give me 5 questions",
    "practice questions", "test my knowledge",
    "ask me questions", "question me",
    "ya sure", "yes sure", "sure", "yes", "ok lets go",
    "lets go", "start", "begin", "go ahead",
    "drill me again", "5 more", "next 5", "more questions"
]

STUDY_PLAN_TRIGGER_WORDS = [
    "guide me", "how to start", "where to start",
    "study plan", "30 days", "20 days", "15 days",
    "10 days", "days left", "weeks left", "how should i",
    "what should i", "failed", "how to prepare",
    "preparation plan", "exam plan", "i have", "days to",
    "help me prepare", "i failed", "got failed"
]

PYQ_TRIGGER_WORDS = [
    "previous year", "past question", "pyq",
    "repeated question", "most repeated", "frequently asked",
    "comes in exam", "asked in exam", "exam question",
    "last 5 year", "last year question", "previous paper",
    "what type of question", "practice question"
]

CHAT_TRIGGER_WORDS = [
    "hi", "hello", "hey", "thanks", "thank you",
    "ok", "okay", "got it", "understood", "great",
    "good", "nice", "cool", "sure", "alright",
    "bye", "see you", "later"
]

# Longer greetings / venting-style openers (do not rely on tiny word-count only).
CONVERSATIONAL_OPENERS = [
    "good morning", "good evening", "good afternoon", "good night",
    "thank you so", "thanks a lot",
]

# Explicit non-CAR66 smalltalk cues — route early to conversational mentor tone.
OFF_TOPIC_TRIGGERS = [
    "bake a", " bake ", "baking ", "cake", "brownie", "cookie",
    "recipe for", "cooking ", "restaurant ", "chef ",
    "bollywood", "cricket score", "ipl ", "movies to watch",
    "dating ", "tiktok dance", "fortnite", "crypto investment",
]


def suggests_non_aviation_smalltalk(question: str) -> bool:
    q = question.lower().strip()
    return any(t in q for t in OFF_TOPIC_TRIGGERS)


def has_car66_study_signals(question: str) -> bool:
    """Cheap lexical filter — not exhaustive; complements retrieval alignment."""
    ql = question.lower()
    needles = (
        "aircraft", "aeroplane", "airplane", "helicopter", "rotor", "fuselage",
        "wing ", "rudder ", "elevator", "landing gear", "engine", "turbine",
        " piston", "propeller", "hydraulic", "fuel", "avi", "icao", "faa",
        "dgca", "car 66", "car66", "ame ", "exam", "module ", " syllabus",
        "pyq", "regulation", "car section", "maintenance", "inspection",
        "mel ", "cmm ", "ad ", "sb ", "rivet", "corrosion", "fatigue",
        "torque", "bearing", "fastener", "bolt", "nut ", "wire ", "avionics",
    )
    return any(n in ql for n in needles)


def is_syllabus_question(question: str) -> bool:
    q = question.lower()
    return any(trigger in q for trigger in SYLLABUS_TRIGGER_WORDS)

def is_note_request(question: str) -> bool:
    q = question.lower().strip()
    # Direct match
    if any(trigger in q for trigger in NOTE_TRIGGER_WORDS):
        return True
    # Common misspellings and variants
    note_variants = [
        "summery", "sumary", "summar", "notee", "nots",
        "breif", "breaf", "bref", "overvew", "overviw",
        "recape", "recaap", "revise", "revsion", "revcap"
    ]
    return any(variant in q for variant in note_variants)

def is_drill_request(question: str) -> bool:
    q = question.lower().strip()
    # Direct drill commands always trigger
    direct_triggers = [
        "drill me", "drill", "test me", "quiz me", "ya",
        "give me questions", "practice questions",
        "drill me again", "5 more", "next 5"
    ]
    if any(trigger in q for trigger in direct_triggers):
        return True
    return False

def is_study_plan_request(question: str) -> bool:
    q = question.lower().strip()
    return any(trigger in q for trigger in STUDY_PLAN_TRIGGER_WORDS)

def is_pyq_request(question: str) -> bool:
    q = question.lower().strip()
    return any(trigger in q for trigger in PYQ_TRIGGER_WORDS)

def is_chat_message(question: str) -> bool:
    q = question.lower().strip()
    # Pure chat: short AND matches trigger word
    if len(q.split()) <= 4 and any(trigger in q for trigger in CHAT_TRIGGER_WORDS):
        return True
    if len(q.split()) <= 12 and any(phrase in q for phrase in CONVERSATIONAL_OPENERS):
        return True
    return False


def classify_intent(question: str) -> str:
    """
    Returns one of: SYLLABUS | NOTE | PYQ | CHAT | CONCEPT
    Order matters — more specific checks first.
    """
    if is_syllabus_question(question):
        return "SYLLABUS"
    if is_study_plan_request(question):
        return "STUDY_PLAN"
    if is_drill_request(question):
        return "DRILL"
    if is_note_request(question):
        return "NOTE"
    if is_pyq_request(question):
        return "PYQ"
    if suggests_non_aviation_smalltalk(question):
        return "CHAT"
    if is_chat_message(question):
        return "CHAT"
    return "CONCEPT"

def format_ground_truth_answer(facts: dict, student_name: str = "") -> str:
    """Format verified exam facts into a clean mentor-style response."""
    name = f"{student_name}, " if student_name else ""
    if not facts.get("exam_applicable"):
        return (
            f"{name}M1 and M2 are not examined per CAR 66 Issue III Rev 2. "
            "Knowledge is required but DGCA does not conduct a written exam for these modules."
        )
    topics = facts.get("topics", {})
    topic_lines = []
    for tid, tdata in topics.items():
        tname = tdata.get("name", "")
        # Get level for this stream
        level = (
            tdata.get("level_B1") or
            tdata.get("level_B2") or
            tdata.get("level_ALL") or
            tdata.get("level_A") or 0
        )
        level_label = {1: "L1 — awareness", 2: "L2 — working knowledge", 3: "L3 — detailed"}.get(level, f"L{level}")
        topic_lines.append(f"  {tid}. {tname} — {level_label}")
    topic_block = "\n".join(topic_lines) if topic_lines else "  (topic breakdown not available)"
    return (
        f"{name}here are the verified exam facts for {facts['name']} ({facts['stream']}) "
        f"from CAR 66 Issue III Rev 2:\n\n"
        f"Questions: {facts['questions']} MCQs (4 options each)\n"
        f"Duration: {facts['duration_mins']} minutes "
        f"({facts['time_per_question_sec']} sec per question)\n"
        f"Pass mark: {facts['pass_mark']}%\n\n"
        f"Syllabus topics:\n{topic_block}\n\n"
        f"Source: CAR 66 Issue III Rev 2 — 29 Sept 2025 (verified)"
    )
# ── END GROUND TRUTH LAYER ─────────────────────────────────────────────────

M10_DOCUMENT_REGISTRY = """
FONUS M10 VERIFIED DATABASE CONTAINS:
Aircraft Rules:
- DGCA Aircraft Rules 1937 (complete)
- DGCA Aircraft Rules 1994 (complete)
- DGCA Aircraft Rules 2003 (complete)
- DGCA Aircraft Rules 2011 (complete)
- DGCA Aircraft Rules 2025 (complete)
- RTR Rules 2025

CAR Sections (all sections 1-11):
- CAR Section 1 through Section 11
- All Series and Parts indexed

APM Documents:
- APM Part 0 Issue 2 Rev 9 March 2017
- APM Part II Chapter 2 Issue 2 Rev 10 April 2025

Advisory Circulars:
- AAC 02, 03, 04 of 2023
- AAC 03, 2 of 2025
- AAC 1 of 2026
- AAC 5 of 2020
- AD AC 01, 07 of 2017
- Aircraft Engineering Advisory Circular 2024
- Air Safety Training Manual
- Multiple Handbook of Procedures (01-18)

IMPORTANT RULE FOR USING THIS REGISTRY:
When a student asks about a specific rule number
from any of the above documents:
1. Search the indexed content first
2. If the exact rule is NOT found in retrieved chunks:
   - Do NOT say "not confirmed"
   - Instead say: "I have [document name] indexed.
     Rule [X] does not appear in the retrieved 
     sections. This rule may not exist in this 
     version, or it may be in a section not 
     retrieved. Verify the complete document at 
     dgca.gov.in"
3. NEVER ask permission when you know the 
   document exists in your database.
   Either answer from it OR confirm it's 
   not found in that specific document.
"""

def load_env():
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def init_settings():
    try:
        embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-en-v1.5"
        )
    except:
        embed_model = None

    if embed_model:
        Settings.embed_model = embed_model
    Settings.llm = Groq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
    )


def _collect_groq_keys() -> List[str]:
    """Unique keys in order: GROQ_API_KEY_1..30, GROQ_CHAT_KEY_1..30, then legacy keys."""
    keys: List[str] = []
    for prefix in ("GROQ_API_KEY", "GROQ_CHAT_KEY"):
        for i in range(1, 31):
            k = os.getenv(f"{prefix}_{i}")
            if k and k not in keys:
                keys.append(k)
    for leg in (os.getenv("GROQ_API_KEY"), os.getenv("GROQ_CHAT_KEY")):
        if leg and leg not in keys:
            keys.append(leg)
    return keys


def _is_rate_limit_error(exc: BaseException) -> bool:
    s = str(exc).lower()
    if "429" in s or "rate limit" in s or "rate_limit" in s or "too many requests" in s:
        return True
    try:
        from openai import RateLimitError

        if isinstance(exc, RateLimitError):
            return True
    except ImportError:
        pass
    return False


def iter_completion_llms(preferred: str = "auto"):
    """
    Yields (llm, label) for each configured Groq key, then Gemini.
    No startup ping — TPD limits often appear only on real completions.
    """
    for key in _collect_groq_keys():
        yield (
            Groq(
                model="llama-3.3-70b-versatile",
                api_key=key,
                max_tokens=400,
                timeout=90,
                temperature=0.1,
            ),
            "Groq (Llama 3.3 70B)",
        )

    gemini_chat_keys = [os.getenv(f"GEMINI_CHAT_KEY_{i}", "") for i in range(1, 5)]
    gemini_chat_keys = [k for k in gemini_chat_keys if k]
    gemini_key = gemini_chat_keys[0] if gemini_chat_keys else (
        os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    )

    if gemini_key:
        from llama_index.llms.google_genai import GoogleGenAI

        print("[LLM] Offering Gemini fallback in rotation chain")
        yield GoogleGenAI(
            model="models/gemini-2.0-flash",
            api_key=gemini_key,
            max_tokens=400,
        ), "Gemini 2.0 Flash"


def get_llm_for_request(preferred: str = "auto"):
    """First configured LLM (lightweight callers — chat intent, compact, etc.)."""
    for llm, label in iter_completion_llms(preferred):
        return llm, label
    raise Exception("All LLM keys exhausted — set GROQ_API_KEY or GEMINI_API_KEY")


def llm_complete_with_rotation(prompt: str, preferred: str = "auto") -> tuple[str, str]:
    """Run a single completion; rotate through Groq keys + Gemini on rate limits."""
    last_err: Optional[BaseException] = None
    for llm_try, label_try in iter_completion_llms(preferred):
        try:
            return llm_try.complete(prompt).text, label_try
        except Exception as exc:
            last_err = exc
            if _is_rate_limit_error(exc):
                print(
                    f"[LLM rotate] {label_try} rate limited "
                    f"(short prompt): {str(exc)[:100]}"
                )
                continue
            raise
    detail = (
        "All AI providers are rate-limited or unavailable. "
        "Wait and retry, add another Groq org key, or set GEMINI_API_KEY."
    )
    if last_err:
        detail += f" Last error: {str(last_err)[:200]}"
    raise HTTPException(status_code=503, detail=detail)


USAGE_COUNT_FIELDS = (
    "questions_asked",
    "chat_questions",
    "message_count",
    "query_count",
    "count",
)


def _usage_count_from_row(row: dict) -> int:
    for k in USAGE_COUNT_FIELDS:
        if k in row and row[k] is not None:
            try:
                return int(row[k])
            except (TypeError, ValueError):
                return 0
    return 0


def _usage_field_from_row(row: dict) -> Optional[str]:
    for k in USAGE_COUNT_FIELDS:
        if k in row:
            return k
    return None


def _daily_usage_set_count(
    supabase: Client,
    user_id: str,
    today: str,
    next_count: int,
    existing_row: Optional[dict] = None,
) -> None:
    """Update or insert daily usage count; adapts to whichever count column exists."""
    field = _usage_field_from_row(existing_row) if existing_row else "questions_asked"
    payload = {field: next_count}
    if existing_row:
        supabase.table("daily_usage").update(payload).eq("user_id", user_id).eq("date", today).execute()
        return
    ins = {"user_id": user_id, "date": today, field: next_count}
    try:
        supabase.table("daily_usage").insert(ins).execute()
    except Exception as e1:
        err = str(e1).lower()
        if "could not find" in err or "pgrst204" in err or "schema cache" in err:
            for alt in ("chat_questions", "message_count", "query_count", "count"):
                try:
                    supabase.table("daily_usage").insert(
                        {"user_id": user_id, "date": today, alt: next_count}
                    ).execute()
                    return
                except Exception:
                    continue
        raise



def load_all_indexes():
    indexes = {}
    # M10
    m10_path = PROJECT_ROOT / "dgca_index_store"
    if m10_path.exists():
        try:
            sc = StorageContext.from_defaults(persist_dir=str(m10_path))
            indexes["M10"] = load_index_from_storage(sc)
        except Exception as e:
            print(f"Warning: Could not load index: {e}")
            indexes["M10"] = None
    # All other modules
    indexes_dir = PROJECT_ROOT / "indexes"
    if indexes_dir.exists():
        for module_dir in indexes_dir.iterdir():
            if module_dir.is_dir():
                try:
                    sc = StorageContext.from_defaults(
                        persist_dir=str(module_dir)
                    )
                    indexes[module_dir.name] = load_index_from_storage(sc)
                    print(f"Loaded index: {module_dir.name}")
                except Exception as e:
                    print(f"Warning: Could not load index: {e}")
                    indexes[module_dir.name] = None
    return indexes


def detect_module(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["bernoulli","lift","drag","airfoil","aerodyn","wing","stall","stability","vortex","glide"]):
        return "M8"
    if any(w in q for w in ["human factor","situational awareness","fatigue","stress","error","complacency","workload"]):
        return "M9"
    if any(w in q for w in ["turbine","gas turbine","compressor","combustion","thrust","jet engine","bypass"]):
        return "M15"
    if any(w in q for w in ["piston","reciprocating","cylinder","carburetor","magneto","crankshaft"]):
        return "M16"
    if any(w in q for w in ["electrical","voltage","current","resistance","ohm","circuit","transformer","generator","battery"]):
        return "M3"
    if any(w in q for w in ["electronic","transistor","diode","amplifier","semiconductor"]):
        return "M4"
    if any(w in q for w in ["digital","binary","logic gate","microprocessor","data bus","computer"]):
        return "M5"
    if any(w in q for w in ["material","alloy","metal","composite","corrosion","fastener","rivet","bolt"]):
        return "M6"
    if any(w in q for w in ["maintenance","inspection","tooling","safety","ppe","workshop","repair","overhaul"]):
        return "M7A"
    if any(w in q for w in ["propeller","blade","pitch","governor","feather","constant speed"]):
        return "M17A"
    if any(w in q for w in ["helicopter","rotor","autorotation","hover"]):
        return "M12"
    if any(w in q for w in ["car 66","license","licence","car 145","airworthiness","dgca","form","certificate","regulation"]):
        return "M10"
    # Log undetected questions for improvement
    print(f"[detect_module] No match found for: {question[:80]}")
    return "M7A"  # Maintenance Practices is the safest general fallback


# High-precision (phrase → CAR module) for scope mismatch: student picked module A in the UI
# but the question clearly belongs in syllabus module B. Longer phrases are matched first.
# Extend here when benchmarks show cross-module retrieval traps — prefer multi-word phrases.
SCOPE_TARGET_PHRASES: list[tuple[str, str]] = [
    ("compressor surge", "M15"),
    ("shell model", "M9"),
    ("shell interface", "M9"),
    ("james reason", "M9"),
    ("reason model", "M9"),
    ("peame", "M9"),
    ("hfacs", "M9"),
    ("dirty dozen", "M9"),
    ("arinc 664", "M5"),
    ("arinc 429", "M5"),
    ("afdx", "M5"),
    ("ground resonance", "M12"),
    ("autorotation", "M12"),
    ("retreating blade", "M12"),
    ("dissymmetry of lift", "M12"),
    ("engine seizure", "M16"),
    ("magneto timing", "M16"),
    ("propeller feather", "M17A"),
    ("constant speed propeller", "M17A"),
    ("permit to work", "M7A"),
    ("lock out tag out", "M7A"),
    ("explosive safety", "M7A"),
]


def resolve_explicit_scope_target(question: str) -> Optional[str]:
    """Return a syllabus module if the question contains an unambiguous phrase route."""
    q = (question or "").lower()
    if not q.strip():
        return None
    for phrase, mod in sorted(SCOPE_TARGET_PHRASES, key=lambda x: -len(x[0])):
        if phrase in q:
            return mod
    return None


def expand_query(question: str) -> str:
    q = question.lower()
    expanded = question
    
    helicopter_terms = {
        'dissymmetry': 'dissymmetry of lift helicopter rotor blade advancing retreating',
        'autorotation': 'autorotation helicopter rotor engine failure descent',
        'washout': 'washout rotor blade angle incidence tip root',
        'ground resonance': 'ground resonance helicopter rotor vibration landing gear',
        'tail rotor': 'tail rotor anti-torque yaw control helicopter'
    }
    
    for term, expansion in helicopter_terms.items():
        if term in q:
            expanded = f"{expanded} {expansion}"
            
    form_match = re.search(r'ca[\s-]?form[\s-]?(\d+)|ca[\s-]?(\d+)', q)
    if form_match:
        num = form_match.group(1) or form_match.group(2)
        expanded = f"{expanded} CA-{num} application form registration certificate"
    else:
        rule_match = re.search(r'rule[\s-]?(\d+\w*)', q)
        if rule_match:
            num = rule_match.group(1)
            expanded = f"{expanded} Aircraft Rules rule {num} regulation"
    return expanded



MASTER_SYSTEM_PROMPT = """
You are Fonus — DGCA CAR 66 AME exam mentor for Indian aviation students.
You are not a chatbot. You are the smartest, most experienced AME senior
the student has ever learned from. You know their name. You know their module.
You speak with authority, warmth, and zero fluff.

Student: {STUDENT_NAME} | Module: {MODULE_NAME} | Stream: {STREAM}

━━━ WHAT FONUS IS (PRODUCT TRUTH) ━━━
- Fonus is a **CAR 66 exam preparation mentor** — not DGCA itself, not a lawyer, not a formal legal ruling. Never imply the app replaces official publications or dgca.gov.in for binding text.
- Be **professionally confident** on syllabus concepts, mechanisms, exam-style reasoning, and maintenance judgement — that is the “smart mentor” students feel on day one.
- Be **precisely careful** on exact regulatory numbers, form IDs, and rule citations: use verified retrieval when present; otherwise teach the concept and point to official verification (dgca.gov.in / CAR PDFs) without sounding robotic.
- **Exam Focus** is a study anchor for how DGCA asks questions — keep it (see EXAM FOCUS below). It is not a claim of government authority.
- Hybrid behaviour: **sources and citations when the material supports them**; **natural explanation and intent-following** always. Never trade fluent teaching for invented facts.

━━━ HOW YOU SPEAK ━━━
- Address the student by first name naturally — not in every sentence, 
  but where it feels right. Like a mentor, not a robot.
- Never start with "Great question!" or "Certainly!" or "Of course!"
- Never say "Based on the context" or "According to the provided information"
- Start every answer with the actual answer. No intro sentences.
- Match length to complexity — short question = short answer. 
  Follow-up = conversational 1-3 lines. Deep concept = full explanation.

━━━ QUESTION TYPE RULES ━━━
True/False:
  One word + one line reason.
  Example: "False — Cat A covers line maintenance only." Cite source if available.

MCQ;
   choose Most accurate option as per question 
   One word + one line reason.
   Cite source if available.

Direct fact (what is, define, list):
  1-3 sentences. Lead with the answer. Cite source if available.

Concept/explanation (how does, why does, explain):
  Direct answer → key mechanism → real maintenance context → exam point.
  Maximum 6-8 lines. No padding, Cite source if available..

Calculation:
  Formula → substitution → working → answer with unit. Nothing else.

Procedure (steps, sequence):
  Numbered list only. No intro sentence.

Follow-up (tell me more, ok, where i left off, continue, what next):
  2-3 conversational sentences only.
  Pick up from the last topic discussed in conversation history.
  NO Exam Focus tag for follow-ups.

Off-topic (fuel price, weather, news, non-aviation):
  One warm redirect. Example:
  "That's outside {MODULE_NAME} scope, {STUDENT_NAME}. 
   Focus on your DGCA prep — what topic in {MODULE_NAME} 
   can I help you with right now?"
  Nothing else. No answer to the off-topic question.

━━━ KNOWLEDGE RULES ━━━
- Use retrieved source context first; cite page when the material supports it.
- If not fully in context: teach from solid CAR 66 / maintenance exam knowledge confidently — concepts and mechanisms first.
- Never say "not found." Either answer helpfully, clarify the question, or redirect off-topic.
- Never invent rule numbers, form numbers, licence fees, durations, or pass marks.
  If those exact values are not in your sources: give the concept, then one short line such as
  "Confirm the exact number in the current CAR / on DGCA." (No long URLs or homework lists.)

━━━ CALCULATION RULES ━━━
- Lift: L = ½ × ρ × V² × S × CL — never drop the ½
- Power: P = VI or P = I²R or P = V²/R
- Ohm: V = IR
- Net Thrust = Gross Thrust − Momentum Drag
- Show every step. Unit in final answer always.

━━━ CONVERSATION MEMORY ━━━
Read the CONVERSATION HISTORY before answering.
If the student is following up — continue from where you left off.
If the student went off-topic and now says "where i left off" — 
return to the last MODULE topic, not the off-topic question.

━━━ EXAM FOCUS ━━━
For concept and explanation answers only, end with:
Exam Focus: [specific DGCA exam point — not generic, not repeated]
Skip Exam Focus for: follow-ups, calculations, True/False, off-topic redirects.

━━━ MODULE STYLE ━━━
M3/M4/M5: Formula or component first → how it works → failure modes
M6: Material property → corrosion/failure → maintenance action
M7: Safety (LOTO first always) → procedure → documentation
M8: Aerodynamic principle → formula → effect on aircraft
M9: Human error model → real maintenance scenario → reporting
M10: Exact regulation → CAR section → Indian context → privileges
M11-M17: Normal operation → limits → fault signs → maintenance action
"""

MODULE_FALLBACK_PROMPTS = {
  "M3": """You are a DGCA CAR 66 Module 3 expert — Electrical Fundamentals. Answer only questions about: DC circuits, AC circuits, magnetism, capacitance, inductance, resistance, Ohm's Law, Kirchhoff's Laws, generators, motors, transformers, batteries, semiconductors basics and other similar electrical topics only. If the question is outside Module 3 scope, say: 'This topic is not covered in Module 3 Electrical Fundamentals.' Answer at DGCA CAR 66 exam depth. Be concise and specific.""",
  "M4": """You are a DGCA CAR 66 Module 4 expert — Electronic Fundamentals. Answer only questions about: semiconductors, diodes, transistors, amplifiers, logic gates, Boolean algebra, ICs, PCBs, servomechanisms and other similar electronic topics only. If outside Module 4 scope, say so clearly. Answer at DGCA CAR 66 exam depth.""",
  "M5": """You are a DGCA CAR 66 Module 5 expert — Digital Techniques and Electronic Instrument Systems. Answer only questions about: numbering systems, data buses (ARINC 429, ARINC 664), ADC/DAC, logic circuits, microprocessors, EFIS, EICAS, ECAM, FMS displays and other similar instrument system topics only. If outside Module 5 scope, say so. Answer at exam depth.""",
  "M6": """You are a DGCA CAR 66 Module 6 expert — Materials and Hardware. Answer only questions about: aircraft metals, composites, corrosion, fasteners, pipes, control cables, bearings, seals, springs, materials testing and other similar materials and hardware topics only. If outside Module 6 scope, say so. Answer at DGCA CAR 66 exam depth.""",
  "M7A": """You are a DGCA CAR 66 Module 7A expert — Maintenance Practices. Answer only questions about: safety precautions, tools, NDT methods, electrical wiring (EWIS), riveting, weight and balance, aircraft handling, maintenance documentation, troubleshooting and other similar maintenance topics only. If outside Module 7A scope, say so. Answer at exam depth.""",
  "M7B": """You are a DGCA CAR 66 Module 7B expert — Maintenance Practices (continuation). Answer only questions about: maintenance practices, workshop safety, technical documentation, airworthiness requirements and other similar topics. If outside Module 7B scope, say so.""",
  "M8": """You are a DGCA CAR 66 Module 8 expert — Basic Aerodynamics. Answer only questions about: atmosphere, lift, drag, thrust, weight, Bernoulli's principle, airfoil theory, angle of attack, stall, stability, control surfaces, high-speed flight, Mach number, compressibility. Fixed-wing aeroplane aerodynamics ONLY. If asked about helicopters, say that is Module 12 not Module 8. Answer at DGCA CAR 66 exam depth.""",
  "M9": """You are a DGCA CAR 66 Module 9 expert — Human Factors in aviation maintenance. Answer only questions about: the Dirty Dozen, SHELL model, Reason's Swiss Cheese model, CRM, human error types, situational awareness, fatigue, stress, shift work, safety culture, incident reporting, communication in maintenance and other human factors topics only. If outside Module 9 scope, say so clearly. Answer at DGCA CAR 66 exam depth. SHELL model exact definition: S=Software (procedures/manuals), H=Hardware (tools/equipment/aircraft), E=Environment (physical/organisational), L=Liveware (the human/self at centre), L=Liveware (other humans — colleagues/supervisors). The second L is Liveware-Liveware interaction, NOT Liveware-Software. Never describe it as 5 components with a separate interface — it is 5 letters with Liveware at the centre.""",
  "M10": """You are a DGCA CAR 66 Module 10 expert — Aviation Legislation for Indian AME students. Answer only questions about: DGCA, ICAO, CAR 66, CAR 145, CAR 147, CAR M regulations, AME licence categories and privileges, CRS requirements, AMO requirements, airworthiness directives, modifications, Indian civil aviation rules and Aircraft Rules 1937, all CAR sections, acts, rules, manuals and procedures. If outside Module 10 Aviation Legislation scope, say so. Answer at DGCA CAR 66 exam depth. Never invent rule, article, or form numbers — if not certain, teach the principle and tell the student to confirm in the current CAR text on DGCA.""",
  "M11A": """You are a DGCA CAR 66 Module 11A expert — Turbine Aeroplane Aerodynamics, Structures and Systems. Answer only questions about turbine aeroplane systems: airframe structures, air conditioning, pressurisation, hydraulics, fuel, electrical, flight controls, landing gear, fire protection, pneumatics, ice protection, instruments and avionics on turbine aeroplanes and other similar topics only. If outside Module 11A scope, say so. Answer at exam depth.""",
  "M11B": """You are a DGCA CAR 66 Module 11B expert — Piston Aeroplane Aerodynamics, Structures and Systems. Same as 11A but for piston engine aeroplanes. Answer at DGCA CAR 66 exam depth.""",
  "M11C": """You are a DGCA CAR 66 Module 11C expert — Piston Aeroplane Aerodynamics, Structures and Systems (B3 category). Answer at DGCA CAR 66 exam depth for B3 licence scope.""",
  "M12": """You are a DGCA CAR 66 Module 12 expert — Helicopter Aerodynamics, Structures and Systems. Answer only questions about: rotary wing aerodynamics, dissymmetry of lift, retreating blade stall, gyroscopic precession, translating tendency, torque reaction, anti-torque systems, vortex ring state, autorotation, ground effect, blade tracking, helicopter transmission, cyclic/collective/tail rotor controls and other similar helicopter topics only. If asked about fixed-wing aeroplanes, redirect to Module 8. Answer at DGCA CAR 66 exam depth.""",
  "M13": """You are a DGCA CAR 66 Module 13 expert — Aircraft Aerodynamics, Structures and Systems for B2 (Avionics) licence. Answer only questions about aircraft systems from avionics perspective: navigation systems, communication systems, autopilot, EFIS, FMS, TCAS, EGPWS, weather radar, data buses, IMA and other similar topics only. Answer at DGCA CAR 66 exam depth.""",
  "M14": """You are a DGCA CAR 66 Module 14 expert — Propulsion for B2 (Avionics) licence. Answer only questions about engine systems from avionics perspective: FADEC, engine indicating systems (EGT, N1, N2, oil pressure), starting and ignition electrical systems, engine fire detection and extinguishing and other similar topics only. Answer at DGCA CAR 66 exam depth.""",
  "M15": """You are a DGCA CAR 66 Module 15 expert — Gas Turbine Engine. Answer only questions about: Brayton cycle, turbojet, turbofan, turboshaft, turboprop construction and operation, compressor types and stall/surge, combustion, turbine blades, exhaust and thrust reversers, FADEC, fuel/oil/bleed air systems, engine performance parameters (EPR, EGT, N1, N2, SFC) and other similar topics only. Answer at DGCA CAR 66 exam depth.""",
  "M16": """You are a DGCA CAR 66 Module 16 expert — Piston Engine. Answer only questions about: 4-stroke and 2-stroke cycles, Otto cycle, compression ratio, engine configuration, carburetor types, fuel injection, magneto ignition, spark plugs, supercharging, turbocharging, engine power calculations, pre-ignition, detonation and other related topics only. Answer at DGCA CAR 66 exam depth.""",
  "M17A": """You are a DGCA CAR 66 Module 17A expert — Propeller. Answer only questions about: propeller aerodynamics, fixed pitch, variable pitch, constant speed propellers, pitch control, feathering, reverse thrust, propeller synchronising, ice protection, maintenance and other similar related topics only. Answer at DGCA CAR 66 exam depth.""",
}

DEFAULT_FALLBACK = """You are a DGCA CAR 66 AME exam expert. Answer only questions related to aircraft maintenance engineering at DGCA CAR 66 exam standard. If the question is outside aviation maintenance scope, say so clearly."""


def is_unhelpful_answer(answer: str) -> bool:
    unhelpful_phrases = [
        "does not specifically discuss",
        "not explicitly listed",
        "not mentioned in the",
        "no information provided",
        "context does not",
        "not provided in the",
        "cannot find",
        "not available in",
        "context information does not",
        "provided context does not",
        "does not mention",
        "is not discussed",
        "no specific information",
        "rule was not found",
        "not found in the retrieved",
    ]
    answer_lower = answer.lower()
    return any(phrase in answer_lower for phrase in unhelpful_phrases)


# Ensure env variables are loaded before reading SUPABASE_* vars
load_env()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")

# --- Supabase SSL Timeout & Retry Fixes ---
import httpx
import time

_original_request = httpx.Client.request

def _patched_request(self, method, url, **kwargs):
    is_supabase = SUPABASE_URL in str(url)
    
    if is_supabase:
        # 1. Add a timeout of 30 seconds to all Supabase requests
        kwargs['timeout'] = 30.0

    try:
        try:
            return _original_request(self, method, url, **kwargs)
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            if is_supabase:
                # 2. Add retry logic - retry up to 3 times
                last_error = e
                for attempt in range(3):
                    print(f"Supabase connection error ({type(last_error).__name__}). Retrying {attempt+1}/3 in 2 seconds...")
                    time.sleep(2)
                    try:
                        return _original_request(self, method, url, **kwargs)
                    except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as retry_e:
                        last_error = retry_e
                raise last_error
            raise e
    except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
        if is_supabase:
            # 3. Proper error handling: clear error message instead of crashing
            raise HTTPException(
                status_code=503, 
                detail="Database connection failed (SSL/Handshake timeout). Please try again later."
            )
        raise e

httpx.Client.request = _patched_request

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize FastAPI app
app = FastAPI(title="Fonus API")

# ── CORS (Cross-Origin Resource Sharing) ─────────────────────────────────────
# CORS controls which websites are allowed to talk to this API.
# In production, NEVER use ["*"] — that means ANY website can call your API!
# We read the allowed origins from an environment variable.
#
# Set in backend/.env:
#   ALLOWED_ORIGINS=https://fonus.co.in,https://www.fonus.co.in
#
# For local dev, also add: http://localhost:3000
# ─────────────────────────────────────────────────────────────────────────────
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"  # Safe fallback for local dev
)
# Split the comma-separated string into a list, strip whitespace from each
ALLOWED_ORIGINS: list = [o.strip() for o in _raw_origins.split(",") if o.strip()]

print(f"[CORS] Allowed origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,     # Only specific domains — NOT wildcard
    allow_credentials=True,            # Allow cookies/auth headers
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# ── SlowAPI Rate Limiter ──────────────────────────────────────────────────────
# Attach the rate limiter to our FastAPI app.
# Individual routes can be decorated with @limiter.limit("X/minute").
# ─────────────────────────────────────────────────────────────────────────────
if _SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    print("[RateLimit] SlowAPI rate limiter active: 200 requests/minute per IP")
else:
    limiter = None

from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    import traceback
    print(f"[GLOBAL ERROR] {request.url} → {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. The team has been notified."}
    )


# ── Health Check Endpoint ─────────────────────────────────────────────────────
# Nginx and Docker use this endpoint to check if the backend is alive.
# If this returns 200, everything is OK. If it fails, something is wrong.
# Visit: http://localhost:8000/health  or  https://yourdomain.com/health
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    Returns a simple OK response so Nginx and Docker know the backend is running.
    This endpoint has no authentication — it's safe to be public.
    """
    return {"status": "ok", "service": "fonus-backend"}


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")




# --- Pydantic Models ---

class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    college: Optional[str] = None

class StreamUpdateRequest(BaseModel):
    user_id: str
    stream: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ChatRequest(BaseModel):
    question: str
    module: str
    user_id: Optional[str] = None
    preferred_llm: Optional[str] = "auto"
    allow_ai_knowledge: Optional[bool] = False
    history: Optional[List[Dict[str, str]]] = []
    stream: Optional[str] = None

class CompactRequest(BaseModel):
    messages: list
    module: str
    user_id: Optional[str] = None

class PracticeAnswerRequest(BaseModel):
    user_id: str
    module: str
    question_id: str
    selected_answer: str
    correct_answer: str
    topic: Optional[str] = "general"  # syllabus topic id e.g. "6.4", "9.10"

class VerifyAnswerRequest(BaseModel):
    question: str
    options: Dict[str, str]
    module: Optional[str] = "M10"
    correct_answer: Optional[str] = None

class FeedbackRequest(BaseModel):
    user_id: Optional[str] = None
    module: str
    type: str
    message: str

class ProgressTrackRequest(BaseModel):
    user_id: Optional[str] = None
    module: str
    target_questions: int
    mode: str 

class GoalRequest(BaseModel):
    user_id: str
    module: str
    target_questions: int

class PromoCheckRequest(BaseModel):
    code: str
    user_id: Optional[str] = None

class PromoRedeemRequest(BaseModel):
    code: str
    module: str
    user_id: str

class UsageTrackRequest(BaseModel):
    user_id: str
    type: str  # "chat_minutes" or "practice_set"
    amount: int = 1

# --- Dependency (Auth) ---

def get_current_user(authorization: Optional[str] = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing Authorization header")
    token = authorization.split(" ")[1]
    
    # Verify token with Supabase
    try:
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_res.user.id
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


# --- Endpoints ---

@app.on_event("startup")
async def startup_event():
    # ── LlamaIndex Settings ────────────────────────────────────────────────────
    # This sets up the embedding model and LLM used for AI retrieval.
    # If GROQ_API_KEY is not set, this will still load but chat routes will fail
    # gracefully (we check for None index before using it).
    # ──────────────────────────────────────────────────────────────────────────
    try:
        init_settings()
        print("[Startup] LlamaIndex settings initialised OK")
    except Exception as e:
        # Settings failed (e.g. missing HuggingFace model on first boot)
        # The server still starts — routes that need AI will return a clear error.
        print(f"[Startup] WARNING: Could not init LlamaIndex settings: {e}")

    # ── Load Module Indexes ────────────────────────────────────────────────────
    # Tries to load all DGCA module indexes from disk.
    # On Render (cloud), the index files don't exist — that's OK.
    # The server still boots; any chat route checks for None and returns a
    # friendly error message instead of a 500 crash.
    # ──────────────────────────────────────────────────────────────────────────
    try:
        app.state.indexes = load_all_indexes()
        print(f"[Startup] Loaded {len(app.state.indexes)} module indexes")
    except Exception as e:
        # No indexes found (normal on cloud deployment without index files)
        print(f"[Startup] WARNING: Could not load indexes: {e}")
        app.state.indexes = {}   # Empty dict — routes will handle this gracefully

    print("Fonus API running on http://localhost:8000")


DISPOSABLE_DOMAINS = [
    'mailinator.com', 'tempmail.com', 'guerrillamail.com', '10minutemail.com', 
    'throwaway.email', 'yopmail.com', 'trashmail.com', 'fakeinbox.com', 
    'sharklasers.com', 'guerrillamailblock.com', 'grr.la', 'spam4.me', 
    'temp-mail.org', 'dispostable.com', 'maildrop.cc'
]

def check_email_domain(email: str):
    parts = email.split('@')
    if len(parts) != 2:
        return False
    domain = parts[1].lower()
    if '.' not in domain:
        return False
    if domain in DISPOSABLE_DOMAINS:
        return 'disposable'
    return True

@app.post("/auth/signup")
async def signup(req: SignupRequest):
    email_status = check_email_domain(req.email)
    if email_status == 'disposable':
        raise HTTPException(status_code=400, detail="Please use a valid college or personal email address. Temporary emails are not allowed.")
    elif email_status is False:
        raise HTTPException(status_code=400, detail="Invalid email format.")
        
    try:
        # 1. Create Supabase auth user
        auth_response = supabase.auth.sign_up({
            "email": req.email,
            "password": req.password,
        })
        
        user = auth_response.user
        if not user:
            raise HTTPException(status_code=400, detail="Signup failed, user already exists or invalid data.")

        # 2. Create profile in `profiles` table
        # Default tier is 'free'
        profile_data = {
            "id": user.id,
            "email": req.email,
            "full_name": req.full_name,
            "college": req.college,
            "tier": "free"
        }
        
        supabase.table("profiles").insert(profile_data).execute()

        return {
            "user_id": user.id,
            "email": req.email,
            "tier": "free"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
async def login(req: LoginRequest):
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })
        
        user = auth_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
        # Get user profile
        profile_res = supabase.table("profiles").select("*").eq("id", user.id).execute()
        profile = profile_res.data[0] if profile_res.data else {}

        return {
            "access_token": auth_response.session.access_token,
            "user": profile
        }
    except Exception as e:
        # Provide better error messages
        err_msg = str(e)
        if "Invalid login credentials" in err_msg:
            raise HTTPException(status_code=400, detail="Invalid email or password.")
        if "Email not confirmed" in err_msg:
            raise HTTPException(status_code=400, detail="Please verify your email address first.")
        raise HTTPException(status_code=400, detail=f"Login failed: {err_msg}")

@app.post("/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    try:
        supabase.auth.reset_password_for_email(req.email)
        return {"success": True, "message": "Password reset link sent to your email"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/profile/stream")
async def update_stream(req: StreamUpdateRequest, user_id: str = Depends(get_current_user)):
    try:
        # Enforce that user can only update their own stream
        if req.user_id != user_id:
            raise HTTPException(status_code=403, detail="Not authorized to update this profile")
        supabase.table("profiles").update({"stream": req.stream}).eq("id", req.user_id).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/auth/check-email")
async def check_email_exists(email: str):
    try:
        # Check if email exists in profiles table
        result = supabase.table("profiles").select("id").eq("email", email).execute()
        return {"exists": len(result.data) > 0}
    except Exception as e:
        print(f"Check email error: {e}")
        return {"exists": False}


@app.get("/auth/me")
async def get_me(user_id: str = Depends(get_current_user)):
    try:
        
        # Fetch profile
        profile_res = supabase.table("profiles").select("*").eq("id", user_id).execute()
        if not profile_res.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        profile = profile_res.data[0]
        
        # Fetch module access
        access_res = supabase.table("module_access").select("module").eq("user_id", user_id).execute()
        module_access = [row["module"] for row in access_res.data] if access_res.data else []
        
        return {
            "profile": profile,
            "tier": profile.get("tier", "free"),
            "module_access": module_access
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed: " + str(e))


def get_exam_focus(question: str, module_key: str, stream: str) -> str:
    """Generate exam focus based on syllabus level."""
    if not stream:
        stream = ""
    
    import json
    from pathlib import Path
    
    syllabus_path = Path(__file__).parent / "data" / "exam_syllabus.json"
    
    if not syllabus_path.exists():
        return ""
    
    with open(syllabus_path) as f:
        syllabus = json.load(f)
    
    module_data = syllabus.get(module_key, {})
    topics = module_data.get("topics", {})
    
    # Find matching topic from question
    question_lower = question.lower()
    matched_topic = None
    max_level = 0
    
    for topic_id, topic_data in topics.items():
        topic_name = topic_data.get("name", "").lower()
        # Check if topic keywords appear in question
        topic_words = topic_name.split()
        if any(word in question_lower for word in topic_words if len(word) > 4):
            # Get level for this stream
            if stream and "B1" in stream:
                level = topic_data.get("level_B1", topic_data.get("level_ALL", 0))
            elif "B2" in stream:
                level = topic_data.get("level_B2", topic_data.get("level_ALL", 0))
            elif "A" in stream:
                level = topic_data.get("level_A", topic_data.get("level_ALL", 0))
            else:
                level = topic_data.get("level_ALL", 0)
            
            if level > max_level:
                max_level = level
                matched_topic = (topic_id, topic_data["name"], level)
    
    if not matched_topic:
        return ""
    
    topic_id, topic_name, level = matched_topic
    
    level_descriptions = {
        1: f"Topic {topic_id} ({topic_name}) is Level 1 — basic awareness. DGCA tests general understanding only.",
        2: f"Topic {topic_id} ({topic_name}) is Level 2 — working knowledge. DGCA tests practical understanding and application.",
        3: f"Topic {topic_id} ({topic_name}) is Level 3 — detailed knowledge. This is a HIGH PRIORITY exam topic. DGCA tests in-depth technical understanding."
    }
    
    return level_descriptions.get(level, "")


VAGUE_QUERY_EXPANSIONS = {
    'M15': {
        'keywords': ['engine', 'turbine', 'jet', 'gas turbine'],
        'expansion': 'gas turbine engine construction operation Brayton cycle compressor turbine combustion',
        'focus': 'gas turbine engine overview — construction, Brayton cycle, major components and operation'
    },
    'M16': {
        'keywords': ['engine', 'piston', 'motor'],
        'expansion': 'piston engine 4-stroke cycle construction operation power output',
        'focus': 'piston engine overview — 4-stroke cycle, major components and power output'
    },
    'M8': {
        'keywords': ['aerodynamics', 'flight', 'lift', 'drag', 'wing'],
        'expansion': 'aerodynamics lift drag thrust weight forces acting on aircraft',
        'focus': 'basic aerodynamics — four forces acting on aircraft in flight'
    },
    'M3': {
        'keywords': ['electrical', 'electricity', 'circuit', 'current'],
        'expansion': 'electrical fundamentals voltage current resistance Ohm law circuits',
        'focus': 'electrical fundamentals — voltage, current, resistance and basic circuit laws'
    },
    'M9': {
        'keywords': ['human factors', 'error', 'safety', 'maintenance'],
        'expansion': 'human factors aviation maintenance dirty dozen SHELL model error types',
        'focus': 'human factors in maintenance — Dirty Dozen and SHELL model'
    },
    'M10': {
        'keywords': ['regulations', 'rules', 'legislation', 'law', 'car'],
        'expansion': 'CAR 66 aviation legislation DGCA regulations AME licence privileges',
        'focus': 'aviation legislation — CAR 66, AME licence categories and privileges'
    },
    'M12': {
        'keywords': ['helicopter', 'rotor', 'rotary'],
        'expansion': 'helicopter aerodynamics rotor system construction operation controls',
        'focus': 'helicopter aerodynamics — rotor system, dissymmetry of lift, controls'
    },
    'M6': {
        'keywords': ['materials', 'metal', 'composite', 'hardware'],
        'expansion': 'aircraft materials metals composites corrosion fasteners properties',
        'focus': 'aircraft materials — metals, composites, corrosion and fasteners'
    },
    'M7A': {
        'keywords': ['maintenance', 'practices', 'tools', 'inspection'],
        'expansion': 'maintenance practices tools safety inspection documentation procedures',
        'focus': 'maintenance practices — safety, tools, inspection and documentation'
    },
    'M17A': {
        'keywords': ['propeller', 'blade', 'prop'],
        'expansion': 'propeller types fixed variable pitch constant speed operation maintenance',
        'focus': 'propellers — fixed pitch, variable pitch and constant speed operation'
    },
}


def build_smart_query(question: str, 
                      module_key: str,
                      chat_history: list) -> str:
    """Build a better search query by 
    understanding context and intent."""
    
    q = question.lower().strip()

    # Never boost CHAT messages or very short greetings
    chat_words = ['hi', 'hello', 'hey', 'thanks', 'thank you', 
                  'ok', 'okay', 'got it', 'understood', 'bye']
    if q in chat_words or len(q.split()) <= 2:
        return question
    
    # Reference questions — use history context
    reference_words = [
        'second topic', 'first topic', 'that',
        'this', 'above', 'previous', 'last one',
        'explain more', 'tell me more',
        'elaborate', 'what about it',
        'and', 'also', 'what else'
    ]
    
    is_reference = any(word in q for word in reference_words)
    
    if is_reference and chat_history:
        # Find last substantive user question
        for msg in reversed(chat_history):
            if msg['role'] == 'user' and \
               len(msg['content']) > 10 and \
               not any(w in msg['content'].lower() 
                       for w in reference_words):
                # Combine with current question
                return f"{msg['content']} {question}"

    # Vague query detection — short question with no specific technical term
    # e.g. "tell me about engines" in M15, "explain hydraulics" in M11A
    word_count = len(q.split())
    vague_openers = [
        'tell me about', 'explain', 'what is', 'describe',
        'overview of', 'give me', 'talk about', 'about'
    ]
    is_vague = (
        word_count <= 6 and
        any(q.startswith(opener) or q == opener.strip() for opener in vague_openers)
    ) or word_count <= 3

    if is_vague and module_key in VAGUE_QUERY_EXPANSIONS:
        entry = VAGUE_QUERY_EXPANSIONS[module_key]
        # Check if the vague query is about this module's topic
        # (to avoid expanding "tell me about safety" in M15 as a turbine question)
        topic_words = entry['keywords']
        is_module_topic = any(kw in q for kw in topic_words)
        # For very short/bare vague queries like "tell me about engines" in M15,
        # always expand using module context
        if is_module_topic or word_count <= 3:
            return entry['expansion']

    # Module-specific keyword boosting
    module_boost = {
        'M17A': 'propeller pitch blade constant speed',
        'M17B': 'propeller pitch blade',
        'M15': 'gas turbine compressor turbine engine',
        'M16': 'piston engine cylinder',
        'M12': 'helicopter rotor blade',
        'M8': 'aerodynamics lift drag aircraft',
        'M9': 'human factors maintenance error',
        'M10': 'aviation legislation regulation CAR',
        'M6': 'materials hardware aircraft metal',
        'M7A': 'maintenance practices procedures',
    }    
    
    boost = module_boost.get(module_key, '')
    
    # For very short queries, add module context
    if len(q.split()) <= 4 and boost:
        return f"{question} {boost}"
    
    return question


def filter_relevant_nodes(nodes, question, module_key):
    if not nodes:
        return nodes
    
    question_lower = question.lower()
    
    module_topic_filters = {
        "M17A": ["propeller", "pitch", "blade", "feather", "constant speed", "csu"],
        "M17B": ["propeller", "pitch", "blade", "feather", "constant speed"],
        "M15":  ["compressor", "turbine", "combustion", "engine", "thrust", "gas turbine", "fadec", "fuel control"],
        "M16":  ["piston", "cylinder", "carburetor", "magneto", "crankshaft"],
        "M12":  ["helicopter", "rotor", "blade", "swashplate", "collective", "cyclic"],
        "M9":   ["human factor", "shell", "error", "fatigue", "crm", "dirty dozen", "assertiveness"],
        "M8":   ["aerodynamic", "lift", "drag", "stall", "bernoulli", "airfoil", "induced", "speed"],
        "M6":   ["metal", "corrosion", "composite", "fastener", "rivet", "material"],
        "M10":  ["rule", "car", "regulation", "licence", "ame", "camo", "form", "dgca", "airworthiness"],
        "M7A":  ["maintenance", "tool", "inspection", "ndt", "safety", "torque", "rigging"],
        "M3":   ["electrical", "voltage", "current", "resistance", "circuit", "transformer", "capacitor"],
        "M4":   ["transistor", "diode", "amplifier", "logic", "semiconductor", "gate"],
        "M5":   ["arinc", "data bus", "digital", "binary", "logic", "efis", "fms", "microprocessor"],
        "M11A": ["aircraft", "hydraulic", "fuel system", "pressurisation", "flight control", "landing gear"],
        "M11B": ["aircraft", "hydraulic", "fuel system", "flight control", "piston aeroplane"],
        "M13":  ["navigation", "communication", "autopilot", "tcas", "egpws", "radar", "avionics"],
        "M14":  ["fadec", "engine control", "egt", "n1", "n2", "fuel metering", "ignition"],
    }
    
    module_keywords = module_topic_filters.get(module_key, [])
    
    if not module_keywords:
        return nodes
    
    question_is_on_topic = any(kw in question_lower for kw in module_keywords)
    
    if not question_is_on_topic:
        return nodes
    
    filtered = [
        node for node in nodes
        if any(kw in node.text.lower() for kw in module_keywords)
    ]
    
    result = filtered if filtered else nodes[:1]
    print(f"[Filter] {len(nodes)} → {len(result)} nodes after topic filter")
    return result


def infer_topic_from_question(module_key: str, question: str) -> tuple[str | None, str, float]:
    """Infer the most likely syllabus topic for a module question."""
    topics = SYLLABUS_DATA.get(module_key, {}).get("topics", {})
    if not topics:
        return None, "", 0.0

    q = (question or "").lower().strip()
    if not q:
        return None, "", 0.0

    stop_words = {
        "what", "is", "are", "the", "of", "and", "for", "to", "in", "on", "a",
        "an", "how", "why", "explain", "define", "about", "with", "from"
    }

    def _tokens(text: str) -> set[str]:
        return {
            tok for tok in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(tok) > 2 and tok not in stop_words
        }

    # Exact matches first (topic id or full topic phrase).
    for tid, t in topics.items():
        tname = (t.get("name", "") or "").lower()
        if tid.lower() in q or (tname and tname in q):
            return tid, t.get("name", tid), 1.0

    q_tokens = _tokens(q)
    best_tid = None
    best_name = ""
    best_score = 0.0

    for tid, t in topics.items():
        tname = t.get("name", tid)
        t_tokens = _tokens(tname)
        if not t_tokens:
            continue
        overlap = len(q_tokens & t_tokens)
        if overlap <= 0:
            continue
        score = overlap / max(1, len(t_tokens))
        if score > best_score:
            best_score = score
            best_tid = tid
            best_name = tname

    # Keep only meaningful topic matches.
    if best_tid and best_score >= 0.34:
        return best_tid, best_name, best_score
    return None, "", 0.0


def filter_relevant_nodes_precise(
    nodes,
    question: str,
    module_key: str,
    topic_id: str | None = None,
    topic_name: str = "",
):
    """
    More precise node filtering:
    1) Topic-aware filtering when a topic is inferred.
    2) Fallback to module keyword filtering.
    """
    if not nodes:
        return nodes

    q_lower = (question or "").lower()
    topic_terms = set()
    if topic_name:
        topic_terms.update(
            tok for tok in re.findall(r"[a-z0-9]+", topic_name.lower())
            if len(tok) > 2
        )
    if topic_id:
        topic_terms.add(topic_id.lower())

    if topic_terms:
        topic_filtered = [
            node for node in nodes
            if any(term in node.text.lower() for term in topic_terms)
        ]
        if topic_filtered:
            print(f"[Topic Filter] {len(nodes)} → {len(topic_filtered)} ({topic_id or topic_name})")
            return topic_filtered

    # Backward-compatible module filter if topic filter had no hits.
    return filter_relevant_nodes(nodes, q_lower, module_key)


def compute_query_source_alignment(question: str, source_nodes) -> float:
    """
    Lexical overlap score between user query and retrieved nodes (0..1).
    Mitigation stack for hallucination vs retrieval drift (beyond this score):
    stricter prompts for regulatory facts, optional human QA on critical paths,
    grounding checks (numbers/dates must appear in context), and citations.
    """
    if not source_nodes:
        return 0.0

    stop_words = {
        "what", "is", "are", "the", "of", "and", "for", "to", "in", "on", "a",
        "an", "how", "why", "explain", "define", "about", "with", "from"
    }
    q_tokens = {
        tok for tok in re.findall(r"[a-z0-9]+", (question or "").lower())
        if len(tok) > 2 and tok not in stop_words
    }
    if not q_tokens:
        return 0.0

    best = 0.0
    for node in source_nodes[:6]:
        n_tokens = {
            tok for tok in re.findall(r"[a-z0-9]+", (node.text or "").lower())
            if len(tok) > 2 and tok not in stop_words
        }
        if not n_tokens:
            continue
        overlap = len(q_tokens & n_tokens) / max(1, len(q_tokens))
        best = max(best, overlap)
    return round(best, 4)


@app.post("/chat")
async def chat(req: ChatRequest):
    indexes = app.state.indexes
    detected = detect_module(req.question)
    # Use requested module if available, else detected
    module_key = req.module if req.module in indexes else detected
    student_name = "there"
    user_stream = (req.stream if hasattr(req, "stream") and req.stream else None) or "B1.1"
    # Strip stray quote characters the frontend may send
    req.question = req.question.strip().strip('"').strip("'").strip()
    intent = classify_intent(req.question)
    # Continue active drill sessions even when user replies with short answers like "a"/"b".
    if intent != "DRILL" and getattr(req, "history", None):
        for _msg in reversed(req.history):
            if _msg.get("role") != "assistant":
                continue
            _content = (_msg.get("content") or "").lower()
            if "drill question" in _content and "reply with option letter" in _content:
                intent = "DRILL"
                break
            # Stop after checking the most recent assistant turn.
            break
    # Fallback: if frontend didn't send history, use latest saved assistant reply.
    if intent != "DRILL" and req.user_id:
        try:
            _last = supabase.table("chat_history")\
                .select("answer")\
                .eq("user_id", req.user_id)\
                .eq("module", module_key)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            if _last.data:
                _answer = (_last.data[0].get("answer", "") or "").lower()
                if "drill question" in _answer and "reply with option letter" in _answer:
                    intent = "DRILL"
        except Exception as _e:
            print(f"[Drill intent fallback] history lookup error: {_e}")
    print(f"[Intent] '{req.question[:50]}' → {intent}")

    # ── CHAT HANDLER ──────────────────────────────────
    if intent == "CHAT":
        name = f"{student_name}" if student_name else "there"
        focus_hint = ""
        if suggests_non_aviation_smalltalk(req.question):
            focus_hint = (
                f"\nTheir message sounds outside CAR 66 / AME study. Reply in 2 short sentences — "
                f"warm empathy, then steer them back to {module_key} concepts, PYQs, regulations, "
                "or troubleshooting scenarios. Do not answer the unrelated topic itself."
            )
        chat_reply, convo_llm = llm_complete_with_rotation(
            f"You are Fonus — DGCA AME exam mentor. "
            f"Student: {name}. Module: {module_key}. Stream: {user_stream}.\n"
            f"The student said: '{req.question}'\n"
            f"Respond warmly in 1-2 sentences like a mentor who knows them. "
            f"Reference their module or upcoming exam naturally if relevant. "
            f"Never say 'How can I help you today' or 'Ask me anything'."
            f"{focus_hint}",
            req.preferred_llm or "auto",
        )
        return JSONResponse(content={
            "answer": chat_reply,
            "source": [],
            "llm_used": convo_llm,
            "topic_id": None,
            "exam_priority": None
        })

    # ── PYQ HANDLER ───────────────────────────────────
    if intent == "PYQ":
        # Try multiple known locations for PYQ files
        pyq_candidates = [
            os.path.join(os.path.dirname(__file__), "data", "Modules", module_key, "processed"),
            os.path.join(os.path.dirname(__file__), "..", "data", "Modules", module_key, "processed"),
            os.path.join(os.path.dirname(__file__), "data", "questions", f"{module_key}.json"),
        ]
        pyq_path = None
        pyq_dir = None
        for candidate in pyq_candidates:
            if os.path.isdir(candidate):
                pyq_dir = candidate
                break
            elif os.path.isfile(candidate):
                pyq_path = candidate
                break
        print(f"[PYQ] module={module_key} | dir={pyq_dir} | file={pyq_path}")
        pyq_note = ""
        all_questions = []
        if pyq_dir and os.path.isdir(pyq_dir):
            # Load all JSON files from the processed folder
            for fname in os.listdir(pyq_dir):
                if fname.endswith(".json"):
                    try:
                        with open(os.path.join(pyq_dir, fname), "r", encoding="utf-8") as f:
                            chunk = json.load(f)
                            if isinstance(chunk, list):
                                all_questions.extend(chunk)
                            elif isinstance(chunk, dict):
                                all_questions.extend(chunk.get("questions", []))
                    except Exception as e:
                        print(f"[PYQ] Error loading {fname}: {e}")
            pyq_data = all_questions
            print(f"[PYQ] Loaded {len(all_questions)} questions from {pyq_dir}")
        elif pyq_path and os.path.isfile(pyq_path):
            with open(pyq_path, "r", encoding="utf-8") as f:
                pyq_data = json.load(f)
        else:
            pyq_data = []
            print(f"[PYQ] No PYQ data found for {module_key}")
        if pyq_data:
            # Count topic frequency to find most repeated
            topic_counts = {}
            for item in pyq_data if isinstance(pyq_data, list) else pyq_data.get("questions", []):
                topic = item.get("topic", item.get("topic_id", "General"))
                # Only count topics that belong to that module
                # M6 topics should  start with "6.", M15 with "15.", etc.
                module_num = module_key.replace("M", "").replace("A","").replace("B","").replace("C","")
                if str(topic).startswith(module_num + ".") or str(topic).startswith(module_num + " "):
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
            top5 = sorted_topics[:5]
            
            # Also pull 2 sample questions per top topic so LLM has real content
            sample_questions = []
            for top_topic, count in top5:
                samples = [
                    q.get("question", q.get("text", ""))
                    for q in all_questions
                    if q.get("topic", q.get("topic_id", "")) == top_topic
                ][:2]
                sample_questions.append(
                    f"  Topic {top_topic} ({count} questions):\n" +
                    "\n".join(f"    Q: {s}" for s in samples if s)
                )
            
            # Add verified topic names from syllabus alongside counts
            syllabus_topics = SYLLABUS_DATA.get(module_key, {}).get("topics", {})
            pyq_note = (
                f"PYQ frequency from Fonus database ({len(all_questions)} total questions):\n"
            )
            for top_topic, count in top5:
                topic_name = syllabus_topics.get(top_topic, {}).get("name", top_topic)
                level = syllabus_topics.get(top_topic, {}).get("level_B1", "?")
                samples = [
                    q.get("question", q.get("text", ""))
                    for q in all_questions
                    if q.get("topic", q.get("topic_id", "")) == top_topic
                ][:2]
                sample_text = "\n".join(f"    Q: {s}" for s in samples if s)
                pyq_note += (
                    f"\n  {top_topic}. {topic_name} — L{level} "
                    f"({count} questions in PYQ bank)\n{sample_text}"
                )
        else:
            pyq_note = f"PYQ database for {module_key} not loaded yet."
        
        name = f"{student_name}, " if student_name else ""
        pyq_reply, _pyq_llm = llm_complete_with_rotation(
            f"You are Fonus — DGCA AME exam mentor.\n"
            f"Student: {name}Module: {module_key}. Stream: {user_stream}.\n"
            f"Student asked: '{req.question}'\n"
            f"Current module page: {module_key}. PYQ data loaded: {module_key}.\n"
            f"If student mentioned a different module in their question, "
            f"start your response with: "
            f"'I have {module_key} data here — based on that: [answer]. "
            f"For [mentioned module], head to that module page for accurate PYQ analysis.'\n\n"
            f"PYQ frequency data:\n{pyq_note}\n\n"
            f"Answer in mentor style — which topics appear most, "
            f"what level they test, what to focus on. "
            f"Be specific. 6-8 lines max. No generic advice.\n"
            f"End your response with exactly this line: "
            f"'Derived from 5–6 years of DGCA PYQ analysis.'",
            req.preferred_llm or "auto",
        )
        return JSONResponse(content={
            "answer": pyq_reply,
            "source": [{"source": f"Fonus PYQ Database — {module_key}", "page": ""}],
            "llm_used": "Ground Truth + LLM",
            "topic_id": None,
            "exam_priority": None
        })

    # ── NOTE HANDLER ─────────────────────────────────
    if intent == "NOTE":
        topics = SYLLABUS_DATA.get(module_key, {}).get("topics", {})
        topic_list = "\n".join(
            f"  {tid}. {t['name']} — L{t.get('level_B1','?')}"
            for tid, t in topics.items()
        ) if topics else ""

        # Find which specific topic the student is asking about
        topic_match = None
        topic_match_name = ""
        q_lower = req.question.lower()
        for tid, t in topics.items():
            if t["name"].lower() in q_lower or tid in q_lower:
                topic_match = tid
                topic_match_name = t["name"]
                break

        # Pull PYQ questions for this specific topic
        pyq_dir = os.path.normpath(os.path.join(
            os.path.dirname(__file__), "..", "data", "Modules", module_key, "processed"
        ))
        topic_pyqs = []
        if os.path.isdir(pyq_dir):
            for fname in os.listdir(pyq_dir):
                if fname.endswith(".json"):
                    try:
                        with open(os.path.join(pyq_dir, fname), "r", encoding="utf-8") as f:
                            chunk = json.load(f)
                            items = chunk if isinstance(chunk, list) else chunk.get("questions", [])
                            for item in items:
                                t = item.get("topic", item.get("topic_id", ""))
                                if topic_match and str(t) == str(topic_match):
                                    topic_pyqs.append(item)
                                elif not topic_match and q_lower in item.get("question", "").lower():
                                    topic_pyqs.append(item)
                    except:
                        pass

        # Pick top 5 PYQ questions for this topic
        sample_pyqs = topic_pyqs[:5]
        pyq_block = ""
        if sample_pyqs:
            pyq_block = "\n\nFREQUENTLY ASKED DGCA QUESTIONS ON THIS TOPIC:\n"
            for i, q in enumerate(sample_pyqs, 1):
                question_text = q.get("question", q.get("text", ""))
                answer = q.get("answer", q.get("correct_answer", ""))
                if question_text:
                    pyq_block += f"Q{i}. {question_text}\n"
                    if answer:
                        pyq_block += f"    Ans: {answer}\n"

        # Get topic level for exam focus
        topic_level = ""
        if topic_match:
            level_num = topics.get(topic_match, {}).get("level_B1", 2)
            level_labels = {1: "L1 — awareness only", 2: "L2 — working knowledge, expect application questions", 3: "L3 — detailed knowledge, expect scenario and calculation questions"}
            topic_level = level_labels.get(level_num, "")

        name = f"{student_name}, " if student_name else ""
        facts = get_exam_facts(module_key, user_stream)

        # Use higher token limit for detailed notes
        _note_prompt = (
            f"You are Fonus — DGCA AME exam mentor and the best aviation notes writer.\n"
            f"Student: {student_name}. Module: {module_key}. Stream: {user_stream}.\n"
            f"Student request: '{req.question}'\n\n"
            f"MODULE SYLLABUS:\n{topic_list}\n\n"
            f"TOPIC BEING STUDIED: {topic_match_name or req.question}\n"
            f"EXAM LEVEL: {topic_level}\n"
            f"{pyq_block}\n\n"
            f"Create a DGCA exam revision note. Use this exact structure:\n\n"
            f"## [Topic Name]\n\n"
            f"DEFINITION\n"
            f"[1-2 line precise definition an AME would use]\n\n"
            f"HOW IT WORKS\n"
            f"[Mechanism explained simply — no textbook jargon]\n\n"
            f"TYPES\n"
            f"[List with one-line explanation each]\n\n"
            f"WHERE IT OCCURS ON AIRCRAFT\n"
            f"[Specific aircraft locations — not generic]\n\n"
            f"DETECTION AND PREVENTION\n"
            f"[What the AME does — inspection, treatment, documentation]\n\n"
            f"DGCA EXAM FOCUS — {topic_level}\n"
            f"[Exactly what DGCA tests on this topic — be specific]\n\n"
            f"MOST REPEATED PYQ POINTS\n"
            f"[3-5 bullet points from the PYQ questions provided]\n\n"
            f"QUICK RECALL\n"
            f"[5-7 one-line facts to memorize]\n\n"
            f"Rules: Only verified M{module_key.replace('M','')} aviation knowledge. "
            f"Never mention external websites. Never fabricate values.\n"
            f"Do not use ** markdown bold anywhere. "
            f"Use plain text headings in CAPS only.\n"
            f"After Quick Recall, add two options on new lines:\n"
            f"'Drill: Say drill me for 5 PYQ questions on this topic'\n"
            f"'Depth: Say go deeper for detailed explanation of any section'\n"
            f"End with: 'Want to drill this with 5 PYQ questions? Just say: drill me.'"
        )
        from llama_index.llms.groq import Groq as GroqLLM

        note_reply = None
        for _gkey in _collect_groq_keys():
            try:
                _note_llm = GroqLLM(
                    model="llama-3.3-70b-versatile",
                    api_key=_gkey,
                    max_tokens=2500,
                    temperature=0.3,
                )
                note_reply = _note_llm.complete(_note_prompt).text
                break
            except Exception as _ne:
                if _is_rate_limit_error(_ne):
                    continue
                raise
        if not note_reply:
            raise HTTPException(
                status_code=503,
                detail="Note generator rate-limited on all Groq keys. Try Gemini or wait.",
            )

        return JSONResponse(content={
            "answer": note_reply,
            "source": [{"source": f"CAR 66 Syllabus + {module_key} EASA Source Book + Fonus PYQ", "page": ""}],
            "llm_used": "Note Generator",
            "topic_id": topic_match,
            "exam_priority": topic_level
        })
    # ── END NOTE HANDLER ──────────────────────────────
    
    # ── DRILL HANDLER ────────────────────────────────
    if intent == "DRILL":
        topics = SYLLABUS_DATA.get(module_key, {}).get("topics", {})
        q_lower = req.question.lower().strip()
        direct_drill_triggers = [
            "drill me", "drill", "test me", "quiz me",
            "give me questions", "practice questions",
            "drill me again", "5 more", "next 5", "more questions"
        ]
        explicit_drill_request = any(t in q_lower for t in direct_drill_triggers)

        def _norm(text: str) -> str:
            return re.sub(r"\s+", " ", (text or "").strip().lower())

        def _extract_question_from_drill_reply(content: str) -> str:
            if not content:
                return ""
            m = re.search(r"Question:\s*(.+)", content)
            return m.group(1).strip() if m else ""

        def _format_options(options: Any) -> str:
            out = ""
            if not options:
                return out
            if isinstance(options, dict):
                for key, text in options.items():
                    out += f"   {key}. {text}\n"
            elif isinstance(options, list):
                for opt in options:
                    if isinstance(opt, dict):
                        key = opt.get("key", opt.get("label", ""))
                        text = opt.get("text", opt.get("value", ""))
                        out += f"   {key}. {text}\n"
                    else:
                        out += f"   {opt}\n"
            return out

        def _resolve_correct_answer(item: dict) -> tuple[str, str]:
            correct = str(item.get("answer", item.get("correct_answer", ""))).strip()
            options = item.get("options", {})
            label = correct.lower()
            text = correct
            if isinstance(options, dict):
                for k, v in options.items():
                    if str(k).strip().lower() == label:
                        label = str(k).strip().lower()
                        text = str(v).strip()
                        break
            return label, text

        def _is_user_correct(item: dict, user_answer: str) -> bool:
            ua = _norm(user_answer)
            if not ua:
                return False
            label, text = _resolve_correct_answer(item)
            if ua == label or ua == _norm(text):
                return True
            options = item.get("options", {})
            if isinstance(options, dict) and ua in [str(k).strip().lower() for k in options.keys()]:
                chosen = options.get(ua) or options.get(ua.upper())
                if chosen and _norm(chosen) == _norm(text):
                    return True
            return False

        # Resolve topic from query/history using topic id, topic name, and common aliases.
        topic_aliases = {
            "M6": {
                "6.9": ["gear", "gears", "transmission", "gearbox", "gear train"],
                "6.8": ["bearing", "bearings", "roller bearing", "ball bearing"],
                "6.7": ["spring", "springs", "belleville"],
                "6.5": ["fastener", "fasteners", "bolt", "nut", "screw", "thread"],
            }
        }

        selected_topic_id = None
        selected_topic_name = ""
        for tid, tdata in topics.items():
            tname = tdata.get("name", "")
            if tid in q_lower or tname.lower() in q_lower:
                selected_topic_id = tid
                selected_topic_name = tname
                break

        if not selected_topic_id:
            for tid, aliases in topic_aliases.get(module_key, {}).items():
                if any(alias in q_lower for alias in aliases):
                    selected_topic_id = tid
                    selected_topic_name = topics.get(tid, {}).get("name", tid)
                    break

        # If current query has no topic hint (e.g., "drill me"), infer from history.
        if not selected_topic_id and req.history:
            for msg in reversed(req.history):
                content = (msg.get("content") or "").lower()
                for tid, tdata in topics.items():
                    tname = tdata.get("name", "")
                    if tid in content or tname.lower() in content:
                        selected_topic_id = tid
                        selected_topic_name = tname
                        break
                if selected_topic_id:
                    break
                for tid, aliases in topic_aliases.get(module_key, {}).items():
                    if any(alias in content for alias in aliases):
                        selected_topic_id = tid
                        selected_topic_name = topics.get(tid, {}).get("name", tid)
                        break
                if selected_topic_id:
                    break

        pyq_dir = os.path.normpath(os.path.join(
            os.path.dirname(__file__), "..",
            "data", "Modules", module_key, "processed"
        ))
        all_questions = []
        if os.path.isdir(pyq_dir):
            for fname in os.listdir(pyq_dir):
                if fname.endswith(".json"):
                    try:
                        with open(os.path.join(pyq_dir, fname), "r", encoding="utf-8") as f:
                            chunk = json.load(f)
                            items = chunk if isinstance(chunk, list) else chunk.get("questions", [])
                            all_questions.extend(items)
                    except Exception:
                        pass

        if not all_questions:
            return JSONResponse(content={
                "answer": f"I don't have PYQ questions loaded for {module_key} yet.",
                "source": [],
                "llm_used": "Drill",
                "topic_id": selected_topic_id,
                "exam_priority": None
            })

        module_num = module_key.replace("M", "").replace("A", "").replace("B", "").replace("C", "")
        module_questions = [
            q for q in all_questions
            if str(q.get("topic", q.get("topic_id", ""))).startswith(module_num + ".")
        ]
        drill_pool = module_questions
        if selected_topic_id:
            topic_specific = [
                q for q in module_questions
                if str(q.get("topic", q.get("topic_id", ""))) == str(selected_topic_id)
            ]
            if topic_specific:
                drill_pool = topic_specific

        # Rebuild asked-question state from assistant drill messages in history.
        asked_questions = set()
        last_drill_question = ""
        if req.history:
            for msg in req.history:
                if msg.get("role") != "assistant":
                    continue
                content = msg.get("content", "")
                qtxt = _extract_question_from_drill_reply(content)
                if qtxt:
                    asked_questions.add(_norm(qtxt))
            for msg in reversed(req.history):
                if msg.get("role") != "assistant":
                    continue
                content = msg.get("content", "")
                if "drill question" in content.lower():
                    last_drill_question = _extract_question_from_drill_reply(content)
                    if last_drill_question:
                        break

        by_question = {
            _norm(q.get("question", q.get("text", ""))): q
            for q in drill_pool
            if q.get("question") or q.get("text")
        }

        def _next_question(exclude: set[str]) -> dict | None:
            for item in drill_pool:
                qtxt = _norm(item.get("question", item.get("text", "")))
                if qtxt and qtxt not in exclude:
                    return item
            return None

        # Grade the previous drill question if the user just answered it.
        feedback_block = ""
        if last_drill_question and not explicit_drill_request:
            prev_item = by_question.get(_norm(last_drill_question))
            if prev_item:
                user_is_correct = _is_user_correct(prev_item, req.question)
                correct_label, correct_text = _resolve_correct_answer(prev_item)
                explanation = (prev_item.get("explanation") or "").strip()
                if not explanation:
                    explanation = f"The correct option is {correct_label or correct_text} for this DGCA PYQ."
                if user_is_correct:
                    feedback_block += "Correct.\n"
                else:
                    feedback_block += "Not correct.\n"
                feedback_block += f"Correct answer: {correct_label}. {correct_text}\n"
                feedback_block += f"Why: {explanation}\n"
                src = prev_item.get("source_file", "")
                if src:
                    feedback_block += f"Source: {src}\n\n"
                asked_questions.add(_norm(last_drill_question))

        next_item = _next_question(asked_questions)
        if not next_item:
            topic_label = selected_topic_name or selected_topic_id or module_key
            return JSONResponse(content={
                "answer": (
                    f"{feedback_block}Drill complete for {topic_label}.\n"
                    f"Say 'drill me again' for another set."
                ).strip(),
                "source": [{
                    "source": f"Fonus PYQ — {module_key} {topic_label}",
                    "page": ""
                }],
                "llm_used": "Drill",
                "topic_id": selected_topic_id,
                "exam_priority": None
            })

        question_text = next_item.get("question", next_item.get("text", ""))
        options_block = _format_options(next_item.get("options", []))
        total_count = min(5, max(1, len(drill_pool)))
        current_index = min(total_count, len(asked_questions) + 1)
        topic_label = selected_topic_name or selected_topic_id or module_key
        answer_text = (
            f"{feedback_block}"
            f"Drill question ({current_index}/{total_count}) — {topic_label}\n"
            f"Question: {question_text}\n"
            f"{options_block}\n"
            f"Reply with option letter (a/b/c/d) or full answer text."
        ).strip()

        return JSONResponse(content={
            "answer": answer_text,
            "source": [{
                "source": f"Fonus PYQ — {module_key} {topic_label}",
                "page": ""
            }],
            "llm_used": "Drill",
            "topic_id": selected_topic_id,
            "exam_priority": None
        })
    # ── END DRILL HANDLER ─────────────────────────────
    
    # ── STUDY PLAN HANDLER ────────────────────────────
    if intent == "STUDY_PLAN":
        topics = SYLLABUS_DATA.get(module_key, {}).get("topics", {})
        # Sort topics by level — highest level first (most exam weight)
        sorted_topics = sorted(
            topics.items(),
            key=lambda x: x[1].get("level_B1", 0),
            reverse=True
        )
        topic_priority = "\n".join(
            f"  {tid}. {t['name']} — L{t.get('level_B1', '?')} "
            f"({'HIGHEST priority' if t.get('level_B1',0)==3 else 'medium priority' if t.get('level_B1',0)==2 else 'low priority'})"
            for tid, t in sorted_topics
        )
        facts = get_exam_facts(module_key, user_stream)
        q_count = facts["questions"] if facts else 80
        name = student_name if student_name else "there"
        plan_reply, _plan_llm = llm_complete_with_rotation(
            f"You are Fonus — DGCA AME exam mentor.\n"
            f"Student: {name}. Module: {module_key} {facts['name'] if facts else ''}. "
            f"Stream: {user_stream}. Total exam questions: {q_count}.\n\n"
            f"Student message: '{req.question}'\n\n"
            f"Module topics by exam priority (L3=detailed, L2=working knowledge, L1=awareness):\n"
            f"{topic_priority}\n\n"
            f"Create a focused study plan as a mentor who knows this student personally.\n"
            f"Structure:\n"
            f"1. Acknowledge their situation warmly (1 line)\n"
            f"2. Tell them their exact gap and what it means (1-2 lines)\n"
            f"3. Give a week-by-week plan based on topic priority levels\n"
            f"4. End with: 'Want to start right now? I'll create a complete "
            f"revision note for [highest priority topic] — just say yes.'\n\n"
            f"Use only M{module_key[-1] if module_key[-1].isdigit() else module_key} "
            f"topics. Never mention external websites. Be specific and encouraging.",
            req.preferred_llm or "auto",
        )
        return JSONResponse(content={
            "answer": plan_reply,
            "source": [{"source": f"CAR 66 Syllabus — {module_key}", "page": "Appendix I"}],
            "llm_used": "Study Planner",
            "topic_id": None,
            "exam_priority": None
        })
    # ── END STUDY PLAN HANDLER ────────────────────────
    # ── END INTENT HANDLERS ───────────────────────────
    if not indexes:
        return JSONResponse(content={
            "answer": "AI index not loaded. The knowledge base is not available on this server. Please contact admin.",
            "source": [],
            "llm_used": "none",
            "topic_id": None,
            "exam_priority": None
        })
    index = indexes.get(module_key) or (list(indexes.values())[0] if indexes else None)
    if index is None:
        return {"error": "AI index not loaded. Please contact admin."}

    # Load module-specific book names from books.json
    import json as _json
    _books_path = PROJECT_ROOT / "data" / "books.json"
    _allowed_books = []
    print(f"[books.json] Looking for file at: {_books_path}, exists: {_books_path.exists()}")
    try:
        with open(_books_path, "r", encoding="utf-8") as _f:
            _books_data = _json.load(_f)
        _module_entry = _books_data.get("modules", {}).get(module_key, {})
        _allowed_books = [b["file"] for b in _module_entry.get("books", [])]
    except Exception as _e:
        print(f"[books.json] Could not load: {_e}")
    print(f"[books.json] Loaded {len(_allowed_books)} books for {module_key}: {_allowed_books}")

    # llm_name set inside RAG loop after a successful provider call
    llm_name = "Groq (Llama 3.3 70B)"

    # Build document context hint for M10
    doc_hint = ""
    if module_key == "M10":
        doc_hint = (
            "NOTE: Fonus has these Aircraft Rules "
            "fully indexed: 1937, 1994, 2003, 2011, "
            "2025, RTR 2025, all CAR Sections 1-11, "
            "APM, and Advisory Circulars.\n"
            "If a specific rule is not found in the "
            "retrieved context below, state clearly "
            "which document was searched and that "
            "the rule was not found in retrieved "
            "sections — do NOT ask for permission.\n\n"
        )



    # Use broader candidate set for better retrieval quality.
    top_k = 6
    
    # Try hybrid search (BM25 + Vector)
    # Load BM25 nodes if available
    bm25_path = None
    if module_key == "M10":
        bm25_path = (
            PROJECT_ROOT / 
            "dgca_index_store" / 
            "bm25_nodes.pkl"
        )
    else:
        bm25_path = (
            PROJECT_ROOT / 
            "indexes" / 
            module_key / 
            "bm25_nodes.pkl"
        )
    
    if bm25_path and bm25_path.exists():
        # Hybrid search available
        with open(bm25_path, "rb") as f:
            bm25_nodes = pickle.load(f)
        
        # Vector retriever
        vector_retriever = index.as_retriever(
            similarity_top_k=top_k
        )
        
        # BM25 retriever
        bm25_retriever = BM25Retriever.from_defaults(
            nodes=bm25_nodes,
            similarity_top_k=top_k
        )
        
        # Combine both retrievers
        hybrid_retriever = QueryFusionRetriever(
            retrievers=[
                vector_retriever,
                bm25_retriever
            ],
            similarity_top_k=top_k,
            num_queries=1,
            mode="reciprocal_rerank",
            use_async=False
        )
        
        # Build query engine from hybrid retriever
        base_retriever = hybrid_retriever
        print(f"[Hybrid Search] {module_key}")
        
    else:
        # Fallback to vector only
        base_retriever = index.as_retriever(similarity_top_k=top_k)
        print(f"[Vector Search] {module_key}")

    tier = "free"
    current_usage = 0
    tier_limit = PRICING_CONFIG.get(tier, {}).get("daily_limit", 30)
    # If user_id is provided, check tier and rate limit
    if req.user_id:
        try:
            profile_res = supabase.table("profiles").select("tier, full_name, stream").eq("id", req.user_id).execute()
            if profile_res.data:
                tier = profile_res.data[0].get("tier", "free")
                raw_name = profile_res.data[0].get("full_name", "") or ""
                student_name = raw_name.strip().split(" ")[0] if raw_name.strip() else ""
                db_stream = profile_res.data[0].get("stream", "") or ""
                if db_stream and not req.stream:
                    user_stream = db_stream
                print(f"[Profile] name='{student_name}' | db_stream='{db_stream}' | req.stream='{req.stream}' | user_stream='{user_stream}'")
                
            # Check daily usage limit based on tier
            today = str(date.today())
            usage_res = supabase.table("daily_usage").select("*").eq("user_id", req.user_id).eq("date", today).execute()
            
            usage_row = usage_res.data[0] if usage_res.data else None
            if usage_row:
                current_usage = _usage_count_from_row(usage_row)

            tier_limit = PRICING_CONFIG.get(tier, {}).get("daily_limit", 30)

            if tier != "pro" and current_usage >= tier_limit:
                raise HTTPException(status_code=429, detail="Daily limit reached. Upgrade to Pro for unlimited questions.")

            _daily_usage_set_count(
                supabase,
                req.user_id,
                today,
                current_usage + 1,
                existing_row=usage_row,
            )
        except HTTPException:
            raise
        except Exception as e:
            print("Error checking/updating usage:", e)
            # Proceeding anyway or fail? Let's proceed but warn.
            pass

    # Process chat request
    try:
        if getattr(req, "allow_ai_knowledge", False):
            # FIX 2: Skip RAG entirely, trigger LLM fallback immediately
            response_text = ""
            answer_not_found = True
            has_relevant_sources = False
            existence_question = False
            source_nodes = []
            sources = []
        else:
            # Build messages with history
            messages = []
            
            if req.user_id:
                try:
                    # Dynamically fetching history handling both schemas to be safe
                    history = supabase.table("chat_history")\
                        .select("*")\
                        .eq("user_id", req.user_id)\
                        .eq("module", module_key)\
                        .order("created_at", desc=True)\
                        .limit(6)\
                        .execute()
                    
                    if history.data:
                        # Reverse to get chronological order
                        past = list(reversed(history.data))
                        # Add as conversation history
                        for msg in past:
                            if "question" in msg and "answer" in msg:
                                messages.append({
                                    "role": "user",
                                    "content": msg["question"]
                                })
                                messages.append({
                                    "role": "assistant",
                                    "content": msg["answer"]
                                })
                            elif "role" in msg and "content" in msg:
                                messages.append({
                                    "role": msg["role"],
                                    "content": msg["content"]
                                })
                except Exception as e:
                    print(f"History fetch error: {e}")
            
            # Add current user message last
            messages.append({
                "role": "user",
                "content": req.question
            })

            history_str = ""
            if hasattr(req, "history") and req.history:
                history_str = "\n".join([
                    f"{m.get('role','').upper()}: {m.get('content','')[:200]}"
                    for m in req.history[-4:]
                ])
            elif locals().get("messages"):
                history_str = "\n".join([
                    f"{m.get('role','').upper()}: {m.get('content','')[:200]}"
                    for m in locals().get("messages")[-5:-1]
                ])

            qa_prompt = PromptTemplate(
                "VERIFIED SOURCE CONTEXT:\n"
                "{context_str}\n"
                "────────────────────────\n"
                "QUESTION: {query_str}\n"
                "────────────────────────\n"
                "You are Fonus — DGCA CAR 66 AME mentor.\n"
                "Student: {STUDENT_NAME} | Module: {MODULE_NAME} | Stream: {STREAM}\n\n"
                "RULES:\n"
                "1. Answer starts immediately — no intro, no 'based on context'\n"
                "2. If the answer is in the context above: use it and cite the page number.\n"
                "3. If context is empty or thin: still answer at CAR 66 exam depth from aviation knowledge — sound like a mentor, not a search snippet.\n"
                "4. No long URLs or link dumps; no filler like 'according to the document'. One short line is OK if exact regulatory numbers are not in context: confirm wording in the current CAR on DGCA.\n"
                "5. Structure concept answers as: Direct answer → Mechanism → Aircraft example → AME relevance.\n"
                "6. End concept answers with one specific DGCA exam angle (Exam Focus style).\n"
                "7. Follow-ups (short, conversational): 2-3 sentences only, no Exam Focus.\n"
                "8. Off-topic: one warm redirect by name, nothing else.\n"
                "9. Never say 'not found' — teach, clarify, or redirect.\n"
                "10. For durations, validity periods, percentages, article/rule numbers — state ONLY "
                "facts supported by VERIFIED SOURCE CONTEXT above; if the context does not spell it "
                "out clearly, give the CAR 66 reasoning style but tell the student to verify the "
                "exact wording in the current DGCA CAR/publication.\n"
                f"11. Module sources available: {', '.join(_allowed_books[:4]) or module_key}\n\n"
                f"{doc_hint}"
                "CONVERSATION HISTORY:\n"
                f"{history_str or 'No previous messages.'}\n\n"
                "ANSWER:"
            )

            user_stream = (req.stream if hasattr(req, "stream") and req.stream else None) or "B1.1"

            # Return verified CAR 66 exam facts directly for syllabus/pattern questions.
            if is_syllabus_question(req.question):
                facts = get_exam_facts(module_key, user_stream)
                print(f"[GT DEBUG] message='{req.question}' | is_syllabus={is_syllabus_question(req.question)} | module_key={module_key} | user_stream={user_stream} | facts={facts}")
                if facts is not None:
                    gt_answer = format_ground_truth_answer(facts, student_name)
                    return {
                        "answer": gt_answer,
                        "source": [{
                            "source": "CAR 66 Issue III Rev 2",
                            "page": "Appendix I"
                        }],
                        "usage_remaining": "unlimited" if tier == "pro" else max(0, tier_limit - (current_usage + 1 if req.user_id else 0)),
                        "llm_used": "Ground Truth",
                        "topic_id": None,
                        "exam_priority": None
                    }

            qa_prompt_str = qa_prompt.template\
                .replace("{MODULE_NAME}", module_key or "General")\
                .replace("{STREAM}", user_stream or "B1.1")\
                .replace("{STUDENT_NAME}", student_name if req.user_id else "there")
            qa_prompt = PromptTemplate(qa_prompt_str)

            topic_id_hint, topic_name_hint, topic_hint_score = infer_topic_from_question(
                module_key, req.question
            )

            module_context_hints = {
                "M17A": "propeller blade pitch angle",
                "M17B": "propeller blade pitch angle", 
                "M16": "piston engine cylinder power",
                "M15": "gas turbine compressor turbine",
                "M12": "helicopter rotor blade system",
                "M11A": "aeroplane structure system",
                "M11B": "aeroplane structure system",
                "M9": "human factors maintenance error",
                "M8": "aerodynamics lift drag flight",
                "M7A": "maintenance practices procedure",
                "M6": "aircraft materials hardware corrosion",
                "M5": "digital electronic instrument system",
                "M4": "electronic semiconductor circuit",
                "M3": "electrical fundamental circuit",
                "M10": "aviation legislation regulation CAR",
            }

            hint = module_context_hints.get(module_key, "")

            # Only add hint for short queries; prefer precise topic terms when available.
            if topic_name_hint and len(req.question.split()) <= 7:
                search_query = f"{req.question} {topic_name_hint} {hint}".strip()
            elif hint and len(req.question.split()) <= 5:
                search_query = f"{req.question} {hint}"
            else:
                search_query = req.question

            print(f"[Query] {search_query}")
            
            question_lower = req.question.lower()
            
            # Detect conversational/greeting messages — skip RAG
            CONVERSATIONAL_PATTERNS = [
                'hi', 'hello', 'hey', 'thanks', 'thank you', 
                'ok', 'okay', 'got it', 'i see', 'sure', 'yes', 
                'no', 'great', 'good', 'nice', 'cool', 'bye',
                'how are you', 'what can you do', 'help me',
                'who are you', 'what are you'
            ]
            is_conversational = (
                question_lower.strip() in CONVERSATIONAL_PATTERNS or
                len(req.question.strip().split()) <= 2 and 
                not any(c in question_lower for c in [
                    'what', 'how', 'why', 'when', 'where', 
                    'explain', 'define', 'difference', 'describe'
                ])
            )

            if is_conversational:
                conversational_replies = {
                    'hi': 'Hello! Ask me anything about CAR 66 — I have all modules ready.',
                    'hello': 'Hello! Ask me anything about CAR 66 — I have all modules ready.',
                    'hey': 'Hey! What CAR 66 topic can I help you with?',
                    'thanks': 'You\'re welcome! Keep studying — ask me anything else.',
                    'thank you': 'You\'re welcome! Keep studying — ask me anything else.',
                    'ok': 'Got it! Ask your next CAR 66 question whenever you\'re ready.',
                    'okay': 'Got it! Ask your next CAR 66 question whenever you\'re ready.',
                    'got it': 'Great! Ask your next question whenever ready.',
                    'bye': 'Good luck with your CAR 66 prep! Come back anytime.',
                }
                reply = conversational_replies.get(
                    question_lower.strip(),
                    'I\'m here! Ask me any CAR 66 question and I\'ll find the answer from verified DGCA sources.'
                )
                return {
                    "answer": reply,
                    "source": [],
                    "usage_remaining": "unlimited",
                    "llm_used": "conversational"
                }
            is_comparison = any(phrase in question_lower for phrase in [
                'difference between', 'compare', 'vs', 'versus', 'contrast'
            ])

            if is_comparison:
                print(f"[Comparison Detected] {req.question}")
                q_clean = re.sub(r'^(what is the |what are the |explain the |can you explain the )', '', question_lower)
                term1, term2 = req.question, req.question

                # Extract exact technical bus names FIRST — before text splitting corrupts them
                import re as _re2
                _tech = _re2.findall(
                    r'arinc[\s-]?\d+|afdx|can[\s-]?bus|'
                    r'mil[\s-]?std[\s-]?\d+|rs[\s-]?\d+',
                    req.question.lower()
                )
                if len(_tech) >= 2:
                    term1 = _tech[0].strip()
                    term2 = _tech[1].strip()
                    print(f"[Comparison] Locked terms: {term1} vs {term2}")
                else:
                    if 'difference between' in q_clean and ' and ' in q_clean:
                        parts = q_clean.split('difference between')[1].split(' and ')
                        if len(parts) >= 2: term1, term2 = parts[0].strip(), ' '.join(parts[1:]).strip()
                    elif ' vs ' in q_clean:
                        parts = q_clean.split(' vs ')
                        term1, term2 = parts[0].strip(), parts[1].strip()
                    elif ' versus ' in q_clean:
                        parts = q_clean.split(' versus ')
                        term1, term2 = parts[0].strip(), parts[1].strip()
                    elif 'compare' in q_clean and ' and ' in q_clean:
                        parts = q_clean.split('compare')[1].split(' and ')
                        if len(parts) >= 2: term1, term2 = parts[0].strip(), ' '.join(parts[1:]).strip()
                    elif 'compare' in q_clean and ' with ' in q_clean:
                        parts = q_clean.split('compare')[1].split(' with ')
                        if len(parts) >= 2: term1, term2 = parts[0].strip(), ' '.join(parts[1:]).strip()
                    elif 'contrast' in q_clean and ' and ' in q_clean:
                        parts = q_clean.split('contrast')[1].split(' and ')
                        if len(parts) >= 2: term1, term2 = parts[0].strip(), ' '.join(parts[1:]).strip()

                if bm25_path and bm25_path.exists():
                    active_retriever = hybrid_retriever
                else:
                    active_retriever = index.as_retriever(similarity_top_k=top_k)
                
                nodes1 = active_retriever.retrieve(term1)
                nodes2 = active_retriever.retrieve(term2)
                
                seen = set()
                combined_nodes = []
                for n in nodes1 + nodes2:
                    if n.node.node_id not in seen:
                        seen.add(n.node.node_id)
                        combined_nodes.append(n)
                
                context_str = "\n\n".join([n.node.get_content() for n in combined_nodes[:6]])
                
                compare_prompt = (
                    "You are Fonus DGCA CAR 66 AME exam coach.\n"
                    f"The student asked: {req.question}\n\n"
                    "CRITICAL RULE: Answer ONLY the exact comparison asked.\n"
                    "If student asks about ARINC 664, answer about ARINC 664.\n"
                    "Never substitute a different standard.\n\n"
                    "VERIFIED SOURCE CONTEXT:\n"
                    f"{context_str}\n\n"
                    "If exact items not in context, answer from aviation knowledge — do not add any source label.\n"
                    "Start the comparison immediately. No intro sentence.\n\n"
                    f"ANSWER — comparing {term1} vs {term2}:"
                )

                class DummyResponse:
                    def __init__(self, t, n):
                        self.text = t
                        self.source_nodes = n
                    def __str__(self): return self.text

                response = None
                for llm_try, label_try in iter_completion_llms(
                    req.preferred_llm or "auto"
                ):
                    try:
                        resp_text = llm_try.complete(compare_prompt).text
                        response = DummyResponse(resp_text, combined_nodes[:6])
                        llm_name = label_try
                        break
                    except Exception as _rot_err:
                        if _is_rate_limit_error(_rot_err):
                            print(
                                f"[LLM rotate] {label_try} rate limited: "
                                f"{str(_rot_err)[:120]}"
                            )
                            continue
                        raise
                if response is None:
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            "All configured AI keys hit rate limits (Groq TPD is per org). "
                            "Try again later or set GEMINI_API_KEY / GOOGLE_API_KEY for Gemini fallback."
                        ),
                    )

            else:
                search_query_rag = search_query
                if hasattr(req, "history") and req.history:
                    recent = req.history[-3:]
                    context_prefix = " | ".join([
                        f"{m.get('role','')}: {m.get('content','')[:150]}"
                        for m in recent
                    ])
                    search_query_rag = (
                        f"[Context: {context_prefix}] Current question: {search_query}"
                    )
                response = None
                for llm_try, label_try in iter_completion_llms(
                    req.preferred_llm or "auto"
                ):
                    try:
                        query_engine = RetrieverQueryEngine.from_args(
                            retriever=base_retriever,
                            text_qa_template=qa_prompt,
                            llm=llm_try,
                            response_mode="compact",
                        )
                        response = query_engine.query(search_query_rag)
                        llm_name = label_try
                        break
                    except Exception as _rot_err:
                        if _is_rate_limit_error(_rot_err):
                            print(
                                f"[LLM rotate] {label_try} rate limited: "
                                f"{str(_rot_err)[:120]}"
                            )
                            continue
                        raise
                if response is None:
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            "All configured AI keys hit rate limits. "
                            "Try again later or set GEMINI_API_KEY for backup."
                        ),
                    )

            response_text = str(response)
            # Clean up source paths and replace with Cloudflare R2 links
            def _r2_replacer(match):
                return get_pdf_url(match.group(1))
            
            response_text = re.sub(
                r'[A-Za-z]:\\[^,\n]*\\([^\\,\n]+\.(?:pdf|txt))',
                _r2_replacer,
                response_text
            )
            # Strip markdown formatting — convert to plain readable text
            response_text = re.sub(r'\*\*(.+?)\*\*', r'\1', response_text)
            response_text = re.sub(r'\*(.+?)\*', r'\1', response_text)
            response_text = re.sub(r'#{1,6}\s+', '', response_text)
            response_text = re.sub(r'`(.+?)`', r'\1', response_text)
            response_text = re.sub(r'\n{3,}', '\n\n', response_text)

            source_nodes = getattr(response, "source_nodes", [])
            
            # Apply precise topic-aware relevance filter first.
            source_nodes = filter_relevant_nodes_precise(
                source_nodes,
                req.question,
                module_key,
                topic_id_hint,
                topic_name_hint
            )
            
            # Rebuild filtered context for LLM if nodes were filtered
            if source_nodes:
                filtered_context = "\n\n".join([
                    f"Source: {get_pdf_url(os.path.basename(n.metadata.get('file_name','?')))} "
                    f"p.{n.metadata.get('page_label','?')}\n"
                    f"{n.text}"
                    for n in source_nodes
                ])
            else:
                filtered_context = ""
            
            print(f"[Context] Using {len(source_nodes)} filtered source nodes")
            sources = []
            for node in source_nodes:
                metadata = getattr(node, "metadata", {})
                sources.append({
                    "source": metadata.get('file_name', 'Unknown'),
                    "page": (metadata.get('page_label') if metadata.get('page_label') and str(metadata.get('page_label')).lower() != 'unknown' else '')
                })

            answer_not_found = is_unhelpful_answer(response_text)
            
            has_relevant_sources = len(source_nodes) > 0
            alignment_score = compute_query_source_alignment(req.question, source_nodes)
            question_lower = req.question.lower()
            existence_question = any(
                phrase in question_lower for phrase in [
                    'does', 'exist', 'is there',
                    'do we have', 'is it present',
                    'can you find', 'is rule',
                    'does rule', 'does section'
                ]
            )

            inferred_from_query = detect_module(req.question)
            explicit_scope_target = resolve_explicit_scope_target(req.question)
            # Phrase-level syllabus route: clarify even when retrieval falsely "fits" the wrong module.
            forced_module_redirect = bool(
                explicit_scope_target
                and explicit_scope_target != module_key
            )
            low_confidence = (
                (has_relevant_sources and alignment_score < 0.18) or
                (not has_relevant_sources and len(req.question.split()) >= 3)
            )

            # If retrieval confidence is low, or the question clearly belongs in another module.
            if (
                (low_confidence or forced_module_redirect)
                and not is_syllabus_question(req.question)
            ):
                topic_hint_text = (
                    f" I think you may be asking about '{topic_name_hint}'"
                    if topic_name_hint else ""
                )
                clarify_sources = sources
                mentor_off_syllabus = (
                    alignment_score < 0.08
                    and len(req.question.split()) >= 4
                    and not has_car66_study_signals(req.question)
                    and not existence_question
                )
                if forced_module_redirect:
                    clarification = (
                        f"This topic fits {explicit_scope_target} better than {module_key} right now.{topic_hint_text}\n"
                        f"Please clarify what you need inside {module_key}, "
                        f"or switch to {explicit_scope_target} for a more accurate answer."
                    )
                elif (
                    low_confidence
                    and inferred_from_query != module_key
                    and inferred_from_query != "M7A"
                ):
                    clarification = (
                        f"I may be mixing topics for this query.{topic_hint_text}\n"
                        f"Please clarify with exact terms (for example: system/component/failure mode), "
                        f"or switch to {inferred_from_query} for a more accurate answer."
                    )
                elif mentor_off_syllabus:
                    clarification = (
                        "I'm geared for DGCA CAR 66 prep — syllabus concepts, faults, PYQ angles. "
                        f"Let's stay on {module_key}: paste a textbook line, acronym, symptom, "
                        "or DGCA wording you saw in class and I'll unpack it properly."
                    )
                    clarify_sources = []
                else:
                    clarification = (
                        f"I need one clearer keyword to return the exact section.{topic_hint_text}\n"
                        f"Please rephrase with specific terms like component name, process, or fault symptom."
                    )
                if forced_module_redirect and explicit_scope_target:
                    _clar_llm_out = f"Scope Clarification → {explicit_scope_target}"
                elif mentor_off_syllabus:
                    _clar_llm_out = "Mentor redirect (off-syllabus phrasing)"
                else:
                    _clar_llm_out = f"Retrieval Clarification (alignment {alignment_score:.2f})"

                return {
                    "answer": clarification,
                    "source": clarify_sources,
                    "usage_remaining": "unlimited" if tier == "pro" else max(0, tier_limit - (current_usage + 1 if req.user_id else 0)),
                    "llm_used": _clar_llm_out,
                    "topic_id": topic_id_hint,
                    "exam_priority": None
                }

        # --- Smart Not-Found: automatic two-layer system ---
        if answer_not_found and has_relevant_sources and existence_question:
            # Layer 2 — existence question with searched docs: report clearly
            doc_names = list(set([
                node.metadata.get('doc_name', 
                node.metadata.get('file_name', ''))
                for node in source_nodes
            ]))
            
            final_answer = (
                f"Based on my search of the Fonus "
                f"verified database, I could not find "
                f"this specific rule or provision in "
                f"the indexed documents.\n\n"
                f"Documents searched: "
                f"{', '.join(doc_names[:3])}\n\n"
                f"This strongly suggests that the "
                f"rule or provision you are asking "
                f"about may not exist in these "
                f"documents, or may be referenced "
                f"under a different number or name.\n\n"
                f"Recommendation: Verify directly at "
                f"dgca.gov.in or check the official "
                f"document index for the correct "
                f"rule number.\n\n"
                f"Exam Focus: DGCA tests accurate "
                f"rule identification — knowing which "
                f"rules exist and under which document "
                f"is as important as knowing their content."
            )
            response_text = final_answer
            # keep existing sources

        elif answer_not_found:
            # Layer 2 — LLM answers from aviation knowledge
            # then self-verifies before responding
            fallback_prompt = MODULE_FALLBACK_PROMPTS.get(
                module_key, DEFAULT_FALLBACK
            )
            try:
                from groq import Groq as GroqClient
                groq_keys = [
                    os.getenv(f"GROQ_CHAT_KEY_{i}", "") 
                    for i in range(1, 31)
                ]
                groq_keys = [k for k in groq_keys if k]

                fallback_answer = None
                for key in groq_keys:
                    if not key:
                        continue
                    try:
                        client = GroqClient(api_key=key)

                        # Build history context
                        history_context = ""
                        if hasattr(req, "history") and req.history:
                            history_lines = []
                            for msg in req.history[-4:]:
                                role = msg.get("role", "")
                                content = msg.get("content", "")[:300]
                                history_lines.append(
                                    f"{role.upper()}: {content}"
                                )
                            history_context = (
                                "\nCONVERSATION HISTORY:\n" + 
                                "\n".join(history_lines) + "\n"
                            )

                        fallback_instruction = (
                            f"You are Fonus — DGCA CAR 66 AME mentor. "
                            f"Student name: {student_name}. Module: {module_key}.\n"
                            "Speak like a knowledgeable senior AME — direct, warm, no fluff.\n"
                            "Answer from verified CAR 66 aviation knowledge only.\n"
                            "CRITICAL — CONVERSATION AWARENESS:\n"
                            "If the student says 'where i left off', 'continue', 'what next', "
                            "or any follow-up — look at the CONVERSATION HISTORY and return to "
                            "the last MODULE topic discussed. Ignore any off-topic question "
                            "that may have come before. Resume teaching the module topic.\n"
                            "For True/False: one word + one line reason.\n"
                            "For follow-ups: 2-3 sentences only, conversational.\n"
                            "For off-topic: one warm redirect by name, nothing else.\n"
                            "Never fabricate rule numbers, form numbers, or exact fees/limits. "
                            "If unsure on a specific number, teach the idea and one short line: confirm in the current CAR on DGCA.\n"
                            "Never say 'not found'.\n\n"
                        )

                        # Step 1 — LLM gives initial answer
                        step1_messages = [
                            {
                                "role": "system",
                                "content": (
                                    fallback_instruction
                                    + fallback_prompt
                                    + history_context
                                )
                            },
                            {
                                "role": "user",
                                "content": req.question
                            }
                        ]

                        step1_response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=step1_messages,
                            max_tokens=500,
                            temperature=0.2
                        )
                        initial_answer = (
                            step1_response.choices[0].message.content
                        )

                        # Step 2 — Self-verification pass
                        step2_messages = [
                            {
                                "role": "system",
                                "content": (
                                    "You are a DGCA CAR 66 aviation expert doing "
                                    "a quick accuracy check. "
                                    "Review the answer below for the given question. "
                                    "If it is accurate: return it as-is, improved if needed. "
                                    "If anything is wrong or uncertain: correct it. "
                                    "Keep it 3-5 sentences. Plain English. "
                                    "Do not add disclaimers or say 'I verified this'.\n"
                                    "Just return the best final answer."
                                )
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Question: {req.question}\n\n"
                                    f"Answer to verify:\n{initial_answer}"
                                )
                            }
                        ]

                        step2_response = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=step2_messages,
                            max_tokens=500,
                            temperature=0.1
                        )
                        verified_answer = (
                            step2_response.choices[0].message.content
                        )

                        # Clean markdown
                        verified_answer = re.sub(
                            r'\*\*(.+?)\*\*', r'\1', verified_answer
                        )
                        verified_answer = re.sub(
                            r'\*(.+?)\*', r'\1', verified_answer
                        )
                        verified_answer = re.sub(
                            r'#{1,6}\s+', '', verified_answer
                        )
                        verified_answer = re.sub(
                            r'\n{3,}', '\n\n', verified_answer
                        )

                        fallback_answer = verified_answer

                        # Clear sources — no source badges for AI answers
                        sources = []
                        break

                    except Exception as e:
                        print(f"[Fallback] Key failed: {str(e)[:60]}")
                        continue

                if fallback_answer:
                    response_text = fallback_answer
                else:
                    response_text = (
                        "I hit a temporary issue generating your answer. Retry in a moment — "
                        "or open your module PDF / DGCA CAR for the exact rule wording."
                    )
            
            except Exception as e:
                print(f"[Auto-fallback error] {e}")
                response_text = (
                    "Answer temporarily unavailable — please retry. "
                    "For exact regulatory text, use the DGCA verified sources."
                )

        # Save to chat history if user_id is provided
        if req.user_id:
            try:
                supabase.table("chat_history").insert({
                    "user_id": req.user_id,
                    "module": req.module,
                    "question": req.question,
                    "answer": response_text
                }).execute()
            except Exception as e:
                print("Failed to save chat history:", e)

    except HTTPException:
        raise
    except Exception as e:
        if _is_rate_limit_error(e):
            raise HTTPException(
                status_code=503,
                detail="AI rate limit — try again shortly or configure GEMINI_API_KEY.",
            ) from e
        raise HTTPException(status_code=500, detail="Error generating response: " + str(e))

    # Calculate remaining
    tier_limit = PRICING_CONFIG.get(tier, {}).get("daily_limit", 30)
    # We already added 1 if user_id was present (so current_usage doesn't have it, but we add 1 here)
    remaining_value = tier_limit - (current_usage + 1 if req.user_id else 0)
    remaining = "unlimited" if tier == "pro" else max(0, remaining_value)

    exam_focus = get_exam_focus(
        req.question, module_key, getattr(req, "stream", "")
    )
    
    if exam_focus:
        response_text = response_text + \
            f"\n\n📊 Exam Priority: {exam_focus}"

    return {
        "answer": response_text,
        "source": sources,
        "usage_remaining": remaining,
        "llm_used": llm_name
    }


@app.post("/chat/compact")
async def compact_chat(req: CompactRequest):
    try:
        conv = "\n".join([
            f"{m.get('role','user').upper()}: "
            f"{m.get('content','')[:400]}"
            for m in req.messages
        ])
        
        prompt = f"""You are analyzing a DGCA AME 
exam study session for Module {req.module}.

Conversation:
{conv}

Return ONLY valid JSON, no markdown, no extra text:
{{
  "summary": "2 sentence summary of what was studied",
  "weak_topics": ["topic if asked 2+ times or wrong"],
  "strong_topics": ["topic answered correctly quickly"]
}}"""

        llm, _ = get_llm_for_request("auto")
        from llama_index.core.llms import ChatMessage
        resp = llm.chat([
            ChatMessage(role="user", content=prompt)
        ])
        
        import json, re
        text = resp.message.content
        match = re.search(r'\{[\s\S]*?\}', text)
        result = json.loads(match.group()) if match \
            else {
                "summary": f"Studied {req.module} topics",
                "weak_topics": [],
                "strong_topics": []
            }
        
        # Save to Supabase if user logged in
        if req.user_id and supabase:
            try:
                from datetime import datetime
                supabase.table("module_progress") \
                    .upsert({
                        "user_id": req.user_id,
                        "module": req.module,
                        "weak_areas": result.get(
                            "weak_topics", []
                        ),
                        "strong_areas": result.get(
                            "strong_topics", []
                        ),
                        "last_studied": datetime.utcnow().isoformat()
                    }, on_conflict="user_id,module") \
                    .execute()
            except Exception:
                pass
        
        return result
        
    except Exception:
        return {
            "summary": f"Studied {req.module} topics",
            "weak_topics": [],
            "strong_topics": []
        }

@app.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    try:
        data = {
            "module": req.module,
            "type": req.type,
            "message": req.message
        }
        if req.user_id:
            data["user_id"] = req.user_id
            
        res = supabase.table("feedback").insert(data).execute()
        return {"status": "success"}
    except Exception as e:
        error_msg = str(e)
        if hasattr(e, 'code'):
            error_msg += f" (Code: {e.code})"
        if hasattr(e, 'details'):
            error_msg += f" - {e.details}"
        if hasattr(e, 'message'):
            error_msg += f" - {e.message}"
        print(f"Feedback Insert Error: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Database insert failed: {error_msg}")

@app.post("/progress/track")
async def track_progress(req: ProgressTrackRequest):
    if not req.user_id:
        return {"status": "skipped", "message": "No user_id provided"}
        
    try:
        prog_res = supabase.table("module_progress").select("*").eq("user_id", req.user_id).eq("module", req.module).execute()
        
        mode_col = ""
        if req.mode == "pyq":
            mode_col = "pyq_attempted"
        elif "ai" in req.mode:
            mode_col = "ai_attempted"
        elif "mind" in req.mode:
            mode_col = "mind_attempted"
        else:
            return {"status": "skipped", "message": "Unknown mode"}

        if prog_res.data:
            record = prog_res.data[0]
            updates = {
                "total_attempted": record.get("total_attempted", 0) + 1,
                mode_col: record.get(mode_col, 0) + 1
            }
            supabase.table("module_progress").update(updates).eq("id", record["id"]).execute()
        else:
            data = {
                "user_id": req.user_id,
                "module": req.module,
                "target_questions": req.target_questions,
                "total_attempted": 1,
                "pyq_attempted": 0,
                "ai_attempted": 0,
                "mind_attempted": 0
            }
            data[mode_col] = 1
            supabase.table("module_progress").insert(data).execute()
            
        return {"status": "success"}
    except Exception as e:
        print(f"Track Progress Error: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/progress/goal")
async def set_progress_goal(req: GoalRequest):
    try:
        prog_res = supabase.table("module_progress").select("*").eq("user_id", req.user_id).eq("module", req.module).execute()
        if prog_res.data:
            supabase.table("module_progress").update({"target_questions": req.target_questions}).eq("id", prog_res.data[0]["id"]).execute()
        else:
            supabase.table("module_progress").insert({
                "user_id": req.user_id,
                "module": req.module,
                "target_questions": req.target_questions,
                "total_attempted": 0,
                "pyq_attempted": 0,
                "ai_attempted": 0,
                "mind_attempted": 0
            }).execute()
        return {"status": "success"}
    except Exception as e:
        print(f"Goal Setup Error: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.get("/module-progress/{module_id}")
async def get_module_progress(module_id: str, user_id: Optional[str] = None, target: int = 0):
    if not user_id:
        return {"total_attempted": 0, "target_questions": target}
    try:
        prog_res = supabase.table("module_progress").select("*").eq("user_id", user_id).eq("module", module_id).execute()
        if prog_res.data:
            return prog_res.data[0]
        else:
            return {"total_attempted": 0, "target_questions": target}
    except Exception as e:
        print(f"Get Progress Error: {str(e)}")
        return {"total_attempted": 0, "target_questions": target}

@app.get("/usage")
async def get_usage(user_id: str):
    try:
        profile_res = supabase.table("profiles").select("tier").eq("id", user_id).execute()
        if not profile_res.data:
            raise HTTPException(status_code=404, detail="User not found")
            
        tier = profile_res.data[0].get("tier", "free")
        tier_limit = PRICING_CONFIG.get(tier, {}).get("daily_limit", 30)
        
        today = str(date.today())
        usage_res = supabase.table("daily_usage").select("*").eq("user_id", user_id).eq("date", today).execute()
        
        current_usage = (
            _usage_count_from_row(usage_res.data[0]) if usage_res.data else 0
        )

        return {
            "tier": tier,
            "today_usage": current_usage,
            "limit": "unlimited" if tier == "pro" else tier_limit,
            "remaining": "unlimited" if tier == "pro" else max(0, tier_limit - current_usage)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/modules")
async def get_modules():
    # Placeholder module list with stream mapping
    modules = [
        {"id": "M1", "name": "Mathematics", "streams": ["mechanical", "avionics"]},
        {"id": "M2", "name": "Physics", "streams": ["mechanical", "avionics"]},
        {"id": "M3", "name": "Electrical Fundamentals", "streams": ["mechanical", "avionics"]},
        {"id": "M4", "name": "Electronic Fundamentals", "streams": ["mechanical", "avionics"]},
        {"id": "M5", "name": "Digital Techniques / Electronic Instrument Systems", "streams": ["mechanical", "avionics"]},
        {"id": "M6", "name": "Materials and Hardware", "streams": ["mechanical", "avionics"]},
        {"id": "M7", "name": "Maintenance Practices", "streams": ["mechanical", "avionics"]},
        {"id": "M8", "name": "Basic Aerodynamics", "streams": ["mechanical", "avionics"]},
        {"id": "M9", "name": "Human Factors", "streams": ["mechanical", "avionics"]},
        {"id": "M10", "name": "Aviation Legislation", "streams": ["mechanical", "avionics"]},
        {"id": "M11", "name": "Aeroplane Aerodynamics, Structures and Systems", "streams": ["mechanical"]},
        {"id": "M12", "name": "Helicopter Aerodynamics, Structures and Systems", "streams": ["mechanical"]},
        {"id": "M13", "name": "Aircraft Aerodynamics, Structures and Systems", "streams": ["avionics"]},
        {"id": "M14", "name": "Propulsion", "streams": ["avionics"]},
        {"id": "M15", "name": "Gas Turbine Engine", "streams": ["mechanical"]},
        {"id": "M16", "name": "Piston Engine", "streams": ["mechanical"]},
        {"id": "M17", "name": "Propeller", "streams": ["mechanical"]}
    ]
    return {
        "modules": modules
    }


@app.get("/syllabus/{module_id}")
async def get_syllabus(module_id: str, stream: Optional[str] = None):
    """
    Returns syllabus topics for a module with stream-aware levels and question targets.
    Target = level × 150  (L1→150, L2→300, L3→450)
    """
    import json as _json

    syllabus_path = Path(__file__).parent / "data" / "exam_syllabus.json"
    if not syllabus_path.exists():
        raise HTTPException(status_code=404, detail="exam_syllabus.json not found")

    with open(syllabus_path, "r", encoding="utf-8") as f:
        syllabus = _json.load(f)

    module_data = syllabus.get(module_id)
    if not module_data:
        # Try uppercase
        module_data = syllabus.get(module_id.upper())
    if not module_data:
        raise HTTPException(status_code=404, detail=f"Module {module_id} not in syllabus")

    raw_topics = module_data.get("topics", {})
    topics_out: Dict[str, Any] = {}

    for topic_id, topic_data in raw_topics.items():
        # Stream-aware level resolution
        if stream:
            if "B1" in stream:
                level = topic_data.get("level_B1", topic_data.get("level_ALL", 0))
            elif "B2" in stream:
                level = topic_data.get("level_B2", topic_data.get("level_ALL", 0))
            elif stream.startswith("A"):
                level = topic_data.get("level_A", topic_data.get("level_ALL", 0))
            elif "B3" in stream:
                level = topic_data.get("level_B3", topic_data.get("level_ALL", 0))
            else:
                level = topic_data.get("level_ALL",
                         topic_data.get("level_B1",
                         topic_data.get("level_A", 0)))
        else:
            # No stream → pick highest available level
            level = max(
                topic_data.get("level_B1", 0),
                topic_data.get("level_B2", 0),
                topic_data.get("level_A", 0),
                topic_data.get("level_ALL", 0),
            )

        if level == 0:
            continue  # topic not applicable for this stream

        target = level * 150  # L1=150, L2=300, L3=450

        topics_out[topic_id] = {
            "name": topic_data.get("name", topic_id),
            "level": level,
            "target": target,
        }

    return {
        "module": module_id,
        "name": module_data.get("name", module_id),
        "topics": topics_out,
    }


_PLACEHOLDER_MCQ_OPT = re.compile(r"^(none|null|n/?a|--?|[.])\s*$", re.I)


def _meaningful_option_text(val) -> bool:
    """True if the option looks like real answer text (excludes OCR junk like lone 'None')."""
    if val is None:
        return False
    t = str(val).strip()
    if len(t) < 2:
        return False
    return _PLACEHOLDER_MCQ_OPT.fullmatch(t) is None


def _substantive_option_count(opts: dict) -> int:
    if not isinstance(opts, dict):
        return 0
    return sum(1 for v in opts.values() if _meaningful_option_text(v))


def _canonical_correct_key(opts: dict, raw) -> Optional[str]:
    """Match correct_answer letter key (handles 'A' vs 'a')."""
    if raw is None:
        return None
    ca = str(raw).strip().lower()
    if not ca:
        return None
    for key in (ca, ca[:1]):
        if key in opts and _meaningful_option_text(opts[key]):
            return key
    return None


def _practice_question_norm_stem(question: str) -> str:
    return " ".join(str(question).strip().lower().split())


def _practice_question_usable(q: dict) -> bool:
    if not q.get("question"):
        return False
    opts = q.get("options")
    if not isinstance(opts, dict):
        return False
    if _substantive_option_count(opts) < 3:
        return False
    return _canonical_correct_key(opts, q.get("correct_answer")) is not None


@app.get("/practice/questions/{module}")
async def get_practice_questions(
    module: str,
    count: int = Query(default=10, le=500),
    offset: int = 0
):
    import json
    
    modules_dir = PROJECT_ROOT / "data" / "Modules"
    module_dir = None
    if modules_dir.exists():
        for d in modules_dir.iterdir():
            if d.is_dir() and d.name.lower().startswith(module.lower()):
                module_dir = d
                break
                
    if not module_dir:
        raise HTTPException(status_code=404, 
            detail=f"Questions not found for module {module}")
            
    questions_file = module_dir / "processed" / "questions.json"
    
    if not questions_file.exists():
        raise HTTPException(status_code=404, 
            detail="Questions file not found for this module")
    
    with open(questions_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    questions = data.get("questions", [])
    seen_stems: set[str] = set()
    valid: list = []
    for q in questions:
        if not _practice_question_usable(q):
            continue
        stem = _practice_question_norm_stem(q["question"])
        if stem in seen_stems:
            continue
        seen_stems.add(stem)
        valid.append(q)

    total = len(valid)
    page = valid[offset:offset + count]
    
    return {
        "module": module,
        "total": total,
        "questions": page,
        "offset": offset,
        "count": len(page)
    }


@app.post("/practice/verify")
async def verify_answer(req: VerifyAnswerRequest):
    question = req.question
    options = req.options
    module = req.module
    correct_answer = (req.correct_answer or "").strip().lower()

    # --- Step 1: Determine correct answer ---
    # Use the correct_answer from the database directly.
    # Do NOT use RAG to determine correctness — retrieved chunks may
    # not contain the right section, causing wrong answers to be marked correct.
    if not correct_answer:
        # No correct answer in DB — ask LLM to determine it
        try:
            from groq import Groq as GroqClient
            groq_keys = [os.getenv(f"GROQ_CHAT_KEY_{i}", "") 
                         for i in range(1, 31)]
            groq_keys = [k for k in groq_keys if k]
            if groq_keys:
                client = GroqClient(api_key=groq_keys[0])
                options_text = "\n".join([
                    f"{k.upper()}) {v}" 
                    for k, v in options.items()
                ])
                determine_prompt = (
                    f"You are a DGCA CAR 66 AME exam expert.\n"
                    f"Question: {question}\n"
                    f"Options:\n{options_text}\n\n"
                    f"Which option is correct? "
                    f"Reply with ONLY the letter (a, b, c, or d) "
                    f"on the first line, then explain why in "
                    f"2-3 sentences on the next line."
                )
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system", 
                            "content": "You are a DGCA CAR 66 AME exam expert. Answer accurately."
                        },
                        {"role": "user", "content": determine_prompt}
                    ],
                    max_tokens=200,
                    temperature=0.1,
                    timeout=20
                )
                llm_response = resp.choices[0].message.content.strip()
                lines = llm_response.strip().split("\n")
                determined_answer = lines[0].strip().lower().replace(")", "").replace(".", "").strip()
                determined_answer = determined_answer[-1] if len(determined_answer) > 1 else determined_answer
                explanation = "\n".join(lines[1:]).strip() if len(lines) > 1 else llm_response
                correct_option_text = options.get(determined_answer, "")
                return {
                    "correct_answer": determined_answer,
                    "explanation": explanation,
                    "sources": [],
                    "llm_used": "Groq (Llama 3.3 70B) — AI determined"
                }
        except Exception as e:
            print(f"[verify] LLM answer determination failed: {e}")
        
        return {
            "correct_answer": "",
            "explanation": "Correct answer not available for this question.",
            "sources": [],
            "llm_used": "N/A"
        }

    # --- Step 2: Generate explanation using LLM (no RAG) ---
    correct_option_text = options.get(correct_answer, options.get(correct_answer.upper(), ""))
    explanation_prompt = (
        f"Question: {question}\n"
        f"Correct answer: {correct_answer.upper()}) {correct_option_text}\n"
        f"Explain why {correct_answer.upper()}) {correct_option_text} is correct "
        f"in 2-3 sentences. Be direct and clear. No preamble."
    )

    explanation = ""
    llm_name = "Groq (Llama 3.3 70B)"
    try:
        from groq import Groq as GroqClient
        groq_keys = [os.getenv(f"GROQ_API_KEY_{i}", "") for i in range(1, 11)]
        groq_keys = [k for k in groq_keys if k]
        if not groq_keys:
            legacy = os.getenv("GROQ_API_KEY", "")
            if legacy:
                groq_keys = [legacy]
        if groq_keys:
            client = GroqClient(api_key=groq_keys[0])
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a DGCA CAR 66 AME exam expert. Give concise, accurate explanations."},
                    {"role": "user", "content": explanation_prompt}
                ],
                max_tokens=200,
                temperature=0.1,
                timeout=20
            )
            explanation = resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[verify] Explanation LLM failed: {e}")
        explanation = f"Correct answer: {correct_answer.upper()}) {correct_option_text}"

    return {
        "correct_answer": correct_answer,
        "explanation": explanation,
        "sources": [],
        "llm_used": llm_name
    }


@app.post("/practice/answer")
async def submit_practice_answer(req: PracticeAnswerRequest):
    try:
        is_correct = req.selected_answer.strip().lower() == req.correct_answer.strip().lower()
        
        # Check if record exists
        prog_res = supabase.table("module_progress").select("*").eq("user_id", req.user_id).eq("module", req.module).execute()
        
        if prog_res.data:
            record = prog_res.data[0]
            total_questions = record.get("total_questions", 0) + 1
            correct_answers = record.get("correct_answers", 0) + (1 if is_correct else 0)
            score = (correct_answers / total_questions) * 100
            
            # --- Topic tracking (Part C) ---
            # Read existing topic_stats dict and increment the topic counter
            topic = req.topic or "general"
            current_stats = record.get("topic_stats") or {}
            current_stats[topic] = current_stats.get(topic, 0) + 1

            supabase.table("module_progress").update({
                "total_questions": total_questions,
                "correct_answers": correct_answers,
                "score": score,
                "topic_stats": current_stats,
            }).eq("id", record["id"]).execute()
        else:
            # New record — initialise topic_stats with this first answer
            topic = req.topic or "general"
            initial_topic_stats = {topic: 1}

            supabase.table("module_progress").insert({
                "user_id": req.user_id,
                "module": req.module,
                "total_questions": 1,
                "correct_answers": 1 if is_correct else 0,
                "score": 100.0 if is_correct else 0.0,
                "topic_stats": initial_topic_stats,
            }).execute()

        # Re-fetch updated stats
        updated_prog = supabase.table("module_progress").select("*").eq("user_id", req.user_id).eq("module", req.module).execute()
        stats = updated_prog.data[0] if updated_prog.data else {}

        return {
            "is_correct": is_correct,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/progress/{user_id}")
async def get_user_progress(user_id: str):
    try:
        prog_res = supabase.table("module_progress").select("*").eq("user_id", user_id).execute()
        progress = prog_res.data if prog_res.data else []
        
        return {
            "progress": progress
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/promo/check")
async def check_promo_code(req: PromoCheckRequest):
    try:
        result = supabase.table("promo_codes")\
            .select("*")\
            .eq("code", req.code.upper().strip())\
            .eq("active", True)\
            .execute()

        if not result.data:
            return {"valid": False, "message": "Invalid or expired promo code."}

        promo = result.data[0]

        # Check expiry
        if promo.get("expires_at"):
            from datetime import datetime, timezone
            expiry = datetime.fromisoformat(
                promo["expires_at"].replace("Z", "+00:00")
            )
            if datetime.now(timezone.utc) > expiry:
                return {"valid": False, "message": "This promo code has expired."}

        # Check usage limit
        if promo["used_count"] >= promo["max_uses"]:
            return {"valid": False, "message": "This promo code has reached its limit."}

        # Check if user already used this code
        if req.user_id:
            used = supabase.table("promo_redemptions")\
                .select("id")\
                .eq("user_id", req.user_id)\
                .eq("code", req.code.upper().strip())\
                .execute()
            if used.data:
                return {"valid": False, "message": "You have already used this promo code."}

        # Build benefit description
        days = promo["benefit_days"]
        module = promo["benefit_module"]
        if module == "ALL":
            benefit_desc = f"{days} days full access — all modules"
        else:
            benefit_desc = f"{days} days full access — this module"

        return {
            "valid": True,
            "benefit_days": days,
            "benefit_module": module,
            "type": promo["type"],
            "message": f"🎉 Code valid! Unlocks {benefit_desc}."
        }

    except Exception as e:
        print(f"Promo check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/promo/redeem")
async def redeem_promo_code(req: PromoRedeemRequest):
    try:
        from datetime import datetime, timezone, timedelta

        # Verify code
        result = supabase.table("promo_codes")\
            .select("*")\
            .eq("code", req.code.upper().strip())\
            .eq("active", True)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=400, detail="Invalid promo code")

        promo = result.data[0]

        # Check already redeemed
        used = supabase.table("promo_redemptions")\
            .select("id")\
            .eq("user_id", req.user_id)\
            .eq("code", req.code.upper().strip())\
            .execute()
        if used.data:
            raise HTTPException(status_code=400, detail="Code already redeemed")

        # Calculate expiry
        expires_at = datetime.now(timezone.utc) + timedelta(days=promo["benefit_days"])

        # Determine modules to unlock
        benefit_module = promo["benefit_module"]
        if benefit_module == "ALL":
            modules_to_unlock = [
                "M3","M4","M5","M6","M7A","M7","M8","M9","M10",
                "M11A","M11B","M11C","M12","M13","M14",
                "M15","M16","M17A","M17"
            ]
        else:
            # SINGLE = only the module the user is currently on
            modules_to_unlock = [req.module]

        # Grant access for each module
        for mod in modules_to_unlock:
            existing = supabase.table("module_access")\
                .select("id")\
                .eq("user_id", req.user_id)\
                .eq("module", mod)\
                .execute()

            if existing.data:
                supabase.table("module_access")\
                    .update({
                        "access_expires_at": expires_at.isoformat(),
                        "access_type": promo["type"]
                    })\
                    .eq("user_id", req.user_id)\
                    .eq("module", mod)\
                    .execute()
            else:
                supabase.table("module_access")\
                    .insert({
                        "user_id": req.user_id,
                        "module": mod,
                        "access_expires_at": expires_at.isoformat(),
                        "access_type": promo["type"]
                    })\
                    .execute()

        # Record redemption
        supabase.table("promo_redemptions").insert({
            "user_id": req.user_id,
            "code": req.code.upper().strip(),
            "module": benefit_module,
            "access_expires_at": expires_at.isoformat()
        }).execute()

        # Increment used count
        supabase.table("promo_codes")\
            .update({"used_count": promo["used_count"] + 1})\
            .eq("id", promo["id"])\
            .execute()

        return {
            "success": True,
            "message": f"Access unlocked for {promo['benefit_days']} days!",
            "expires_at": expires_at.isoformat(),
            "modules_unlocked": len(modules_to_unlock),
            "benefit_module": benefit_module
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Promo redeem error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/usage/track")
async def track_usage(req: UsageTrackRequest):
    """Track free user chat minutes or practice sets for the week."""
    try:
        from datetime import date, timedelta

        # Get current week start (Monday)
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        # Get existing usage record
        existing = supabase.table("free_usage")\
            .select("*")\
            .eq("user_id", req.user_id)\
            .execute()

        if existing.data:
            record = existing.data[0]
            record_week = date.fromisoformat(str(record["week_start"]))

            # Reset if new week
            if record_week < week_start:
                supabase.table("free_usage")\
                    .update({
                        "chat_minutes_used": 0,
                        "practice_sets_used": 0,
                        "week_start": week_start.isoformat()
                    })\
                    .eq("user_id", req.user_id)\
                    .execute()
                record["chat_minutes_used"] = 0
                record["practice_sets_used"] = 0

            # Update the right field
            if req.type == "chat_minutes":
                new_val = record["chat_minutes_used"] + req.amount
                supabase.table("free_usage")\
                    .update({"chat_minutes_used": new_val})\
                    .eq("user_id", req.user_id)\
                    .execute()
            elif req.type == "practice_set":
                new_val = record["practice_sets_used"] + req.amount
                supabase.table("free_usage")\
                    .update({"practice_sets_used": new_val})\
                    .eq("user_id", req.user_id)\
                    .execute()

        else:
            # Create new record
            supabase.table("free_usage").insert({
                "user_id": req.user_id,
                "chat_minutes_used": req.amount if req.type == "chat_minutes" else 0,
                "practice_sets_used": req.amount if req.type == "practice_set" else 0,
                "week_start": week_start.isoformat()
            }).execute()

        return {"success": True}

    except Exception as e:
        print(f"Usage track error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/usage/{user_id}")
async def get_usage(user_id: str):
    """Get current week usage for a user."""
    try:
        from datetime import date, timedelta

        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        existing = supabase.table("free_usage")\
            .select("*")\
            .eq("user_id", user_id)\
            .execute()

        if not existing.data:
            return {
                "chat_minutes_used": 0,
                "practice_sets_used": 0,
                "chat_hours_used": 0.0,
                "week_start": week_start.isoformat()
            }

        record = existing.data[0]
        record_week = date.fromisoformat(str(record["week_start"]))

        # If old week return zeros
        if record_week < week_start:
            return {
                "chat_minutes_used": 0,
                "practice_sets_used": 0,
                "chat_hours_used": 0.0,
                "week_start": week_start.isoformat()
            }

        return {
            "chat_minutes_used": record["chat_minutes_used"],
            "practice_sets_used": record["practice_sets_used"],
            "chat_hours_used": round(record["chat_minutes_used"] / 60, 1),
            "week_start": record["week_start"]
        }

    except Exception as e:
        print(f"Usage get error: {e}")
        raise HTTPException(status_code=500, detail=str(e))