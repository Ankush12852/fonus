"""
Fonus Learning - M10 Query Script (LlamaIndex)
Loads vector index from dgca_index_store, runs chat with context + multi-LLM fallback.
"""

import os
import sys
from pathlib import Path

from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# --- Configuration ---
PROJECT_ROOT = Path(__file__).resolve().parent
INDEX_PERSIST_DIR = PROJECT_ROOT / "dgca_index_store"
ENV_PATH = PROJECT_ROOT / ".env"

SYSTEM_PROMPT = """CRITICAL INSTRUCTION: You must ONLY answer from 
   the source documents provided to you. If information 
   is not in the sources, say it is not available. 
   Never use your general training knowledge.

You are Fonus, an expert DGCA AME 
(Aircraft Maintenance Engineer) exam coach built for 
Indian aviation students preparing for all DGCA AME 
license modules.

You have access to official DGCA source documents 
covering all AME modules including Aviation 
Legislation, Aerodynamics, Electrical, Electronic, 
Digital Systems, Materials, Maintenance Practices, 
Basic Aerodynamics, Human Factors, Aeroplane 
Structures, Gas Turbine Engines, Piston Engines, 
Propellers, and all related CAR sections, Aircraft 
Rules, Advisory Circulars, Airworthiness Procedure 
Manuals, and DGCA Handbooks.

YOUR CHARACTER:
- Confident and direct like an experienced AME examiner
- You explain technical concepts clearly without 
  dumbing them down
- You know what the exam actually tests vs what the 
  regulation says
- You never waste a student's time

BEFORE YOU ANSWER:
1. Which module does this question belong to?
2. Which specific document has this answer?
3. Is there ambiguity? (Same rule in different years? 
   Same term in different modules?)
4. What does the DGCA exam test on this topic?

RESPONSE FORMAT - ALWAYS USE THIS:

[Direct answer in 2-4 confident sentences]

Key Points:
- [Most important point]
- [Second important point]
- [Third point if genuinely needed]

Source: [Exact document | Section/Part | Page]

Exam Focus: [What DGCA specifically tests on this - 
be precise]

HANDLING QUESTION TYPES:

CA Form questions:
- Exact purpose, who fills it, who approves it
- Which regulation mandates it
- If not in sources: say so, never guess

Rule number questions:
- Same number exists in Rules 1937/1994/2003/2011/2025
- Always specify which year you are answering from
- If not specified, use most current relevant version
- Give exact content, not paraphrase

CAR Section questions:
- Cite: Section → Series → Part
- Give actual regulatory content
- Include issue number if exam-relevant

Process/Procedure questions:
- Step by step
- Responsible authority at each step
- Include timelines if specified in regulation

Technical concept questions:
- Plain language explanation first
- Then technical regulatory definition
- Connect to aircraft safety significance
- Then what exam tests on it

Numerical/Limit questions:
- Exact number from source
- State unit clearly
- Which regulation specifies it
- If multiple limits for different categories, list all

Module guidance:
- M1/M2: Show calculations and formula working
- M3/M4/M5: Circuit principles and component functions
- M6: Material properties and specifications
- M7: Procedures, tools, safety precautions
- M8: Aerodynamic principles and effects
- M9: Human performance and error management
- M10: Exact regulatory requirements and form numbers
- M11-M17: System operation, limits, maintenance

STRICT RULES - NEVER BREAK:
1. ONLY use confirmed source document information
2. When NOT found in sources say:
   "This is not in my current sources. Refer books or dgca.gov.in directly."
3. NEVER guess or use general knowledge to fill gaps
4. NEVER fabricate form numbers, rule content, 
   or any numerical value
5. NEVER say "based on provided context"
6. If partially sure: clearly separate confirmed 
   vs uncertain information
7. Wrong answer in aviation = safety risk.
   Accuracy is non-negotiable."""


def load_env():
    """Load API keys from .env into os.environ."""
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


def set_llm_fallback():
    """
    Set Settings.llm to first available: 1. Groq, 2. Gemini, 3. Perplexity.
    Returns the name of the active model for printing.
    """
    # 1. Groq
    if os.getenv("GROQ_API_KEY"):
        try:
            from llama_index.llms.groq import Groq
            Settings.llm = Groq(
                model="llama-3.3-70b-versatile",
                api_key=os.getenv("GROQ_API_KEY"),
            )
            return "Groq (llama-3.3-70b-versatile)"
        except Exception:
            pass

    # 2. Gemini
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        try:
            from llama_index.llms.google_genai import GoogleGenAI
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            Settings.llm = GoogleGenAI(
                model="gemini-2.0-flash",
                api_key=api_key,
            )
            return "Gemini (gemini-2.0-flash)"
        except Exception:
            pass

    # 3. Perplexity
    if os.getenv("PERPLEXITY_API_KEY"):
        try:
            from llama_index.llms.perplexity import Perplexity
            Settings.llm = Perplexity(
                api_key=os.getenv("PERPLEXITY_API_KEY"),
                model="sonar",
                temperature=0.1,
            )
            return "Perplexity (sonar)"
        except Exception:
            pass

    return None


def expand_query(question):
    """Expand query with relevant keywords for 
    better retrieval"""
    q = question.lower()
    
    # CA Form number expansions
    import re
    form_match = re.search(r'ca[\s-]?form[\s-]?(\d+)|ca[\s-]?(\d+)', q)
    if form_match:
        num = form_match.group(1) or form_match.group(2)
        return f"{question} CA-{num} application form registration certificate"
    
    # Rule number expansions  
    rule_match = re.search(r'rule[\s-]?(\d+\w*)', q)
    if rule_match:
        num = rule_match.group(1)
        return f"{question} Aircraft Rules rule {num} regulation"
    
    return question


def get_chat_engine():
    """Builds and returns the LlamaIndex chat engine without the interactive CLI."""
    if not ENV_PATH.exists():
        print(f"ERROR: .env not found at {ENV_PATH}")
        return None
    load_env()

    # Same HuggingFace embeddings as ingest.py
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.context_window = 6000
    Settings.num_output = 1024

    active_model = set_llm_fallback()
    if not active_model:
        print("ERROR: No LLM available. Set GROQ_API_KEY, GEMINI_API_KEY, or PERPLEXITY_API_KEY in .env")
        return None

    try:
        storage_context = StorageContext.from_defaults(persist_dir=str(INDEX_PERSIST_DIR))
        index = load_index_from_storage(storage_context)
    except Exception as e:
        print(f"ERROR: Index not found. Run ingest.py first. Details: {e}")
        return None

    memory = ChatMemoryBuffer.from_defaults(token_limit=4000)

    chat_engine = index.as_chat_engine(
        chat_mode="context",
        memory=memory,
        system_prompt=SYSTEM_PROMPT,
        context_window=6000,
        verbose=False,
    )
    return chat_engine


def run_fonus_coach():
    print("--- 1. Initializing Fonus Chat Coach ---")

    chat_engine = get_chat_engine()
    if not chat_engine:
        return

    # To show what model is active like previously:
    if hasattr(Settings, 'llm') and hasattr(Settings.llm, 'metadata'):
        print(f"    Model active: {Settings.llm.metadata.model_name}")

    print(f"--- 2. Loading index from: {INDEX_PERSIST_DIR} ---")
    print("    Index loaded successfully.")

    print("\n--- Fonus Coach is online. Type 'quit' to exit ---\n")
    while True:
        try:
            prompt = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not prompt.strip():
            continue
        if prompt.strip().lower() == "quit":
            print("Goodbye.")
            break

        response = chat_engine.chat(expand_query(prompt))
        import re
        response_text = str(response)
        response_text = re.sub(
            r'[A-Za-z]:\\[^,\n]*\\([^\\,\n]+\.(?:pdf|txt))',
            r'\1',
            response_text
        )
        print(f"\nFonus: {response_text}\n")


if __name__ == "__main__":
    run_fonus_coach()
