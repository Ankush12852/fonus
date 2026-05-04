import streamlit as st
import os
import json
import random
import re
import time
import unicodedata
from pathlib import Path
from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.groq import Groq

# --- Configuration ---
PROJECT_ROOT = Path(__file__).resolve().parent
INDEX_PERSIST_DIR = PROJECT_ROOT / "dgca_index_store"
ENV_PATH = PROJECT_ROOT / ".env"
QUESTIONS_FILE = PROJECT_ROOT / "data" / "Modules" / "M10_aviation_legislation" / "processed" / "questions.json"

SYSTEM_PROMPT = """


▋IDENTITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are FONUS — an expert AI exam coach built exclusively for Indian AME students
preparing for DGCA CAR 66 licensing examinations.
built exclusively for Indian AME 
students preparing DGCA CAR 66 licensing exams.

You are NOT a general assistant.
You are NOT allowed to guess.
You are NOT allowed to answer before completing 
the mandatory thinking protocol below.

Your only job: Give the student the correct answer 
that will help them pass the DGCA exam.
Wrong answer = exam failure = safety risk.
This is non-negotiable.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▋MANDATORY PRE-ANSWER PROTOCOL
Every single response MUST complete all 5 gates.
No exceptions. No shortcuts.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GATE 1 — READ THE QUESTION EXACTLY
Extract the EXACT subject noun from the question.
Write it out internally before anything else.

Examples of common misreads — NEVER make these:
✗ "validity of AME licence" ≠ "validation of 
   foreign licence"
✗ "SHELL model" ≠ "SHEL model" (two L's always)
✗ "Category A privileges" ≠ "Category B1 privileges"
✗ "washout" ≠ "blade coning" ≠ "blade twist"
✗ "CAR-66" ≠ "CAR-145" ≠ "CAR-147"
✗ "Rule 61" ≠ general rule overview

If the question contains ANY of these pairs or 
similar ambiguous terms — slow down and confirm 
which specific one is being asked.

GATE 2 — CLASSIFY THE QUESTION TYPE
Identify exactly ONE primary type:
[ ] Rule/Regulation number question
[ ] CA Form question
[ ] Technical concept question
[ ] Procedure/Process question
[ ] Numerical limit/specification question
[ ] System operation question
[ ] Calculation question
[ ] Safety/Human factors question

The type determines which response FORMAT to use.
Wrong type = wrong format = incomplete answer.

GATE 3 — LOCATE THE SOURCE
Search sources in this strict order:

TIER 1 (use first, always):
→ CAR 66 Module documents (M1–M17)
→ Aircraft Rules 1937 (latest amendment)
→ CAR Sections (cite Section→Series→Part→Issue)
→ DGCA APM (Airworthiness Procedure Manual)
→ DGCA Advisory Circulars
→ EASA Part 66/145/147/M (where DGCA references)

TIER 2 (use only if Tier 1 incomplete):
→ FAA/EASA approved textbooks in CAR 66 syllabus
→ Jeppesen, EASA approved study materials
→ ICAO Annexes referenced by DGCA

TIER 3 — LAST RESORT:
→ General established aviation principle
→ MANDATORY: Flag every Tier 3 answer with:
  "⚠ From general aviation knowledge — 
   verify with official DGCA source before exam."

SOURCE VERIFICATION RULE:
If the source shown is "AI Knowledge Base" →
this means NO verified source was found.
In this case you MUST say:
"This is not confirmed in current Fonus sources.
Best reference: [specific document name].
Check dgca.gov.in directly."
NEVER present AI Knowledge Base answers as 
verified facts.

GATE 4 — CHECK KNOWN TRAP LIST
Before writing the answer, check if this topic 
appears in the known confusion list below.
If yes — address the trap explicitly in response.

KNOWN DGCA EXAM TRAPS:
→ SHELL model: S-H-E-L-L (TWO L's)
   L1 = Liveware self | L2 = Liveware others
   Never write SHEL. Never omit second Liveware.

→ Washout: Decrease in angle of incidence 
   ROOT TO TIP. Prevents tip stall at high AOA.
   NOT centrifugal twist. NOT coning. NOT flexing.

→ Category A privileges: Simple scheduled line 
   maintenance tasks ONLY. Cannot certify after 
   major repair. Cannot exercise privileges on 
   complex aircraft systems independently.

→ AME licence validity: 5 years from date of 
   issue (CAR 66). Revalidation requires 
   recent experience within preceding 2 years.
   NOT the same as type rating revalidation.

→ Type rating revalidation: Different from 
   licence validity. Requires recency experience
   or proficiency check — module specific.

→ CA Form 1: Release to service document.
   Certifies airworthiness after maintenance.
   CA Form 2: Application for approval — 
   different document entirely.

→ CAR-66 vs CAR-145 vs CAR-147:
   66 = Personnel licensing
   145 = Maintenance organisation approval
   147 = Training organisation approval
   Never mix these up.

→ Aircraft Rules 1937 rule numbers: Same number 
   may exist in multiple amendment years.
   Always specify which version you are citing.

→ CAME vs CAMO: DGCA uses CAMO (organisation).
   CAME is not standard DGCA terminology.

→ Foreign licence validation: Completely separate 
   topic from AME licence validity period.
   Read question carefully before answering.

→ Pressure ratio calculation: outlet/inlet.
   Always confirm which value is outlet vs inlet
   before dividing.

→ Scope questions: Investment advice, history 
   assignments, medical advice, legal advice —
   all outside Fonus scope. Decline clearly 
   in one sentence and redirect to aviation topic.

GATE 5 — SELECT AND USE CORRECT FORMAT
Use ONLY the format that matches the question type.
Every field in the format is mandatory.
Never skip Exam Focus. Never skip Source.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▋RESPONSE FORMATS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FORMAT A — TECHNICAL CONCEPT
─────────────────────────────
[Direct answer: 2-3 sentences. Plain language first,
technical definition second.]

Key Points:
- [Most exam-critical point]
- [Second point]
- [Third only if genuinely needed]

⚠ Common Trap: [If this topic has a known 
confusion area — state it explicitly]

Source: [Document | Section/Module | Page if known]
Exam Focus: [Exactly what DGCA tests on this topic]

FORMAT B — RULE/REGULATION NUMBER
───────────────────────────────────
Rule: [Exact number and full official title]
Under: [Exact Act/Rules/CAR with year]

Content:
[Exact regulatory content — verbatim if short,
key terms preserved if summarised]

Note: [If same rule number exists in multiple 
years — list all versions and clarify which 
is current for exam purposes]

Source: [Document | Year | Section]
Exam Focus: [Number, content, or both — 
what is specifically tested]

FORMAT C — CA FORM
────────────────────
Form: [CA Form number + full official name]
Purpose: [Exact regulatory purpose — one sentence]
Who Fills: [Exact designation]
Who Approves/Accepts: [Exact designation]
Validity: [Period if applicable]
Mandated by: [Exact CAR/Rule reference]

Source: [Document | Section]
Exam Focus: [What is tested about this form]

FORMAT D — NUMERICAL/LIMIT
────────────────────────────
Value: [EXACT number + unit — never approximate]

Applies to: [What aircraft/system/condition]
Variations: [If limit differs by category — 
list ALL categories and their limits]
Specified in: [Exact regulation]

⚠ Precision Note: [If rounding matters in exam]

Source: [Document | Section | Page]
Exam Focus: [Exact number is what is tested]

FORMAT E — PROCEDURE/PROCESS
──────────────────────────────
Process: [Official name of procedure]

Steps:
1. [Action] — [Responsible authority]
2. [Action] — [Responsible authority]
[Continue as required]

Timelines: [If regulation specifies — mandatory]
Documents: [Required paperwork if applicable]

Source: [Document | Section]
Exam Focus: [Which step/authority/timeline 
is most commonly tested]

FORMAT F — CALCULATION
───────────────────────
Formula: [State formula first — always]
Given: [List all given values with units]
Working:
Step 1: [substitution]
Step 2: [calculation]
Answer: [Final value + unit — bold]

Exam Variations: [Other ways this formula 
is tested in DGCA exams]

Source: [Document | Module | Section]

FORMAT G — SYSTEM OPERATION (M11-M17)
───────────────────────────────────────
System: [Full system name]

Principle: [How it works — 3-5 sentences]

Key Components:
- [Component] — [Function]
- [Component] — [Function]

Operating Limits: [Exact values if applicable]
Failure Indications: [If exam-relevant]
Safety Precautions: [If exam-relevant]

Source: [Document | Module | Section]
Exam Focus: [Operation/limit/failure — 
which aspect is tested]

FORMAT H — OUT OF SCOPE
────────────────────────
"This is outside Fonus scope.
[One sentence redirect to relevant aviation topic
the student could ask instead.]"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▋ABSOLUTE RULES — CANNOT BE OVERRIDDEN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Complete all 5 gates before every answer.
   No exceptions. Even for simple questions.

2. Never fabricate:
   Rule numbers | Form numbers | 
   Numerical limits | Page references |
   Regulatory content

3. Never present "AI Knowledge Base" as a 
   verified source. It is not a source.
   Treat it as: source not found → say so.

4. Never say "based on provided context"

5. Never skip Source field

6. Never skip Exam Focus field

7. Wrong answer = exam failure = safety risk.
   If uncertain → say so clearly.
   Uncertainty stated honestly > 
   confident wrong answer always.

8. SHELL has TWO L's. Always.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▋MODULE CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Student is currently studying: {MODULE_NAME}
License stream: {STREAM}

Prioritise answers relevant to this module 
and stream. If question belongs to a different 
module — answer it and note which module 
it actually belongs to.

"""

# --- Page Config ---
st.set_page_config(page_title="Fonus — DGCA AME Exam Coach", layout="centered")

# --- UI Header ---
st.title("Fonus — DGCA AME Exam Coach")
st.markdown("##### Powered by official DGCA source documents")

# --- Sidebar ---
svg_path = PROJECT_ROOT / "assets" / "fonus logo.svg"
if svg_path.exists():
    svg_content = svg_path.read_text()
    st.sidebar.markdown(
        f'<div style="width:120px; margin: 10px auto;">'
        f'{svg_content}'
        f'</div>',
        unsafe_allow_html=True
    )
else:
    st.sidebar.title("🛩️ Fonus")

st.sidebar.markdown("---")
st.sidebar.markdown("**powered by** Groq + LlamaIndex")

if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.messages = []
    st.rerun()


# --- Helper Functions ---

def clean_text(text):
    if not text:
        return text
    text = unicodedata.normalize('NFKD', str(text))
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text.strip()

def load_env():
    """Load API keys from .env into os.environ."""
    if not ENV_PATH.exists():
        return False
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()
    return True


@st.cache_resource
def get_index():
    """Load the index once and cache it."""
    if not INDEX_PERSIST_DIR.exists():
        return None
    try:
        storage_context = StorageContext.from_defaults(persist_dir=str(INDEX_PERSIST_DIR))
        index = load_index_from_storage(storage_context)
        return index
    except Exception:
        return None


@st.cache_resource
def get_all_indexes():
    """Load all available module indexes and cache them."""
    indexes = {}

    # M10 — special location
    m10_path = PROJECT_ROOT / "dgca_index_store"
    if m10_path.exists():
        try:
            sc = StorageContext.from_defaults(persist_dir=str(m10_path))
            indexes["M10"] = load_index_from_storage(sc)
        except Exception:
            pass

    # All other modules under indexes/
    indexes_dir = PROJECT_ROOT / "indexes"
    if indexes_dir.exists():
        for module_dir in sorted(indexes_dir.iterdir()):
            if module_dir.is_dir():
                try:
                    sc = StorageContext.from_defaults(persist_dir=str(module_dir))
                    indexes[module_dir.name] = load_index_from_storage(sc)
                except Exception:
                    pass

    return indexes


def detect_module(question: str) -> str:
    """Detect the most relevant AME module from the question text."""
    q = question.lower()
    if any(w in q for w in ["bernoulli", "lift", "drag", "airfoil", "aerodyn", "wing", "stall",
                             "chord", "camber", "pitching", "rolling", "yawing", "stability",
                             "vortex", "glide"]):
        return "M8"
    if any(w in q for w in ["human factor", "situational awareness", "fatigue", "stress", "crew",
                             "communication", "error", "complacency", "workload", "perception",
                             "memory", "attention"]):
        return "M9"
    if any(w in q for w in ["car 66", "car-66", "license", "licence", "car 145", "car 147",
                             "car 21", "airworthiness", "dgca", "form", "certificate",
                             "regulation", "rule", "authority", "approval"]):
        return "M10"
    if any(w in q for w in ["turbine", "gas turbine", "compressor", "combustion", "nozzle",
                             "thrust", "jet engine", "bypass", "turbofan", "turbojet"]):
        return "M15"
    if any(w in q for w in ["piston", "reciprocating", "cylinder", "carburetor", "magneto",
                             "spark plug", "crankshaft"]):
        return "M16"
    if any(w in q for w in ["electrical", "voltage", "current", "resistance", "ohm", "circuit",
                             "transformer", "generator", "battery", "capacitor"]):
        return "M3"
    if any(w in q for w in ["electronic", "transistor", "diode", "amplifier",
                             "semiconductor", "rectifier"]):
        return "M4"
    if any(w in q for w in ["digital", "binary", "logic gate", "microprocessor",
                             "data bus", "computer", "software"]):
        return "M5"
    if any(w in q for w in ["material", "alloy", "metal", "composite", "corrosion",
                             "hardware", "fastener", "rivet", "bolt", "steel", "aluminium"]):
        return "M6"
    if any(w in q for w in ["maintenance", "inspection", "tooling", "hangar", "safety",
                             "ppe", "workshop", "repair", "overhaul"]):
        return "M7A"
    if any(w in q for w in ["propeller", "blade", "pitch", "governor", "feather",
                             "constant speed"]):
        return "M17A"
    if any(w in q for w in ["helicopter", "rotor", "autorotation", "torque",
                             "anti-torque", "hover"]):
        return "M12"
    return "M10"  # default


def is_valid_question(q):
    question = q.get('question', '')
    options = q.get('options', {})
    
    # Filter out corrupted questions
    # 1. Question must be at least 10 characters
    if len(question) < 10:
        return False
    
    # 2. Must have at least 3 valid options
    valid_options = [
        v for v in options.values() 
        if v and len(v.strip()) > 1
    ]
    if len(valid_options) < 3:
        return False
    
    # 3. Detect corruption - if more than 3 
    #    non-ASCII characters in question, skip it
    non_ascii = sum(1 for c in question if ord(c) > 127)
    if non_ascii > 3:
        return False
    
    return True

@st.cache_data
def load_questions():
    """Load MCQ questions from questions.json once and cache."""
    if not QUESTIONS_FILE.exists():
        return None
    try:
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        all_questions = data.get("questions", [])
        initial_count = len(all_questions)
        
        filtered_questions = [q for q in all_questions if is_valid_question(q)]
        passed_count = len(filtered_questions)
        
        print(f"Question Filter: {passed_count} out of {initial_count} questions passed the quality filter.")
        
        data["questions"] = filtered_questions
        return data
    except Exception as e:
        print(f"Error loading questions: {e}")
        return None


def init_settings():
    """Initialize LlamaIndex settings."""
    from llama_index.llms.openai import OpenAI
    
    Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
    Settings.context_window = 6000
    Settings.num_output = 1024

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        Settings.llm = OpenAI(
            model="gpt-4o",
            api_key=openai_api_key,
            temperature=0.1,
            system_prompt=SYSTEM_PROMPT
        )
        return True
    return False


# --- App Logic ---
if not load_env():
    st.error("Error: `.env` file not found in project root.")
    st.stop()

if not init_settings():
    st.error("Error: `GROQ_API_KEY` missing in `.env`. Please add it to use the coach.")
    st.stop()

all_indexes = get_all_indexes()
if not all_indexes:
    st.error("No indexes found. Run `build_index.py` first.")
    st.stop()

# Show loaded modules in sidebar
loaded_modules = list(all_indexes.keys())
st.sidebar.markdown(f"**Modules loaded:** {', '.join(sorted(loaded_modules))}")

# --- Session State Defaults ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# MCQ Practice state
if "mcq_index" not in st.session_state:
    st.session_state.mcq_index = 0
if "mcq_score" not in st.session_state:
    st.session_state.mcq_score = 0
if "mcq_answered" not in st.session_state:
    st.session_state.mcq_answered = 0
if "mcq_submitted" not in st.session_state:
    st.session_state.mcq_submitted = False

# Mock Test state
if "mock_active" not in st.session_state:
    st.session_state.mock_active = False
if "mock_questions" not in st.session_state:
    st.session_state.mock_questions = []
if "mock_index" not in st.session_state:
    st.session_state.mock_index = 0
if "mock_score" not in st.session_state:
    st.session_state.mock_score = 0
if "mock_answers" not in st.session_state:
    st.session_state.mock_answers = []
if "mock_submitted" not in st.session_state:
    st.session_state.mock_submitted = False
if "mock_finished" not in st.session_state:
    st.session_state.mock_finished = False
if "mock_start_time" not in st.session_state:
    st.session_state.mock_start_time = None


# =============================================
# TABS
# =============================================
tab1, tab2, tab3 = st.tabs([
    "💬 Ask Anything",
    "📝 MCQ Practice",
    "🎯 Mock Test"
])


# =============================================
# TAB 1 — Ask Anything (existing chat)
# =============================================
with tab1:
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    if prompt := st.chat_input("Ask Fonus anything about DGCA AME modules..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Fonus is thinking..."):
                try:
                    q = prompt.lower()
                    expanded_q = prompt
                    form_match = re.search(r'ca[\s-]?form[\s-]?(\d+)|ca[\s-]?(\d+)', q)
                    if form_match:
                        num = form_match.group(1) or form_match.group(2)
                        expanded_q = f"{prompt} CA-{num} application form registration certificate"
                    else:
                        rule_match = re.search(r'rule[\s-]?(\d+\w*)', q)
                        if rule_match:
                            num = rule_match.group(1)
                            expanded_q = f"{prompt} Aircraft Rules rule {num} regulation"

                    # Detect module and route to the right index
                    detected_module = detect_module(prompt)
                    index = all_indexes.get(detected_module) or list(all_indexes.values())[0]

                    # Build module-scoped system prompt
                    user_stream = st.session_state.get("user_stream", "B1.1")
                    scoped_prompt = SYSTEM_PROMPT.replace(
                        "{MODULE_NAME}", detected_module
                    ).replace(
                        "{STREAM}", user_stream
                    )

                    # Apply scoped prompt to the LLM for this query
                    from llama_index.llms.openai import OpenAI as _OpenAI
                    scoped_llm = _OpenAI(
                        model="gpt-4o",
                        api_key=os.getenv("OPENAI_API_KEY", ""),
                        temperature=0.1,
                        system_prompt=scoped_prompt
                    )

                    query_engine = index.as_query_engine(
                        llm=scoped_llm,
                        similarity_top_k=5,
                        response_mode="compact"
                    )
                    response = query_engine.query(expanded_q)

                    full_response = str(response)
                    full_response = re.sub(
                        r'[A-Za-z]:\\[^,\n]*\\([^\\,\n]+\.(?:pdf|txt))',
                        r'\1',
                        full_response
                    )

                    def stream_response(text):
                        words = text.split(" ")
                        for word in words:
                            yield word + " "
                            time.sleep(0.03)

                    st.write_stream(stream_response(full_response))
                    # Extract source nodes from response
                    source_info = []
                    if hasattr(response, 'source_nodes') and response.source_nodes:
                        for node in response.source_nodes[:2]:
                            metadata = node.node.metadata or {}
                            file_name = metadata.get('file_name', '')
                            page = metadata.get('page_label',
                                   metadata.get('page', ''))
                            if file_name:
                                clean_name = Path(file_name).stem
                                clean_name = clean_name.replace('_', ' ')
                                if page:
                                    source_info.append(f"{clean_name} — Page {page}")
                                else:
                                    source_info.append(clean_name)

                    if source_info:
                        st.caption(f"📚 Module: {detected_module} | Source: {' | '.join(source_info)}")
                    else:
                        st.caption(f"📚 Source module: {detected_module}")
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                except Exception as e:
                    st.error(f"An error occurred: {e}")


# =============================================
# TAB 2 — MCQ Practice
# =============================================
with tab2:
    qdata = load_questions()

    if qdata is None:
        st.warning("⚠️ No questions found. Run `extract_questions.py` first.")
    else:
        questions = qdata.get("questions", [])
        total_q = len(questions)

        if total_q == 0:
            st.warning("⚠️ questions.json is empty. Run `extract_questions.py` first.")
        else:
            # Score display
            st.markdown(f"**Score: {st.session_state.mcq_score}/{st.session_state.mcq_answered}**")

            idx = st.session_state.mcq_index
            if idx >= total_q:
                st.success(f"🎉 You've completed all {total_q} questions!")
                st.markdown(f"**Final Score: {st.session_state.mcq_score}/{st.session_state.mcq_answered}**")
                if st.button("🔄 Restart Practice", key="mcq_restart"):
                    st.session_state.mcq_index = 0
                    st.session_state.mcq_score = 0
                    st.session_state.mcq_answered = 0
                    st.session_state.mcq_submitted = False
                    st.session_state.mcq_explanation = None
                    st.rerun()
            else:
                current_q = questions[idx]
                q_text = clean_text(current_q.get('question', 'No question text'))
                st.markdown(f"**Question {idx + 1} of {total_q}**")
                st.markdown(f"**{q_text}**")

                options = current_q.get("options", {})
                option_labels = []
                option_keys = []
                for key in ["a", "b", "c", "d"]:
                    if key in options:
                        opt_text = clean_text(options[key])
                        option_labels.append(f"{key.upper()}) {opt_text}")
                        option_keys.append(key)

                if option_labels:
                    correct_raw = current_q.get("correct_answer", "").strip().lower()
                    has_correct = bool(correct_raw)
                    disabled_radio = st.session_state.mcq_submitted or st.session_state.get(f"mcq_finding_{idx}", False)
                    
                    selected = st.radio(
                        "Choose your answer:",
                        option_labels,
                        key=f"mcq_radio_{idx}",
                        index=None,
                        disabled=disabled_radio
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        if not has_correct:
                            if not st.session_state.get(f"mcq_finding_{idx}", False):
                                if st.button("🔍 Find Answer from Sources", key=f"mcq_find_{idx}"):
                                    st.session_state[f"mcq_finding_{idx}"] = True
                                    st.session_state.mcq_explanation = None
                                    st.rerun()
                        else:
                            if not st.session_state.mcq_submitted:
                                if st.button("✅ Submit", key=f"mcq_submit_{idx}"):
                                    if selected is not None:
                                        selected_key = option_keys[option_labels.index(selected)]
                                        correct = correct_raw
                                        st.session_state.mcq_answered += 1

                                        if selected_key == correct:
                                            st.session_state.mcq_score += 1
                                        st.session_state.mcq_submitted = True
                                        st.session_state.mcq_explanation = None
                                        st.rerun()
                                    else:
                                        st.warning("Please select an answer first.")

                    if not has_correct and st.session_state.get(f"mcq_finding_{idx}", False):
                        if st.session_state.get("mcq_explanation") is None:
                            with st.spinner("Searching sources..."):
                                _mcq_module = detect_module(q_text)
                                _mcq_index = all_indexes.get(_mcq_module) or list(all_indexes.values())[0]
                                _mcq_qe = _mcq_index.as_query_engine(similarity_top_k=5, response_mode="compact")
                                response = _mcq_qe.query(q_text)
                                st.session_state.mcq_explanation = str(response)
                        
                        st.markdown(f"**📖 From Sources:**\n\n{st.session_state.mcq_explanation}")
                        
                        source = current_q.get("source_file", "Unknown")
                        st.caption(f"📄 Source: {source}")

                        with col2:
                            if st.button("➡️ Next Question", key=f"mcq_next_{idx}"):
                                st.session_state.mcq_index += 1
                                st.session_state[f"mcq_finding_{idx}"] = False
                                st.session_state.mcq_explanation = None
                                st.rerun()

                    if has_correct and st.session_state.mcq_submitted:
                        if selected is not None:
                            selected_key = option_keys[option_labels.index(selected)]
                        else:
                            selected_key = None

                        correct = correct_raw
                        correct_text = clean_text(options.get(correct, "N/A"))

                        if selected_key == correct:
                            st.success("✅ Correct!")
                        else:
                            st.error("❌ Wrong!")
                        
                        st.markdown(f"Correct answer: {correct.upper()}. {correct_text}")

                        if st.session_state.get("mcq_explanation") is None:
                            with st.spinner("Finding explanation from sources..."):
                                 _mcq_module = detect_module(q_text)
                                 _mcq_index = all_indexes.get(_mcq_module) or list(all_indexes.values())[0]
                                 _mcq_qe = _mcq_index.as_query_engine(similarity_top_k=5, response_mode="compact")
                                 response = _mcq_qe.query(f"Explain: {q_text}")
                                 st.session_state.mcq_explanation = str(response)

                        st.markdown(f"**📖 From Sources:**\n\n{st.session_state.mcq_explanation}")

                        source = current_q.get("source_file", "Unknown")
                        st.caption(f"📄 Source: {source}")

                        with col2:
                            if st.button("➡️ Next Question", key=f"mcq_next_{idx}"):
                                st.session_state.mcq_index += 1
                                st.session_state.mcq_submitted = False
                                st.session_state.mcq_explanation = None
                                st.rerun()
                else:
                    st.error("This question has no options. Skipping...")
                    if st.button("➡️ Skip", key=f"mcq_skip_{idx}"):
                        st.session_state.mcq_index += 1
                        st.session_state.mcq_explanation = None
                        st.rerun()


# =============================================
# TAB 3 — Mock Test
# =============================================
with tab3:
    qdata = load_questions()

    if qdata is None:
        st.warning("⚠️ No questions found. Run `extract_questions.py` first.")
    else:
        questions = qdata.get("questions", [])

        if len(questions) == 0:
            st.warning("⚠️ questions.json is empty. Run `extract_questions.py` first.")
        else:
            # ---- Test not started ----
            if not st.session_state.mock_active and not st.session_state.mock_finished:
                st.markdown("### 🎯 Mock Test — M10 Aviation Legislation")
                st.markdown("- **44 random questions** from the question bank")
                st.markdown("- **55 minutes** duration")
                st.markdown("- Pass mark: 75% (33 correct out of 44)")
                st.markdown("")

                if st.button("🚀 Start Test", key="mock_start"):
                    selected = random.sample(questions, min(44, len(questions)))
                    st.session_state.mock_questions = selected
                    st.session_state.mock_index = 0
                    st.session_state.mock_score = 0
                    st.session_state.mock_answers = []
                    st.session_state.mock_active = True
                    st.session_state.mock_finished = False
                    st.session_state.mock_submitted = False
                    st.session_state.mock_start_time = time.time()
                    st.rerun()

            # ---- Test in progress ----
            elif st.session_state.mock_active and not st.session_state.mock_finished:
                mock_qs = st.session_state.mock_questions
                mock_total = len(mock_qs)
                midx = st.session_state.mock_index

                # Timer
                elapsed = int(time.time() - st.session_state.mock_start_time)
                mins, secs = divmod(elapsed, 60)
                st.markdown(f"⏱️ **Time: {mins:02d}:{secs:02d}** &nbsp;&nbsp;|&nbsp;&nbsp; Question **{midx + 1}** of **{mock_total}**")

                if midx < mock_total:
                    mq = mock_qs[midx]
                    st.markdown(f"**{mq.get('question', 'No question text')}**")

                    options = mq.get("options", {})
                    option_labels = []
                    option_keys = []
                    for key in ["a", "b", "c", "d"]:
                        if key in options:
                            option_labels.append(f"{key.upper()}) {options[key]}")
                            option_keys.append(key)

                    if option_labels:
                        selected = st.radio(
                            "Your answer:",
                            option_labels,
                            key=f"mock_radio_{midx}",
                            index=None,
                            disabled=st.session_state.mock_submitted
                        )

                        col1, col2 = st.columns(2)

                        with col1:
                            if not st.session_state.mock_submitted:
                                if st.button("✅ Submit", key=f"mock_submit_{midx}"):
                                    if selected is not None:
                                        selected_key = option_keys[option_labels.index(selected)]
                                        correct = mq.get("correct_answer", "").strip().lower()
                                        is_correct = selected_key == correct

                                        if is_correct:
                                            st.session_state.mock_score += 1

                                        st.session_state.mock_answers.append({
                                            "question": mq.get("question", ""),
                                            "your_answer": f"{selected_key.upper()}) {options.get(selected_key, '')}",
                                            "correct_answer": f"{correct.upper()}) {options.get(correct, '')}",
                                            "is_correct": is_correct,
                                            "topic": mq.get("topic", "Unknown"),
                                            "source_file": mq.get("source_file", "Unknown"),
                                        })
                                        st.session_state.mock_submitted = True
                                        st.rerun()
                                    else:
                                        st.warning("Please select an answer first.")

                        if st.session_state.mock_submitted:
                            last_answer = st.session_state.mock_answers[-1]
                            if last_answer["is_correct"]:
                                st.success("✅ Correct!")
                            else:
                                st.error(f"❌ Wrong! Correct: **{last_answer['correct_answer']}**")

                            with col2:
                                if midx + 1 < mock_total:
                                    if st.button("➡️ Next", key=f"mock_next_{midx}"):
                                        st.session_state.mock_index += 1
                                        st.session_state.mock_submitted = False
                                        st.rerun()
                                else:
                                    if st.button("📊 See Results", key="mock_finish"):
                                        st.session_state.mock_active = False
                                        st.session_state.mock_finished = True
                                        st.rerun()

            # ---- Test finished ----
            elif st.session_state.mock_finished:
                mock_total = len(st.session_state.mock_questions)
                score = st.session_state.mock_score
                pct = round((score / mock_total) * 100) if mock_total > 0 else 0

                elapsed = int(time.time() - st.session_state.mock_start_time)
                mins, secs = divmod(elapsed, 60)

                st.markdown("### 📊 Mock Test Results")
                st.markdown(f"**Final Score: {score}/{mock_total}**")
                st.markdown(f"**Percentage: {pct}%**")
                st.markdown(f"**Time taken: {mins:02d}:{secs:02d}**")

                if pct >= 75:
                    st.success(f"🎉 Great job! You passed! (Required: 33/44, Your Score: {score}/{mock_total})")
                elif pct >= 50:
                    st.warning("⚠️ Close! Review the topics below.")
                else:
                    st.error("❌ Needs improvement. Study the topics below.")

                # Wrong answers
                wrong = [a for a in st.session_state.mock_answers if not a["is_correct"]]
                if wrong:
                    st.markdown("---")
                    st.markdown("### ❌ Incorrect Answers")
                    for i, wa in enumerate(wrong, 1):
                        with st.expander(f"{i}. {wa['question'][:80]}..."):
                            st.markdown(f"**Your answer:** {wa['your_answer']}")
                            st.markdown(f"**Correct answer:** {wa['correct_answer']}")
                            st.caption(f"📄 Source: {wa['source_file']}")

                    # Study topics
                    st.markdown("---")
                    st.markdown("### 📚 Study These Topics")
                    topics = list(set(wa["topic"] for wa in wrong if wa["topic"] != "Unknown"))
                    if topics:
                        for topic in topics:
                            st.markdown(f"- {topic}")
                    else:
                        st.markdown("- Review the incorrect answers above")
                else:
                    st.balloons()
                    st.success("🏆 Perfect score! No wrong answers!")

                st.markdown("")
                if st.button("🔄 Take Another Test", key="mock_retake"):
                    st.session_state.mock_active = False
                    st.session_state.mock_finished = False
                    st.session_state.mock_questions = []
                    st.session_state.mock_index = 0
                    st.session_state.mock_score = 0
                    st.session_state.mock_answers = []
                    st.session_state.mock_submitted = False
                    st.session_state.mock_start_time = None
                    st.rerun()
