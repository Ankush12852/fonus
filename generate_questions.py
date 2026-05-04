"""
Fonus — AI Question Generator
Generates exam-style MCQ questions for all modules
using LlamaIndex indexes and Groq LLM.
Target: 4000+ questions per module minimum.
Syllabus: CAR 66 Issue III Rev 2 dated 29 Sept 2025
"""
import os, sys, json, time, re, argparse
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

# Load .env
if ENV_PATH.exists():
    for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ.setdefault(k.strip(), v.strip())

parser = argparse.ArgumentParser()
parser.add_argument('module', help='Module name e.g. M6, M10, ALL')
args = parser.parse_args()
TARGET_MODULE = args.module.upper()

# ── Groq key rotator ──────────────────────────────────────────────────────────
class GroqRotator:
    def __init__(self):
        keys = []
        for i in range(1, 11):
            k = os.getenv(f"GROQ_INDEX_KEY_{i}", "")
            if k: keys.append(k)
        for i in range(1, 11):
            k = os.getenv(f"GROQ_API_KEY_{i}", "")
            if k and k not in keys: keys.append(k)
        legacy = os.getenv("GROQ_API_KEY", "")
        if legacy and legacy not in keys: keys.append(legacy)
        self.keys = keys
        self._i = 0
        print(f"Loaded {len(keys)} Groq key(s) for generation.")

    def get(self):
        return self.keys[self._i] if self.keys else None

    def rotate(self):
        self._i = (self._i + 1) % len(self.keys)

    def generate(self, prompt, retries=3):
        from groq import Groq
        for attempt in range(retries * len(self.keys)):
            key = self.get()
            if not key:
                print("No Groq keys available."); return None
            try:
                client = Groq(api_key=key)
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.7
                )
                return resp.choices[0].message.content
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    self.rotate()
                    time.sleep(2)
                elif "all keys" in str(e).lower():
                    print("  All Groq keys exhausted. Waiting 60s...")
                    time.sleep(60)
                else:
                    print(f"  Groq error: {str(e)[:80]}")
                    self.rotate()
        return None

# ── Complete CAR 66 Issue III Rev 2 Syllabus with detailed topics ──────────────
SYLLABUS = {
    "M3": [
        "3.1 Electron Theory — atomic structure, conductors semiconductors insulators",
        "3.2 Static Electricity and Conduction — electrostatic charges, laws of attraction repulsion",
        "3.3 Electrical Terminology — EMF, voltage, current, resistance, conductance, charge",
        "3.4 Generation of Electricity — light heat friction pressure chemical magnetism",
        "3.5 Sources of DC Electricity — primary secondary cells, lead acid, NiCd, lithium, internal resistance",
        "3.6 DC Circuits — Ohm's law, Kirchhoff's laws, series parallel circuits",
        "3.7a Resistance — specific resistance, Wheatstone bridge, potentiometer, rheostat",
        "3.7b Resistors — temperature coefficient, colour code, tolerance, wattage, thermistors, VDR",
        "3.8 Power — work energy power, dissipation, power formula calculations",
        "3.9 Capacitance and Capacitors — construction, types, capacitance calculations, time constants",
        "3.10a Theory of Magnetism — properties, magnetisation, demagnetisation, electromagnets",
        "3.10b Magnetomotive Force — flux density, permeability, hysteresis, eddy currents",
        "3.11 Inductance and Inductors — induction principles, mutual inductance, back EMF, Lenz's law",
        "3.12 DC Motor and Generator Theory — construction, output factors, series shunt compound motors",
        "3.13 AC Theory — sinusoidal waveform, RMS peak average values, single three phase",
        "3.14 RCL Circuits — phase relationship, impedance, power factor, true reactive apparent power",
        "3.15 Transformers — construction, losses, efficiency, turn ratio, three phase, autotransformer",
        "3.16 Filters — low pass high pass band pass band stop applications",
        "3.17 AC Generators — revolving armature, revolving field, star delta, permanent magnet",
        "3.18 AC Motors — synchronous induction, speed control, rotating field methods",
    ],
    "M4": [
        "4.1.1a Diodes — characteristics, P-N junction, forward reverse bias, parameters",
        "4.1.1b Diode Operation — rectifiers, clippers, clampers, LED, Zener, SCR, Schottky, varactor",
        "4.1.2a Transistors — PNP NPN construction, characteristics, testing",
        "4.1.2b Transistor Operation — amplifier classes A B C, bias, feedback, multistage circuits",
        "4.1.3a Integrated Circuits — logic and linear circuits, operational amplifiers",
        "4.1.3b Op-Amp Applications — integrator, differentiator, voltage follower, comparator",
        "4.2 Printed Circuit Boards — description, use, construction",
        "4.3a Servomechanisms Principles — open closed loop, feedback, null, overshoot, synchro systems",
        "4.3b Servomechanisms Construction — resolvers, differential synchros, E-I transformers, PID controller",
    ],
    "M5": [
        "5.1 Electronic Instrument Systems — cockpit layout, EFIS, ECAM, EICAS",
        "5.2 Numbering Systems — binary, octal, hexadecimal, decimal conversions",
        "5.3 Data Conversion — ADC, DAC, analogue digital signals, limitations",
        "5.4 Data Buses — ARINC 429, ARINC 629, aircraft Ethernet, MIL-STD-1553",
        "5.5 Logic Circuits — AND OR NOT NAND NOR XOR gates, truth tables, diagrams",
        "5.6a Computer Structure — CPU, RAM, ROM, PROM, memory types, terminology",
        "5.6b Computer Operation — bus systems, instruction words, memory devices, data storage",
        "5.7 Microprocessors — CPU operation, control unit, ALU, registers, clock",
        "5.8 Integrated Circuits — encoders, decoders, function and use",
        "5.9 Multiplexing — multiplexers, demultiplexers, operation and application",
        "5.10 Fibre Optics — advantages disadvantages, data bus, terminators, couplers, aircraft use",
        "5.11 Electronic Displays — CRT, LED, LCD principles and operation",
        "5.12 Electrostatic Sensitive Devices — ESD handling, risks, antistatic protection",
        "5.13 Software Management Control — airworthiness requirements, unapproved changes risks",
        "5.14 Electromagnetic Environment — EMC, HIRF, lightning protection",
        "5.15 Typical Electronic Digital Aircraft Systems — FMS, autopilot, ACARS, ADS-B",
    ],
    "M6": [
        "6.1 Ferrous Materials — alloy steels, testing, repair inspection procedures",
        "6.2 Non-Ferrous Materials — aluminium alloys, titanium, characteristics, testing",
        "6.3.1 Composite and Non-Metallic — CFRP, GFRP, characteristics, defect detection, repair",
        "6.3.2 Wooden Structures — construction, inspection, repair",
        "6.3.3 Fabric Covering — materials, inspection, repair",
        "6.4 Corrosion — chemical fundamentals, types: galvanic, intergranular, stress, fretting, prevention",
        "6.5.1 Screw Threads — types, designation, tolerances, standard threads",
        "6.5.2 Bolts Studs and Screws — types, grades, identification, torque values",
        "6.5.3 Locking Devices — split pins, lockwire, locknuts, tab washers",
        "6.5.4 Aircraft Rivets — types, identification, installation, inspection",
        "6.6 Pipes and Unions — identification, standard unions, installation",
        "6.7 Springs — types, application, testing",
        "6.8 Bearings — types, construction, use, installation",
        "6.9 Transmissions — gears, belts, chains, shafts",
        "6.10 Control Cables — types, construction, inspection, repair",
        "6.11 Electrical Cables and Connectors — types, identification, installation",
    ],
    "M7": [
        "7.1 Safety Precautions — aircraft and workshop safety, hazardous materials, fire prevention",
        "7.2 Workshop Practices — housekeeping, tools, equipment, safety",
        "7.3 Tools — hand tools, power tools, precision measuring instruments, torque wrenches",
        "7.5 Engineering Drawings — blueprint reading, schematics, standards, tolerances",
        "7.6 Fits and Clearances — types of fits, measurement, limits",
        "7.7 EWIS — electrical wiring interconnection system, harness installation, inspection",
        "7.8 Riveting — types, tools, installation, inspection",
        "7.9 Pipes and Hoses — installation, inspection, leak testing",
        "7.10 Springs — installation, testing",
        "7.11 Bearings — installation, inspection",
        "7.12 Transmissions — installation, inspection",
        "7.13 Control Cables — installation, rigging, tension adjustment",
        "7.14 Material Handling — sheet metal, composite, additive manufacturing",
        "7.16 Aircraft Weight and Balance — CG calculation, datum, moment, aircraft weighing",
        "7.17 Aircraft Handling and Storage — towing, jacking, mooring, storage",
        "7.18a Disassembly and Inspection — defect types, visual inspection, NDT techniques",
        "7.18b Repair and Assembly — structural repair manual, reassembly, troubleshooting",
        "7.19 Abnormal Events — lightning strike HIRF inspection, heavy landing inspection",
        "7.20 Maintenance Procedures — maintenance checks, task cards, work orders",
        "7.21 Documentation and Communication — logbooks, tech records, maintenance release, CRS",
        
    ],
    "M8": [
        "8.1 Physics of the Atmosphere — ISA, pressure altitude, density altitude, temperature lapse rate",
        "8.2 Aerodynamics — Bernoulli's principle, venturi effect, airfoil, lift drag generation",
        "8.3 Theory of Flight — lift drag thrust weight, angle of attack, stall, glide ratio",
        "8.4 High Speed Airflow — subsonic transonic supersonic, Mach number, wave drag, shock waves",
        "8.5 Flight Stability and Dynamics — static dynamic stability, longitudinal lateral directional stability",
    ],
    "M9": [
        "9.1 General — human factors in aviation maintenance, accidents incidents statistics",
        "9.2 Human Performance and Limitations — vision, hearing, information processing, memory",
        "9.3 Social Psychology — group dynamics, peer pressure, culture, leadership, teamwork",
        "9.4 Factors Affecting Performance — fitness, stress, fatigue, alcohol, medication, drugs",
        "9.5 Physical Environment — noise, fumes, lighting, climate, turbulence, confined spaces",
        "9.6 Tasks — physical and mental workload, time pressure, complacency, vigilance",
        "9.7 Communication — verbal written non-verbal, shift handover, work orders",
        "9.8 Human Error — error types, violations, error models, error prevention",
        "9.9 Safety Management — SMS, safety culture, reporting systems, investigation",
        "9.10 Dirty Dozen — 12 human factors preconditions, risk mitigation strategies",
    ],
    "M10": [
        "10.1 Regulatory Framework — ICAO, DGCA, CAR 66, CAR 145, CAR 147, CAR 21",
        "10.2 Certifying Staff — AME license categories, privileges, limitations, currency requirements",
        "10.3 Approved Maintenance Organisations — AMO approval, scope, quality system, requirements",
        "10.4 Independent Certifying Staff — authorizations, privileges, responsibilities",
        "10.5 Air Operations — operator certificate, airworthiness requirements, MEL",
        "10.6 Certification of Aircraft Parts and Appliances — type certificate, STC, AFMS, EASA Form 1",
        "10.7 Continuing Airworthiness — CAME, maintenance program, ADs, SBs, airworthiness review",
        "10.8 Oversight Principles — DGCA oversight, audits, findings, corrective actions",
        "10.10 Cybersecurity in Aviation Maintenance — threats, network security, software integrity",
    ],
    "M11A": [
        "11.1 Theory of Flight — aeroplane aerodynamics, flight controls, high lift devices",
        "11.2 Airframe Structures — general concepts, airworthiness, construction methods",
        "11.3 Airframe Structures Aeroplanes — fuselage, doors, windows, wings, stabilisers, nacelles",
        "11.4 Air Conditioning and Pressurisation — pressurisation, air supply, conditioning, warnings",
        "11.5 Instruments and Avionics — instrument systems ATA 31, autoflight, comms, nav systems",
        "11.6 Electrical Power ATA 24 — generation, distribution, batteries, external power",
        "11.7 Equipment and Furnishings — emergency equipment, cabin cargo layout ATA 25",
        "11.8 Fire Protection ATA 26 — detection systems, extinguishing systems, portable extinguishers",
        "11.9 Flight Controls ATA 27 — primary secondary controls, actuation, balancing rigging",
        "11.10 Fuel Systems ATA 28 — layout, handling, indication, warnings, balancing",
        "11.11 Hydraulic Power ATA 29 — system description, components, operation",
        "11.12 Ice and Rain Protection ATA 30 — de-icing, anti-icing, wipers, rain repellent",
        "11.13 Landing Gear ATA 32 — description, operation, air-ground sensing, tail protection",
        "11.14 Lights ATA 33 — navigation, landing, anti-collision, emergency lights",
        "11.15 Oxygen ATA 35 — chemical, gaseous, crew passenger systems",
        "11.16 Pneumatic Vacuum ATA 36 — systems, pumps, operation",
        "11.17 Water Waste ATA 38 — systems, corrosion",
        "11.18 On-Board Maintenance Systems ATA 45 — CFDS, ACMS",
        "11.19 Integrated Modular Avionics ATA 42 — IMA concept, system layout",
        "11.20 Cabin Systems ATA 44 — cabin management, entertainment",
        "11.21 Information Systems ATA 46 — aircraft information systems",
    ],
    "M12": [
        "12.1 Theory of Flight Rotary Wing — helicopter aerodynamics, rotor theory, autorotation",
        "12.2 Flight Control Systems ATA 67 — collective pitch, cyclic, anti-torque, mixing units",
        "12.3 Blade Tracking and Vibration Analysis ATA 18 — tracking methods, vibration types",
        "12.4 Transmission — gearboxes, drive shafts, freewheeling unit, tail rotor drive",
        "12.5 Airframe Structures ATA 51 — fuselage, tail boom, construction methods",
        "12.6 Air Conditioning ATA 21 — air supply, conditioning systems",
        "12.7 Instruments and Avionics — instrument systems, autoflight, comms, navigation",
        "12.8 Electrical Power ATA 24 — generation, distribution, batteries",
        "12.9 Equipment and Furnishings ATA 25 — emergency equipment, seats, flotation",
        "12.10 Fire Protection ATA 26 — detection, extinguishing, portable extinguishers",
        "12.11 Fuel Systems ATA 28 — layout, handling, indication",
        "12.12 Hydraulic Power ATA 29 — systems, components",
        "12.13 Ice and Rain Protection ATA 30 — de-icing anti-icing systems",
        "12.14 Landing Gear ATA 32 — fixed, retractable, sensors, operation",
        "12.15 Lights ATA 33 — navigation, landing, anti-collision lights",
        "12.17 Integrated Modular Avionics ATA 42 — IMA system layout",
        "12.18 On-Board Maintenance Systems ATA 45 — central maintenance computer, data loading",
        "12.19 Information Systems ATA 46 — aircraft information management",
    ],
    "M13": [
        "13.1 Theory of Flight — aeroplane and rotary wing aerodynamics, flight controls",
        "13.2 Structures General Concepts ATA 51 — structural fundamentals, airworthiness",
        "13.3 Autoflight ATA 22 — autopilot, autothrottle, automatic landing systems",
        "13.4 Communication Navigation ATA 23/34 — VHF HF SATCOM, VOR ILS GPS ADS-B",
        "13.5 Electrical Power ATA 24 — AC DC systems, generators, TRUs, batteries",
        "13.6 Equipment and Furnishings ATA 25 — emergency equipment, cabin layout",
        "13.7 Flight Controls — primary secondary, actuation, FBW, rotorcraft controls",
        "13.8 Instruments ATA 31 — ADI, HSI, EFIS, EICAS, ECAM",
        "13.9 Lights ATA 33 — navigation, landing, emergency lighting",
        "13.10 On-Board Maintenance Systems ATA 45 — CFDS, ACMS",
        "13.11 Air Conditioning Pressurisation ATA 21 — pressurisation, conditioning, warnings",
        "13.12 Fire Protection ATA 26 — detection, extinguishing systems",
        "13.13 Fuel Systems ATA 28/47 — layout, handling, indication, balancing",
        "13.14 Hydraulic Power ATA 29 — systems, operation",
        "13.15 Ice Rain Protection ATA 30 — de-icing anti-icing wiper systems",
        "13.16 Landing Gear ATA 32 — description, system, air-ground sensing",
        "13.17 Oxygen ATA 35 — crew passenger oxygen systems",
        "13.18 Pneumatic Vacuum ATA 36 — systems, pumps",
        "13.19 Water Waste ATA 38 — systems, corrosion",
        "13.20 Integrated Modular Avionics ATA 42 — IMA concept, layout",
        "13.21 Cabin Systems ATA 44 — cabin management, in-flight entertainment",
        "13.22 Information Systems ATA 46 — aircraft information systems",
    ],
    "M14": [
        "14.1a Turbine Engines — types, construction, operation, performance",
        "14.1b Auxiliary Power Units APU — function, operation, systems",
        "14.1c Piston Engines — types, construction, operation",
        "14.1d Electric and Hybrid Engines — principles, operation, components",
        "14.1e Engine Control — FADEC, EEC, fuel metering, control systems",
        "14.2 Electric Electronic Engine Indication — EGT, N1 N2, EPR, oil pressure temp",
        "14.3 Propeller Systems — fixed pitch, variable pitch, constant speed, feathering",
        "14.4 Starting and Ignition Systems — starter types, ignition, starting sequence",
    ],
    "M15": [
        "15.1 Fundamentals — Brayton cycle, thrust, bypass ratio, specific fuel consumption",
        "15.2 Engine Performance — thrust calculations, flat rating, performance curves",
        "15.3 Inlet — subsonic supersonic intakes, inlet ice protection, FOD",
        "15.4 Compressors — axial centrifugal types, surge stall, pressure ratio, bleed air",
        "15.5 Combustion Section — types, combustion process, fuel injectors, liner",
        "15.6 Turbine Section — axial turbines, cooling methods, tip clearance, NGVs",
        "15.7 Exhaust — nozzle types, thrust reversers, noise suppression",
        "15.8 Bearings and Seals — types, lubrication, carbon seals, labyrinth seals",
        "15.9 Lubricants and Fuels — oil types, fuel types, specifications, contamination",
        "15.10 Lubrication Systems — pressure feed, oil tank, cooler, filters, monitoring",
        "15.11 Fuel Systems — fuel control unit, FADEC, flow divider, burner manifold",
        "15.12 Air Systems — cooling, sealing, anti-icing, customer bleed",
        "15.13 Starting and Ignition Systems — air starter, ignition exciter, plugs, sequence",
        "15.14 Engine Indication Systems — EPR, EGT, RPM, fuel flow, oil pressure temp",
        "15.15 Alternate Turbine Constructions — contra-rotating, geared turbofan",
        "15.16 Turboprop Engines — reduction gearbox, propeller coupling, power turbine",
        "15.17 Turboshaft Engines — free power turbine, helicopter application",
        "15.18 APU — construction, operation, pneumatic electrical output, shutdown",
        "15.19 Power Plant Installation — engine mounts, firewalls, cowlings, QEC",
        "15.20 Fire Protection — fire zones, detection, extinguishing, fire handles",
        "15.21 Engine Monitoring and Ground Operation — run-up, test cell, trending, borescope",
        "15.22 Engine Storage and Preservation — short long term storage, inhibiting",
    ],
    "M16": [
        "16.1 Fundamentals — four stroke two stroke cycle, Otto cycle, valve timing",
        "16.2 Engine Performance — BHP, BMEP, volumetric efficiency, detonation, pre-ignition",
        "16.3 Engine Construction — crankcase, cylinders, pistons, connecting rods, crankshaft",
        "16.4.1 Carburettors — float type, pressure injection, icing, mixture control",
        "16.4.2 Fuel Injection Systems — continuous flow, direct injection, Bendix RSA",
        "16.4.3 Electronic Engine Control — FADEC, EEC, engine management systems",
        "16.5 Starting and Ignition Systems — magneto operation, timing, spark plugs, starter",
        "16.6 Induction Exhaust and Cooling Systems — air filter, manifold, muffler, baffles, cowl flaps",
        "16.7 Supercharging and Turbocharging — types, wastegate, intercooler, operation",
        "16.8 Lubricants and Fuels — oil grades, AVGAS types, fuel grades, contamination",
        "16.9 Lubrication Systems — wet dry sump, oil pump, cooler, filters, breather",
        "16.10 Engine Indication Systems — MP, RPM, EGT, CHT, oil pressure temp, fuel flow",
        "16.11 Power Plant Installation — engine mounts, baffles, cowling, firewalls",
        "16.12 Engine Monitoring and Ground Operation — run-up checks, mag check, leaning",
        "16.13 Engine Storage and Preservation — short long term, pickling, corrosion prevention",
        "16.14 Alternative Piston Engine Constructions — rotary Wankel, opposed, radial, inline",
    ],
    "M17": [
        "17.1 Fundamentals — propeller theory, blade angle, pitch, efficiency, slipstream",
        "17.2 Propeller Construction — materials, blade sections, hub types, markings",
        "17.3 Propeller Pitch Control — fixed pitch, ground adjustable, variable pitch, CSU",
        "17.4 Propeller Synchronising — synchrophaser, operation, benefits",
        "17.5 Propeller Ice Protection — fluid de-ice, electrical de-ice, anti-ice systems",
        "17.6 Propeller Maintenance — inspection, repair limits, tracking, balancing, overhaul",
        "17.7 Propeller Storage and Preservation — storage procedures, inhibiting, preservation",
    ],
}

# ── Load index ─────────────────────────────────────────────────────────────────
def load_index(module):
    try:
        from llama_index.core import StorageContext, load_index_from_storage, Settings
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from llama_index.llms.groq import Groq as GroqLLM

        Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
        idx_path = PROJECT_ROOT / "indexes" / module
        if not idx_path.exists():
            idx_path = PROJECT_ROOT / "dgca_index_store"
        storage = StorageContext.from_defaults(persist_dir=str(idx_path))
        index = load_index_from_storage(storage)
        return index.as_query_engine(similarity_top_k=5)
    except Exception as e:
        print(f"  Could not load index for {module}: {e}")
        return None

# ── Parse questions from LLM response ─────────────────────────────────────────
def parse_questions(text, topic, module):
    questions = []
    try:
        # Try JSON array first
        match = re.search(r'\[[\s\S]*\]', text)
        if match:
            data = json.loads(match.group())
            for q in data:
                if isinstance(q, dict) and q.get('question') and q.get('options'):
                    opts = q.get('options', {})
                    if len([v for v in opts.values() if v and str(v).strip()]) >= 3:
                        questions.append({
                            "question": str(q['question']).strip(),
                            "options": {
                                "a": str(opts.get('a', '')).strip(),
                                "b": str(opts.get('b', '')).strip(),
                                "c": str(opts.get('c', '')).strip(),
                                "d": str(opts.get('d', '')).strip(),
                            },
                            "correct_answer": str(q.get('correct_answer', 'a')).lower().strip(),
                            "explanation": str(q.get('explanation', '')).strip(),
                            "topic": topic,
                            "module": module,
                            "source": "ai_generated",
                            "generated_date": str(date.today()),
                        })
    except Exception:
        pass
    return questions

# ── Generate for one topic ─────────────────────────────────────────────────────
def generate_topic(module, topic, rotator, query_engine, batch=10):
    prompt = f"""Generate exactly {batch} DGCA CAR 66 {module} exam MCQ questions about:
"{topic}"

These are for Indian AME license exam preparation. Questions should be exam-level difficulty.
Reference: CAR 66 Issue III Rev 2, EASA module books, official DGCA sources.

Return ONLY a valid JSON array, no other text, no markdown:
[
  {{
    "question": "Full question text here?",
    "options": {{"a": "Option A", "b": "Option B", "c": "Option C", "d": "Option D"}},
    "correct_answer": "a",
    "explanation": "Brief explanation from source"
  }}
]"""

    # Try using index query engine first for source-grounded questions
    if query_engine:
        try:
            context_prompt = f"Based on the source documents, {prompt}"
            response = query_engine.query(context_prompt)
            text = str(response)
            qs = parse_questions(text, topic, module)
            if qs:
                return qs
        except Exception:
            pass

    # Fallback to direct Groq
    text = rotator.generate(prompt)
    if text:
        return parse_questions(text, topic, module)
    return []

# ── Load existing questions ────────────────────────────────────────────────────
def load_existing(out_file):
    if out_file.exists():
        try:
            data = json.loads(out_file.read_text(encoding='utf-8'))
            return data.get('questions', [])
        except Exception:
            pass
    return []

# ── Save questions ─────────────────────────────────────────────────────────────
def save_questions(out_file, questions):
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(
        json.dumps({"questions": questions}, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

# ── Process one module ─────────────────────────────────────────────────────────
def process_module(module, rotator):
    print(f"\n{'='*50}")
    print(f"Module: {module}")
    print(f"{'='*50}")

    topics = SYLLABUS.get(module, [])
    if not topics:
        print(f"  No syllabus defined for {module}, skipping.")
        return

    out_file = PROJECT_ROOT / "data" / "Modules" / module / "processed" / "questions.json"
    existing = load_existing(out_file)
    existing_texts = {q['question'].strip().lower() for q in existing}

    print(f"  Existing questions: {len(existing)}")
    print(f"  Target: 4000 minimum")
    print(f"  Topics to process: {len(topics)}")

    query_engine = load_index(module)
    all_questions = list(existing)
    new_count = 0

    # Calculate how many batches needed
    current = len(existing)
    target = 4000
    needed = max(0, target - current)
    batches_per_topic = max(2, needed // len(topics) // 10 + 1)

    for i, topic in enumerate(topics):
        topic_short = topic.split('—')[0].strip()
        print(f"\n  [{i+1}/{len(topics)}] {topic_short}...")

        for batch_num in range(batches_per_topic):
            qs = generate_topic(module, topic, rotator, query_engine, batch=10)
            added = 0
            for q in qs:
                if q['question'].lower().strip() not in existing_texts:
                    all_questions.append(q)
                    existing_texts.add(q['question'].lower().strip())
                    new_count += 1
                    added += 1

            print(f"    Batch {batch_num+1}: +{added} questions (total: {len(all_questions)})")

            if len(all_questions) >= target:
                break

            time.sleep(2)

        save_questions(out_file, all_questions)

        if len(all_questions) >= target:
            print(f"\n  ✅ Reached target of {target} questions!")
            break

    print(f"\n  Module {module} complete:")
    print(f"  New questions generated: {new_count}")
    print(f"  Total questions: {len(all_questions)}")
    save_questions(out_file, all_questions)

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    rotator = GroqRotator()
    if not rotator.keys:
        print("ERROR: No Groq keys found. Check .env")
        sys.exit(1)

    if TARGET_MODULE == "ALL":
        modules = list(SYLLABUS.keys())
        # Remove duplicates (M7 and M7A same content)
        modules = [m for m in modules if m in ['M3','M4','M5','M6','M7A','M8','M9','M10','M11A','M12','M13','M14','M15','M16','M17A']]
        print(f"Processing all {len(modules)} modules...")
        for m in modules:
            process_module(m, rotator)
    else:
        if TARGET_MODULE not in SYLLABUS:
            print(f"ERROR: No syllabus for {TARGET_MODULE}. Available: {list(SYLLABUS.keys())}")
            sys.exit(1)
        process_module(TARGET_MODULE, rotator)

    print("\n\nAll done! Run python check_questions.py to see updated counts.")

if __name__ == "__main__":
    main()