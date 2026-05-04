"""
tag_questions.py — Topic Tagging Script for Fonus Practice Mode
================================================================
Reads exam_syllabus.json for reference, then for each module's
processed/questions.json, assigns a "topic" field like "6.4" or
"9.10" based on keyword matching against question text.

Usage:
    python backend/tag_questions.py

Output:
    M6: 45 questions tagged, 8 untagged (general)
    ...
"""

import json
import re
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYLLABUS_PATH = PROJECT_ROOT / "backend" / "data" / "exam_syllabus.json"
MODULES_DIR = PROJECT_ROOT / "data" / "Modules"

# ─── Keyword → Topic ID mapping ─────────────────────────────────────────────
# Each entry: (list_of_keywords_to_match_in_question_text, topic_id)
# Rules are checked IN ORDER — first match wins.
# Keywords are matched case-insensitively against question+options text.

TOPIC_RULES = [

    # ── Module 4 — Electronic Fundamentals ───────────────────────────────────
    (["transistor", "bjt", "fet", "mosfet",
      "amplifier", "gain", "diode",
      "zener diode", "led diode",
      "rectifier", "thyristor", "scr",
      "op amp", "operational amplifier",
      "pcb", "printed circuit board",
      "synchro", "servomechanism",
      "resolver", "selsyn"], "4.1"),

    # ── Module 5 — Digital Techniques ────────────────────────────────────────
    (["eprom", "eeprom", "prom", "ram memory",
      "rom memory", "cpu", "microprocessor",
      "binary", "octal", "hexadecimal",
      "logic gate", "and gate", "or gate",
      "nand gate", "nor gate", "flip flop",
      "data bus", "fibre optic", "arinc",
      "esds", "electrostatic sensitive",
      "efis", "ecam", "eicas", "fms display",
      "gps satellite", "adirs", "irs",
      "digital system", "boolean"], "5.6"),

    # ── Module 11 — Aeroplane Systems ────────────────────────────────────────
    (["pitot static", "altimeter", "asi",
      "vsi", "gyroscope", "attitude indicator",
      "artificial horizon", "hsi",
      "pressurisation", "pressurization",
      "bleed air", "air conditioning aircraft",
      "landing gear system", "flap system",
      "hydraulic system aircraft",
      "fuel system aircraft",
      "fire detection aircraft",
      "oxygen system aircraft",
      "anti ice aircraft",
      "de ice aircraft"], "11.4"),

    # ── Module 3 — Electrical Fundamentals ───────────────────────────────────
    (["electron theory", "electron cloud", "valence electron", "free electron",
      "bohr model", "atomic structure"], "3.1"),

    (["static electricity", "static charge", "static discharge",
      "electrostatic", "triboelectric", "static buildup"], "3.2"),

    (["ohm", "volt", "ampere", "resistance", "conductance", "impedance",
      "potential difference", "emf", "electromotive force",
      "siemens", "coulomb", "electrical terminology"], "3.3"),

    (["generation of electricity", "electromagnetic induction",
      "faraday", "lenz", "magnetic flux", "induce current"], "3.4"),

    (["battery", "lead acid", "nickel cadmium", "nicad", "dry cell",
      "wet cell", "cell voltage", "battery capacity", "ah rating",
      "primary cell", "secondary cell", "thermocoupl",
      "photovoltaic", "piezoelectric", "thermoelectric"], "3.5"),

    (["dc circuit", "series circuit", "parallel circuit",
      "kirchhoff", "voltage divider", "current divider",
      "wheatstone bridge"], "3.6"),

    (["resistor", "colour code", "color code", "fixed resistor",
      "variable resistor", "potentiometer", "rheostat",
      "tolerance", "wattage rating"], "3.7"),

    (["power formula", "watt", "horsepower", "power dissipation",
      "efficiency", "p = i", "p = v"], "3.8"),

    (["capacitor", "capacitance", "farad", "dielectric",
      "electrolytic capacitor", "ceramic capacitor",
      "charge capacitor", "discharge capacitor",
      "time constant", "rc circuit"], "3.9"),

    (["magnetism", "magnetic field", "permeability", "reluctance",
      "hysteresis", "flux density", "tesla", "weber",
      "permanent magnet", "electromagnet", "solenoid",
      "coercive force", "residual magnetism"], "3.10"),

    (["inductance", "inductor", "henry", "mutual inductance",
      "self inductance", "choke", "inductive reactance",
      "back emf", "counter emf"], "3.11"),

    (["dc motor", "dc generator", "commutator", "brush", "armature",
      "field winding", "compound motor", "series motor",
      "shunt motor", "back emf motor"], "3.12"),

    (["ac theory", "alternating current", "frequency", "hertz",
      "cycle", "rms", "peak voltage", "peak to peak",
      "phase angle", "power factor", "three phase", "single phase",
      "waveform", "phasor", "reactance"], "3.13"),

    (["rlc circuit", "resonance", "impedance circuit",
      "inductive circuit", "capacitive circuit",
      "resistive capacitive", "resistive inductive",
      "series resonance", "parallel resonance"], "3.14"),

    (["transformer", "turns ratio", "primary winding", "secondary winding",
      "step up", "step down", "auto transformer",
      "isolation transformer", "transformer efficiency"], "3.15"),

    (["filter", "low pass", "high pass", "bandpass", "band pass",
      "band reject", "notch filter", "cutoff frequency"], "3.16"),

    (["ac generator", "alternator", "stator", "rotor ac",
      "slip ring", "exciter", "voltage regulator ac",
      "three phase generator", "brushless alternator"], "3.17"),

    (["ac motor", "induction motor", "squirrel cage", "synchronous motor",
      "slip motor", "starting torque", "single phase motor",
      "capacitor start", "motor running"], "3.18"),

    # ── Module 6 — Materials & Hardware ──────────────────────────────────────
    (["ferrous", "steel", "iron", "carbon steel", "alloy steel",
      "stainless steel", "chrome molybdenum", "chrome vanadium",
      "nickel steel", "heat treatment", "annealing", "hardening",
      "tempering", "normalizing", "case hardening", "cementation",
      "nitriding", "carburizing", "quenching", "martensite",
      "brinell", "rockwell", "vickers", "shore scleroscope",
      "tensile strength", "yield strength", "elongation",
      "hardness test", "carbon content", "iron alloy",
      "ferrite", "austenite", "pearlite", "cementite",
      "aisi", "sae steel"], "6.1"),

    (["non-ferrous", "aluminum", "aluminium", "magnesium",
      "titanium", "copper", "brass", "bronze",
      "wrought aluminum", "cast aluminum", "aluminum alloy",
      "duralumin", "alclad", "4-digit index", "four digit",
      "heat treatable alloy", "clad", "anodiz",
      "zinc alloy", "tin alloy", "lead alloy"], "6.2"),

    (["composite", "fiberglass", "carbon fibre", "carbon fiber",
      "aramid", "kevlar", "resin", "epoxy", "matrix",
      "laminate", "sandwich structure", "honeycomb",
      "delamination", "void", "disbond", "core material",
      "glass cloth", "woven fabric", "non-metallic",
      "polymer", "prepreg", "dry layup", "wet layup",
      "autoclave", "bonded repair", "injection molding",
      "thermoplastic", "thermosetting", "dope material",
      "transparent plastic", "fabric repair",
      "fabric patch", "maule punch", "polyester fabric",
      "sealant", "adhesive", "structural adhesive"], "6.3"),

    (["corrosion", "galvanic", "oxidation", "rust",
      "intergranular", "stress corrosion", "fretting corrosion",
      "pitting corrosion", "exfoliation", "microbial",
      "corrosion inhibitor", "anodic", "cathodic",
      "dissimilar metal", "bimetallic", "sacrificial anode",
      "corrosion resistant", "corrosion prevention",
      "corrosion protection", "corrosion detection",
      "corrosion treatment", "surface corrosion",
      "filiform corrosion", "crevice corrosion",
      "corrosion prone area", "exhaust trail",
      "battery compartment corrosion", "bilge area"], "6.4"),

    (["fastener", "bolt", "nut", "screw", "rivet",
      "washer", "pin", "cotter", "clevis",
      "shear bolt", "tension bolt", "close tolerance",
      "an bolt", "ms bolt", "castellated nut",
      "self locking nut", "elastic stop nut",
      "jo-bolt", "lockbolt", "hi-lok",
      "blind rivet", "solid rivet", "pop rivet",
      "countersunk rivet", "universal head",
      "brazier head", "roundhead rivet",
      "flathead rivet", "ms20426", "ms20470",
      "ms20430", "field rivet", "2117", "2024 rivet",
      "aileron", "dowel", "taper pin",
      "shakeproof", "lockwasher", "plain washer",
      "check nut", "jam nut", "AN stands",
      "thread", "nf thread", "nc thread",
      "unf thread", "unc thread", "major diameter",
      "minor diameter", "pitch thread",
      "thread class", "dedendum", "addendum",
      "internal wrenching", "eye bolt",
      "hi-shear", "turnlock fastener", "dzus",
      "camloc", "airloc"], "6.5"),

    (["pipe", "tube", "union", "coupling", "fitting",
      "flare fitting", "flareless fitting",
      "flared tube", "single flare", "double flare",
      "bead and clamp", "swage fitting",
      "tube material", "aluminum tube", "stainless tube",
      "titanium tube", "hydraulic tube",
      "fuel line fitting", "oxygen tube",
      "pipe thread", "npt", "straight thread fitting",
      "b-nut", "sleeve", "ferrule",
      "corrosion resistant tubing",
      "high pressure tubing", "low pressure tubing"], "6.6"),

    (["spring", "helical spring", "torsion spring",
      "compression spring", "tension spring",
      "leaf spring", "spiral spring",
      "belleville spring", "washer spring",
      "chrome vanadium spring", "stainless spring",
      "inconel spring", "spring rate", "spring constant",
      "free length", "solid height", "coil spring"], "6.7"),

    (["bearing", "ball bearing", "roller bearing",
      "needle bearing", "plain bearing", "journal bearing",
      "sleeve bearing", "thrust bearing",
      "radial bearing", "angular contact",
      "tapered roller", "cylindrical roller",
      "bearing race", "inner race", "outer race",
      "ball retainer", "cage bearing",
      "bearing load", "axial load bearing",
      "radial load bearing", "bearing lubrication",
      "bearing clearance"], "6.8"),

    (["gear", "gear train", "spur gear", "helical gear",
      "bevel gear", "worm gear", "rack and pinion",
      "epicyclic gear", "planetary gear", "sun gear",
      "gear ratio", "idler gear", "compound gear",
      "stub tooth", "involute tooth",
      "addendum gear", "dedendum gear",
      "pitch circle", "diametral pitch",
      "transmission", "gearbox", "reduction gear",
      "drive shaft"], "6.9"),

    (["control cable", "wire rope", "aircraft cable",
      "7x7 cable", "7x19 cable", "cable splice",
      "cable tension", "cable turnbuckle",
      "swaged fitting", "nicopress", "cable guard",
      "pulley", "fairlead", "cable wear",
      "cable corrosion", "cable breakage",
      "cable rigging", "cable inspection"], "6.10"),

    (["electrical cable", "wire gauge", "awg",
      "aluminum wire", "copper wire",
      "terminal lug", "crimping", "connector",
      "circular mil", "ampacity", "wire bundle",
      "wire routing", "electrical connector",
      "cannon plug", "circular connector",
      "voltage drop wire", "current capacity wire",
      "wire diameter", "barrel plating",
      "galvanizing", "cadmium plating",
      "chrome plating", "zinc plating",
      "electroplating", "surface protection"], "6.11"),

    # ── Module 7 — Maintenance Practices ─────────────────────────────────────
    (["safety precaution", "ppe", "personal protective",
      "fire extinguisher", "fire safety", "hazardous material",
      "msds", "storage safety", "workshop safety",
      "oxygen safety", "fuel safety",
      "electrical safety maintenance", "lockout tagout",
      "tooling safety", "ground safety"], "7.1"),

    (["workshop practice", "workbench", "cleaning solvent",
      "degreaser", "cleaning procedure",
      "surface finish", "grinding", "drilling",
      "filing", "sawing", "hacksaw", "hacksawing",
      "blade length", "thread cutting"], "7.2"),

    (["tools", "torque wrench", "torque value",
      "calibration tool", "special tool", "hand tool",
      "power tool", "pneumatic tool", "hydraulic tool",
      "jig", "fixture", "micrometer", "vernier",
      "dial indicator", "feeler gauge",
      "precision measurement"], "7.3"),

    (["engineering drawing", "blueprint", "schematic",
      "title block", "tolerance drawing", "standard",
      "weld symbol", "surface finish symbol",
      "third angle projection", "first angle projection",
      "isometric", "exploded view"], "7.5"),

    (["fits and clearance", "tolerance", "clearance fit",
      "interference fit", "transition fit",
      "shrink fit", "press fit", "slip fit"], "7.6"),

    (["ewis", "electrical wiring interconnection",
      "wire installation", "wiring separation",
      "wiring inspection", "wiring protection",
      "chafe protection", "wiring routing maintenance"], "7.7"),

    (["riveting", "rivet installation", "rivet removal",
      "bucking bar", "rivet gun", "squeeze riveter",
      "rivet hole", "rivet pitch", "edge distance",
      "rivet spacing"], "7.8"),

    (["weight and balance", "centre of gravity", "cg",
      "datum", "moment", "arm", "basic empty weight",
      "operating empty weight", "payload", "useful load",
      "take off weight", "zero fuel weight",
      "cg limit", "cg envelope", "weigh aircraft",
      "jack aircraft", "balance procedure"], "7.16"),

    (["aircraft handling", "ground handling", "towing",
      "pushback", "aircraft storage", "jacking",
      "shoring", "mooring", "picketing",
      "defueling", "refueling procedure",
      "aircraft movement", "hangar storage"], "7.17"),

    (["disassembly", "inspection", "assembly procedure",
      "repair", "overhaul", "ndt", "non-destructive test",
      "dye penetrant", "magnetic particle", "eddy current",
      "ultrasonic inspection", "radiograph",
      "borescope", "visual inspection",
      "liquid penetrant", "x-ray inspection",
      "structural repair", "sheet metal repair",
      "damage assessment"], "7.18"),

    (["maintenance procedure", "airworthiness directive",
      "service bulletin", "maintenance manual",
      "component maintenance manual", "aircraft maintenance manual",
      "technical instruction", "troubleshooting",
      "fault isolation", "maintenance check",
      "scheduled maintenance", "unscheduled maintenance"], "7.20"),

    (["maintenance documentation", "tech log", "technical log",
      "work order", "job card", "maintenance record",
      "certificate of release to service", "crs",
      "sign off", "deferred defect",
      "ground deferred defect", "mel", "cdl",
      "communication maintenance", "maintenance reporting",
      "shift handover"], "7.21"),

    # ── Module 8 — Basic Aerodynamics ─────────────────────────────────────────
    (["atmosphere", "isa", "standard atmosphere",
      "pressure altitude", "density altitude",
      "temperature lapse rate", "tropopause",
      "stratosphere", "troposphere",
      "humidity aviation", "air density"], "8.1"),

    (["bernoulli", "venturi", "lift formula", "drag formula",
      "angle of attack", "aoa", "airfoil",
      "chord line", "camber", "leading edge", "trailing edge",
      "aspect ratio", "mean aerodynamic chord",
      "boundary layer", "laminar flow", "turbulent flow",
      "separation point", "lift coefficient",
      "drag coefficient", "centre of pressure",
      "vortex", "induced drag", "profile drag",
      "parasite drag", "total drag"], "8.2"),

    (["theory of flight", "stall", "stall speed",
      "critical angle", "lift to drag ratio",
      "glide ratio", "best glide", "best range",
      "rate of climb", "power required",
      "thrust required", "four forces",
      "weight balance", "control surface",
      "aileron", "elevator", "rudder",
      "flap", "slat", "spoiler",
      "ground effect", "washout wing",
      "swept wing", "delta wing"], "8.3"),

    (["high speed", "mach number", "sonic", "supersonic",
      "compressibility", "shock wave", "critical mach",
      "wave drag", "mach tuck", "transonic",
      "buffet", "area rule", "sweep effect",
      "supercritical wing", "subsonic"], "8.4"),

    (["stability", "static stability", "dynamic stability",
      "longitudinal stability", "lateral stability",
      "directional stability", "dutch roll",
      "phugoid", "spiral instability",
      "spiral dive", "dihedral", "anhedral",
      "keel effect", "weathercock", "neutral point",
      "metacentric height"], "8.5"),

    # ── Module 9 — Human Factors ──────────────────────────────────────────────
    (["general human factor", "human factor introduction",
      "aviation human factor", "human performance",
      "ergonomics", "anthropometry",
      "health and fitness aviation",
      "physical limitation", "sensory limitation"], "9.1"),

    (["perception", "vision", "hearing aviation",
      "illusion", "spatial disorientation",
      "workload", "mental workload", "attention",
      "memory", "short term memory", "long term memory",
      "information processing",
      "reaction time", "vigilance"], "9.2"),

    (["teamwork", "crew resource management", "crm",
      "group dynamics", "authority gradient",
      "leadership aviation", "followership",
      "assertiveness", "interpersonal skill",
      "motivation maintenance"], "9.3"),

    (["fatigue", "stress", "complacency", "pressure",
      "distraction", "time pressure",
      "workload factor", "shift work", "circadian rhythm",
      "night shift", "alcohol", "medication",
      "physical fitness", "diet aviation",
      "sleep deprivation", "hypoxia human factor"], "9.4"),

    (["noise aviation", "vibration human factor",
      "temperature environment", "lighting maintenance",
      "physical environment", "tool design",
      "workplace design", "confined space"], "9.5"),

    (["task complexity", "routine task", "non-routine task",
      "task interruption", "multitasking",
      "visual task", "cognitive task"], "9.6"),

    (["communication", "briefing", "debriefing",
      "shift handover communication", "written communication",
      "verbal communication", "non verbal", "language barrier",
      "miscommunication", "reporting culture",
      "open reporting", "just culture"], "9.7"),

    (["human error", "active error", "latent error",
      "slip", "lapse", "mistake", "violation",
      "error model", "swiss cheese model",
      "james reason", "error chain",
      "error recovery", "error prevention",
      "normalization of deviance",
      "complacency error"], "9.8"),

    (["safety management system", "sms", "safety culture",
      "incident reporting", "air safety report",
      "mandatory occurrence report", "mor",
      "safety investigation", "root cause",
      "corrective action", "risk management",
      "hazard identification", "risk assessment",
      "bowtie model"], "9.9"),

    (["dirty dozen", "shel model", "shell model",
      "lack of communication dirty", "distraction dirty",
      "lack of resources", "lack of teamwork",
      "fatigue dirty", "lack of assertiveness",
      "stress dirty", "lack of awareness",
      "lack of knowledge dirty", "norms",
      "lack of pressure", "pressure dirty dozen",
      "complacency dirty", "lack of standards",
      "12 factors", "twelve human factor"], "9.10"),

    # ── Module 10 — Aviation Legislation ──────────────────────────────────────
    (["icao", "chicago convention", "bilateral agreement",
      "annex", "regulatory framework", "dgca",
      "directorate general", "civil aviation authority",
      "aircraft rule 1937", "aircraft rule 1994",
      "aircraft rule 2003", "rule 61", "rule 62",
      "rule 133", "car section",
      "car 66", "car-66", "car 145", "car-145",
      "car 147", "car-147", "car 21", "car-21",
      "car m", "car-m", "part m"], "10.1"),

    (["ame licence", "ame license", "category a licence",
      "category b1", "category b2", "category c licence",
      "certifying staff", "crs signatory",
      "licence privileges", "rating",
      "licence validity", "revalidation licence",
      "experience requirement",
      "basic knowledge", "additional qualification",
      "temporary authorisation",
      "restricted privileges", "full privilege"], "10.2"),

    (["approved maintenance organisation", "amo",
      "maintenance organisation", "car 145 approval",
      "part 145", "maintenance approval",
      "quality system", "accountable manager",
      "maintenance procedures exposition",
      "maintenance organisation exposition", "moe",
      "quality manager", "independent audit",
      "sub-contractor"], "10.3"),

    (["independent certifying staff",
      "independent ics", "self certifying",
      "independent signatory"], "10.4"),

    (["air operator", "aoc", "maintenance programme",
      "maintenance control", "contracted maintenance",
      "minimum equipment list", "mel",
      "config deviation list", "cdl",
      "air operation regulation"], "10.5"),

    (["ca form", "form 1", "authorized release certificate",
      "arc", "airworthiness review certificate",
      "release to service document",
      "ca-1", "ca-2", "ca form 1",
      "easa form 1", "part approval tag",
      "serviceable tag", "unserviceable tag",
      "parts certification"], "10.6"),

    (["continuing airworthiness", "camo",
      "airworthiness directive", "ad",
      "service bulletin compliance",
      "maintenance programme",
      "maintenance check", "a check", "b check",
      "c check", "d check",
      "maintenance planning", "certificate of airworthiness",
      "certificate of registration", "airworthiness review"], "10.7"),

    (["dgca oversight", "audit", "regulatory inspection",
      "surveillance", "enforcement action",
      "oversight principle", "findings",
      "corrective action plan", "cap"], "10.8"),

    (["cybersecurity aviation", "cyber threat",
      "avionics cybersecurity", "data protection aviation",
      "network security aircraft", "acs",
      "aviation information security"], "10.10"),

    # ── Module 12 — Helicopter Aerodynamics ───────────────────────────────────
    (["autorotation", "autorotate", "engine failure helicopter",
      "autorotation entry", "autorotation descent",
      "collective lower", "flare autorotation",
      "rotor rpm autorotation", "rotary wing aerodynamics",
      "dissymmetry of lift", "retreating blade stall",
      "advancing blade", "retreating blade",
      "gyroscopic precession", "translating tendency",
      "translational lift", "effective translational lift",
      "vortex ring state", "settling with power",
      "blade flapping", "lead lag", "hunting",
      "blade coning", "washout rotor",
      "ground resonance", "rotor icing",
      "helicopter hover", "anti-torque",
      "tail rotor", "notar", "fenestron",
      "torque reaction helicopter"], "12.1"),

    (["collective pitch", "cyclic pitch control",
      "pitch change mechanism", "swashplate",
      "rotor head", "hub", "blade pitch link",
      "servo actuator helicopter",
      "mixing unit helicopter",
      "tandem rotor", "coaxial rotor",
      "yaw control helicopter"], "12.2"),

    (["blade tracking", "blade balance",
      "track and balance", "rotor track",
      "vibration analysis", "vibration absorber",
      "bifilar absorber", "rotor vibration",
      "blade sweep", "blade droop"], "12.3"),

    (["helicopter transmission", "rotor gearbox",
      "main gearbox", "tail rotor gearbox",
      "freewheeling unit", "overrunning clutch",
      "sprag clutch", "transmission chip detector",
      "driven plate", "flexible coupling helicopter",
      "driveshaft helicopter"], "12.4"),

    (["helicopter airframe", "fuselage helicopter",
      "skid", "landing gear helicopter",
      "monocoque helicopter", "semi-monocoque helicopter",
      "helicopter structure"], "12.5"),

    (["helicopter air conditioning", "environmental control helicopter",
      "pressurization helicopter",
      "bleed air helicopter"], "12.6"),

    (["helicopter electrical", "rotor electrical",
      "electrical power helicopter",
      "generator helicopter battery"], "12.8"),

    (["helicopter fire protection", "fire detection helicopter",
      "fire suppression helicopter",
      "halon helicopter"], "12.10"),

    (["helicopter fuel system", "fuel tank helicopter",
      "fuel pump helicopter", "fuel control helicopter"], "12.11"),

    (["helicopter hydraulic", "hydraulic actuator helicopter",
      "hydraulic pump helicopter",
      "helicopter flight control hydraulic"], "12.12"),

    (["helicopter landing gear", "skid gear",
      "wheels helicopter landing",
      "shock absorber helicopter",
      "oleo strut helicopter"], "12.14"),

    # ── Module 15 — Gas Turbine Engine ────────────────────────────────────────
    (["brayton cycle", "gas turbine fundamentals",
      "turbojet", "turbofan", "turboprop", "turboshaft",
      "bypass ratio", "engine cycle", "ideal gas turbine",
      "thermal efficiency engine",
      "propulsive efficiency", "jet engine type"], "15.1"),

    (["engine performance", "thrust", "sfc",
      "specific fuel consumption", "epr",
      "engine pressure ratio", "n1", "n2",
      "flat rating", "thrust rating",
      "takeoff thrust", "climb thrust",
      "derate"], "15.2"),

    (["air inlet", "engine intake", "inlet duct",
      "ram air intake", "variable inlet",
      "inlet anti-ice", "inlet temperature",
      "ram recovery", "inlet efficiency"], "15.3"),

    (["compressor", "axial compressor", "centrifugal compressor",
      "compressor stall", "compressor surge",
      "blade stall", "rotating stall",
      "compressor blade", "stator vane",
      "compressor stage", "pressure ratio compressor",
      "compressor efficiency", "variable stator",
      "bleed valve", "handling bleed",
      "inter stage bleed", "compressor materials",
      "titanium compressor blade"], "15.4"),

    (["combustion", "combustion chamber", "burner",
      "can type", "annular", "cannular",
      "flame tube", "fuel injector",
      "combustion efficiency", "rich extinction",
      "lean extinction", "primary zone",
      "dilution zone", "combustor liner cooling",
      "combustion pressure drop"], "15.5"),

    (["turbine blade", "turbine nozzle", "turbine vane",
      "turbine disc", "turbine cooling",
      "npt turbine", "ngt turbine",
      "high pressure turbine", "low pressure turbine",
      "turbine efficiency", "turbine material",
      "single crystal blade", "directionally solidified",
      "creep turbine blade", "blade erosion",
      "turbine tip clearance"], "15.6"),

    (["exhaust", "exhaust nozzle", "thrust reverser",
      "cascade reverser", "clamshell reverser",
      "target reverser", "variable area nozzle",
      "exhaust gas temperature", "egt",
      "exhaust mixture", "mixer nozzle",
      "noise suppressor", "chevron nozzle"], "15.7"),

    (["engine oil", "jet fuel", "kerosene",
      "avtur", "jeta", "jp4", "jp5", "jp8",
      "fuel spec", "contamination fuel",
      "fuel density", "fuel freezing point",
      "lubricating oil type", "synthetic oil"], "15.9"),

    (["lubrication system", "oil pressure",
      "oil temperature", "oil filter",
      "oil pump engine", "scavenge pump",
      "pressure pump", "oil cooler",
      "oil chip detector", "magnetic plug",
      "oil analysis", "drain plug engine",
      "oil consumption engine"], "15.10"),

    (["engine fuel system", "fuel control unit", "fcu",
      "hydromechanical fuel control",
      "fadec", "full authority digital", "hmu",
      "fuel metering unit", "pressurizing valve",
      "flowdivider", "dump valve engine",
      "fuel flow schedule", "acceleration schedule",
      "deceleration schedule", "datum valve",
      "power management"], "15.11"),

    (["ignition system turbine", "igniters",
      "exciter unit", "high energy ignition",
      "capacitor discharge ignition",
      "igniter plug", "starting sequence",
      "light up speed", "starter turbine",
      "air turbine starter", "cartridge starter",
      "internal cooling", "engine starting"], "15.13"),

    (["engine indication", "egt indicator",
      "n1 indicator", "n2 indicator",
      "oil pressure gauge engine",
      "oil temperature gauge", "vibration monitor",
      "engine health monitoring", "eecu",
      "eec", "engine monitor"], "15.14"),

    (["engine monitoring", "ground run", "engine run",
      "engine test", "power assurance",
      "trim", "engine trim",
      "idle speed setting", "max speed check",
      "engine log", "borescope inspection",
      "ttl", "time since overhaul", "since new",
      "engine change", "qad"], "15.21"),

    # ── Fallback extras ───────────────────────────────────────────────────────
    # (Keep general last so more specific rules win)
]


# ─── Helper ───────────────────────────────────────────────────────────────────

def build_search_text(q: dict) -> str:
    """Combine question text + all option texts for keyword scanning."""
    parts = [q.get("question", "")]
    for v in q.get("options", {}).values():
        if v:
            parts.append(str(v))
    return " ".join(parts).lower()


def assign_topic(q: dict) -> str:
    """Return the best matching topic ID, or 'general'."""
    text = build_search_text(q)
    for keywords, topic_id in TOPIC_RULES:
        for kw in keywords:
            if kw in text:
                return topic_id
    return "general"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not MODULES_DIR.exists():
        print(f"ERROR: Modules directory not found: {MODULES_DIR}")
        return

    # Load syllabus for reference
    syllabus = {}
    if SYLLABUS_PATH.exists():
        with open(SYLLABUS_PATH, "r", encoding="utf-8") as f:
            syllabus = json.load(f)
        print(f"Loaded syllabus with {len(syllabus)} modules.\n")
    else:
        print(f"WARNING: Syllabus not found at {SYLLABUS_PATH}. Continuing without validation.\n")

    total_tagged = 0
    total_untagged = 0

    for module_dir in sorted(MODULES_DIR.iterdir()):
        if not module_dir.is_dir():
            continue

        questions_file = module_dir / "processed" / "questions.json"
        if not questions_file.exists():
            continue

        with open(questions_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        questions = data.get("questions", [])
        if not questions:
            print(f"{module_dir.name}: No questions found — skipping.")
            continue

        tagged = 0
        untagged = 0

        for q in questions:
            topic_id = assign_topic(q)
            q["topic"] = topic_id        # overwrite or add "topic" field
            if topic_id == "general":
                untagged += 1
            else:
                tagged += 1

        # Save back
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        total_tagged += tagged
        total_untagged += untagged
        print(f"{module_dir.name}: {tagged} questions tagged, {untagged} untagged (general)")

    print(f"\nDone. Total tagged: {total_tagged} | Total untagged (general): {total_untagged}")


if __name__ == "__main__":
    main()
