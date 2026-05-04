'use client';

import React, { useState, useEffect, useRef, useCallback, Suspense } from 'react';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import Image from 'next/image';
import { askQuestion } from '@/lib/api';
import NavBar from '@/app/components/NavBar';
import { supabase } from '@/lib/supabaseClient';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: { source: string; page: string }[];
  llm_used?: string;
}

interface PracticeQ {
  question: string;
  options: Record<string, string>;
  correct_answer: string;
  source_file: string;
  topic: string;
  explanation?: string;
}

interface VerifyResult {
  correct_answer: string;
  explanation: string;
  sources: { source: string; page: string }[];
  llm_used: string;
}

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
if (typeof window !== 'undefined') {
  console.log('Chat page API initialized as:', API);
}

const MODULE_NAMES: Record<string, string> = {
  M1: 'Mathematics', M2: 'Physics', M3: 'Electrical Fundamentals',
  M4: 'Electronic Fundamentals', M5: 'Digital Techniques / Electronic Instrument Systems',
  M6: 'Materials and Hardware', M7A: 'Maintenance Practices', M7: 'Maintenance Practices',
  M8: 'Basic Aerodynamics', M9: 'Human Factors', M10: 'Aviation Legislation',
  M11A: 'Aeroplane Aerodynamics, Structures and Systems',
  M11B: 'Aeroplane Aerodynamics, Structures and Systems',
  M12: 'Helicopter Aerodynamics, Structures and Systems',
  M13: 'Aircraft Aerodynamics, Structures and Systems',
  M14: 'Propulsion', M15: 'Gas Turbine Engine',
  M16: 'Piston Engine', M17A: 'Propeller', M17: 'Propeller',
};

const EXAM_INFO: Record<string, {
  A?: number; B1?: number; B2?: number; B3?: number;
  timeA?: number; timeB1?: number; timeB2?: number; timeB3?: number;
}> = {
  M3:  { A:20,  timeA:25,  B1:52,  timeB1:65,  B2:52,  timeB2:65,  B3:24,  timeB3:30  },
  M4:  {                   B1:20,  timeB1:25,  B2:40,  timeB2:50,  B3:20,  timeB3:25  },
  M5:  { A:20,  timeA:25,  B1:40,  timeB1:50,  B2:72,  timeB2:90,  B3:20,  timeB3:25  },
  M6:  { A:52,  timeA:65,  B1:80,  timeB1:100, B2:60,  timeB2:75,  B3:80,  timeB3:100 },
  M7A: { A:76,  timeA:95,  B1:80,  timeB1:100, B2:60,  timeB2:75  },
  M7B: {                                                             B3:80,  timeB3:100 },
  M8:  { A:30,  timeA:38,  B1:30,  timeB1:38,  B2:30,  timeB2:38,  B3:30,  timeB3:38  },
  M9:  { A:28,  timeA:35,  B1:28,  timeB1:35,  B2:28,  timeB2:35,  B3:28,  timeB3:35  },
  M10: { A:32,  timeA:40,  B1:44,  timeB1:55,  B2:44,  timeB2:55,  B3:44,  timeB3:55  },
  M11A:{ A:108, timeA:135, B1:140, timeB1:175 },
  M11B:{ A:72,  timeA:90,  B1:100, timeB1:125 },
  M11C:{                                                             B3:60,  timeB3:75  },
  M12: { A:100, timeA:125, B1:128, timeB1:160 },
  M13: {                            B2:188, timeB2:235 },
  M14: {                            B2:32,  timeB2:40  },
  M15: { A:60,  timeA:75,  B1:92,  timeB1:115 },
  M16: { A:52,  timeA:65,  B1:76,  timeB1:95,              B3:76,  timeB3:95  },
  M17A:{ A:20,  timeA:25,  B1:32,  timeB1:40  },
  M17B:{                                                             B3:32,  timeB3:40  },
};

export const STREAM_MODULE_MAP: Record<string, string[]> = {
  'B1.1': ['M3','M4','M5','M6','M7','M8','M9','M10','M11A','M15','M17'],
  'B1.2': ['M3','M4','M5','M6','M7','M8','M9','M10','M11B','M16','M17'],
  'B1.3': ['M3','M4','M5','M6','M7','M8','M9','M10','M12','M15'],
  'B1.4': ['M3','M4','M5','M6','M7','M8','M9','M10','M12','M16'],
  'A1':   ['M3','M4','M5','M6','M7','M8','M9','M10','M11A','M15','M17'],
  'A2':   ['M3','M4','M5','M6','M7','M8','M9','M10','M11B','M16','M17'],
  'A3':   ['M3','M4','M5','M6','M7','M8','M9','M10','M12','M15'],
  'A4':   ['M3','M4','M5','M6','M7','M8','M9','M10','M12','M16'],
  'B2':   ['M3','M4','M5','M6','M7','M8','M9','M10','M13','M14'],
  'B3':   ['M3','M5','M6','M7','M8','M9','M10','M11B','M16','M17'],
  'C':    ['M3','M4','M5','M6','M7','M8','M9','M10','M11A','M12','M13','M14','M15','M16','M17'],
};

// Exact CAR 66 Issue III Rev 2 syllabus
const SYLLABUS: Record<string, string[]> = {
  M3: ['3.1 Electron Theory', '3.2 Static Electricity and Conduction', '3.3 Electrical Terminology', '3.4 Generation of Electricity', '3.5 Sources of DC Electricity', '3.6 DC Circuits', '3.7 Resistance/Resistor', '3.8 Power', '3.9 Capacitance/Capacitor', '3.10 Magnetism', '3.11 Inductance/Inductor', '3.12 DC Motor/Generator Theory', '3.13 AC Theory', '3.14 R, C and L Circuits', '3.15 Transformers', '3.16 Filters', '3.17 AC Generators', '3.18 AC Motors'],
  M4: ['4.1.1 Diodes', '4.1.2 Transistors', '4.1.3 Integrated Circuits', '4.2 Printed Circuit Boards', '4.3 Servomechanisms'],
  M5: ['5.1 Electronic Instrument Systems', '5.2 Numbering Systems', '5.3 Data Conversion', '5.4 Data Buses', '5.5 Logic Circuits', '5.6 Basic Computer Structure', '5.7 Microprocessors', '5.8 Integrated Circuits', '5.9 Multiplexing', '5.10 Fibre Optics', '5.11 Electronic Displays', '5.12 Electrostatic Sensitive Devices', '5.13 Software Management Control', '5.14 Electromagnetic Environment', '5.15 Typical Electronic/Digital Aircraft Systems'],
  M6: ['6.1 Aircraft Materials — Ferrous', '6.2 Aircraft Materials — Non-Ferrous', '6.3 Composite and Non-Metallic Materials', '6.3.2 Wooden Structures', '6.3.3 Fabric Covering', '6.4 Corrosion', '6.5.1 Screw Threads', '6.5.2 Bolts, Studs and Screws', '6.5.3 Locking Devices', '6.5.4 Aircraft Rivets', '6.6 Pipes and Unions', '6.7 Springs', '6.8 Bearings', '6.9 Transmissions', '6.10 Control Cables', '6.11 Electrical Cables and Connectors'],
  M7A: ['7.1 Safety Precautions — Aircraft and Workshop', '7.2 Workshop Practices', '7.3 Tools', '7.5 Engineering Drawings, Diagrams and Standards', '7.6 Fits and Clearances', '7.7 Electrical Wiring Interconnection System (EWIS)', '7.8 Riveting', '7.9 Pipes and Hoses', '7.10 Springs', '7.11 Bearings', '7.12 Transmissions', '7.13 Control Cables', '7.14 Material Handling', '7.16 Aircraft Weight and Balance', '7.17 Aircraft Handling and Storage', '7.18 Disassembly, Inspection, Repair and Assembly', '7.19 Abnormal Events', '7.20 Maintenance Procedures', '7.21 Documentation and Communication'],
  M7: ['7.1 Safety Precautions — Aircraft and Workshop', '7.2 Workshop Practices', '7.3 Tools', '7.5 Engineering Drawings, Diagrams and Standards', '7.6 Fits and Clearances', '7.7 EWIS', '7.8 Riveting', '7.14 Material Handling', '7.16 Aircraft Weight and Balance', '7.17 Aircraft Handling and Storage', '7.18 Disassembly, Inspection, Repair and Assembly', '7.19 Abnormal Events', '7.20 Maintenance Procedures', '7.21 Documentation and Communication'],
  M8: ['8.1 Physics of the Atmosphere — ISA', '8.2 Aerodynamics', '8.3 Theory of Flight', '8.4 High-Speed Airflow', '8.5 Flight Stability and Dynamics'],
  M9: ['9.1 General', '9.2 Human Performance and Limitations', '9.3 Social Psychology', '9.4 Factors that Affect Performance', '9.5 Physical Environment', '9.6 Tasks', '9.7 Communication', '9.8 Human Error', '9.9 Safety Management', "9.10 The 'Dirty Dozen' and Risk Mitigation"],
  M10: ['10.1 Regulatory Framework', '10.2 Certifying Staff — Maintenance', '10.3 Approved Maintenance Organisations', '10.4 Independent Certifying Staff', '10.5 Air Operations', '10.6 Certification of Aircraft, Parts and Appliances', '10.7 Continuing Airworthiness', '10.8 Oversight Principles in Continuing Airworthiness', '10.10 Cybersecurity in Aviation Maintenance'],
  M11A: ['11.1 Theory of Flight', '11.2 Airframe Structures (ATA 51)', '11.3 Airframe Structures — Aeroplanes', '11.4 Air Conditioning and Pressurisation (ATA 21)', '11.5 Instruments/Avionics (ATA 31/34)', '11.6 Electrical Power (ATA 24)', '11.7 Equipment and Furnishings (ATA 25)', '11.8 Fire Protection (ATA 26)', '11.9 Flight Controls (ATA 27)', '11.10 Fuel Systems (ATA 28)', '11.11 Hydraulic Power (ATA 29)', '11.12 Ice and Rain Protection (ATA 30)', '11.13 Landing Gear (ATA 32)', '11.14 Lights (ATA 33)', '11.15 Oxygen (ATA 35)', '11.16 Pneumatic/Vacuum (ATA 36)', '11.17 Water/Waste (ATA 38)', '11.19 Integrated Modular Avionics (ATA 42)', '11.20 Cabin Systems (ATA 44)'],
  M12: ['12.1 Theory of Flight — Rotary Wing Aerodynamics', '12.2 Flight Control Systems (ATA 67)', '12.3 Blade Tracking and Vibration Analysis (ATA 18)', '12.4 Transmission', '12.5 Airframe Structures (ATA 51)', '12.6 Air Conditioning', '12.7 Instruments/Avionics', '12.8 Electrical Power (ATA 24)', '12.9 Fire Protection (ATA 26)', '12.10 Fuel Systems (ATA 28)', '12.11 Hydraulic Power (ATA 29)', '12.12 Ice and Rain Protection (ATA 30)', '12.13 Landing Gear (ATA 32)', '12.14 Lights (ATA 33)', '12.15 Oxygen (ATA 35)', '12.16 Pneumatic/Vacuum (ATA 36)', '12.17 Water/Waste (ATA 38)', '12.18 Auxiliary Power Units (ATA 49)'],
  M13: ['13.1 Theory of Flight', '13.2 Structures — General Concepts (ATA 51)', '13.3 Autoflight (ATA 22)', '13.4 Communication/Navigation (ATA 23/34)', '13.5 Electrical Power (ATA 24)', '13.6 Equipment and Furnishings (ATA 25)', '13.7 Flight Controls', '13.8 Fuel Systems (ATA 28)', '13.9 Hydraulic Power (ATA 29)', '13.10 Ice and Rain Protection (ATA 30)', '13.11 Instruments (ATA 31)', '13.12 Lights (ATA 33)', '13.13 Navigation (ATA 34)', '13.14 Oxygen (ATA 35)', '13.15 Pneumatic/Vacuum (ATA 36)', '13.16 Landing Gear (ATA 32)', '13.20 Integrated Modular Avionics (ATA 42)', '13.21 Cabin Systems (ATA 44)', '13.22 Information Systems (ATA 46)'],
  M14: ['14.1 Engines — Turbine, APU, Piston, Electric/Hybrid', '14.2 Electric/Electronic Engine Indication Systems', '14.3 Propeller Systems', '14.4 Starting and Ignition Systems'],
  M15: ['15.1 Fundamentals', '15.2 Engine Performance', '15.3 Inlet', '15.4 Compressors', '15.5 Combustion Section', '15.6 Turbine Section', '15.7 Exhaust', '15.8 Bearings and Seals', '15.9 Lubricants and Fuels', '15.10 Lubrication Systems', '15.11 Fuel Systems', '15.12 Air Systems', '15.13 Starting and Ignition Systems', '15.14 Engine Indication Systems', '15.15 Alternate Turbine Constructions', '15.16 Turboprop Engines', '15.17 Turboshaft Engines', '15.18 Auxiliary Power Units (APUs)', '15.19 Power Plant Installation', '15.20 Fire Protection Systems', '15.21 Engine Monitoring and Ground Operation', '15.22 Engine Storage and Preservation'],
  M16: ['16.1 Fundamentals', '16.2 Engine Performance', '16.3 Engine Construction', '16.4.1 Carburettors', '16.4.2 Fuel Injection Systems', '16.4.3 Electronic Engine Control', '16.5 Starting and Ignition Systems', '16.6 Induction, Exhaust and Cooling Systems', '16.7 Supercharging/Turbocharging', '16.8 Lubricants and Fuels', '16.9 Lubrication Systems', '16.10 Engine Indication Systems', '16.11 Power Plant Installation', '16.12 Engine Monitoring and Ground Operation', '16.13 Engine Storage and Preservation', '16.14 Alternative Piston Engine Constructions'],
  M17A: ['17.1 Fundamentals', '17.2 Propeller Construction', '17.3 Propeller Pitch Control', '17.4 Propeller Synchronising', '17.5 Propeller Ice Protection', '17.6 Propeller Maintenance', '17.7 Propeller Storage and Preservation'],
  M17: ['17.1 Fundamentals', '17.2 Propeller Construction', '17.3 Propeller Pitch Control', '17.4 Propeller Synchronising', '17.5 Propeller Ice Protection', '17.6 Propeller Maintenance', '17.7 Propeller Storage and Preservation'],
};

const SOURCES: Record<string, string[]> = {
  M10: ['CAR 66 Issue III Rev 2', 'Aircraft Rules 1937/2025', 'CAR Sections (All)', 'Advisory Circulars', 'APM Part 0 & II'],
  M8: ['EASA Module 08', 'AC Kermode — Mechanics of Flight'],
  M9: ['EASA Module 09', 'CAP 715', 'CAP 716', 'CAP 718'],
  M6: ['EASA Module 06', 'CAIP Part 1 & 2', 'Titterton — Materials'],
  M15: ['EASA Module 15', 'Gulf Gas Turbine Handbook', 'FAA Powerplant Handbook'],
  M7A: ['EASA Module 07', 'CAIP Part 1 & 2', 'FAA Mechanics General'],
  M7: ['EASA Module 07', 'CAIP Part 1 & 2', 'FAA Mechanics General'],
  M3: ['EASA Module 03', 'BL Theraja Vol 1', 'VK Mehta Electrical'],
  M4: ['EASA Module 04', 'BL Theraja Vol 4'],
  M5: ['EASA Module 05 B1', 'EASA Module 05 B2', 'Leach & Malvino Digital'],
  M11A: ['EASA Module 11A', 'FAA Aviation Maintenance Handbook'],
  M12: ['EASA Module 12 Helicopter'],
  M13: ['EASA Module 13', 'Civil Avionics Systems — Wiley'],
  M14: ['EASA Module 14'],
  M16: ['EASA Module 16', 'Jeppesen Powerplant'],
  M17A: ['EASA Module 17A', 'Frank Hitchens — Propeller Aerodynamics'],
};

const SUGGESTIONS: Record<string, string[]> = {
  M10: ['What is CAR 66 and who does it apply to?', 'Who can issue a Certificate of Release to Service?', 'What are the privileges of a B1.1 license?'],
  M8: ['Explain Bernoulli\'s principle', 'What causes induced drag?', 'Explain stall and angle of attack'],
  M9: ['What is situational awareness?', 'Explain the SHELL model', 'What causes complacency in maintenance?'],
  M6: ['Properties of aluminium alloys in aircraft', 'Types of corrosion and prevention', 'Difference between rivets and bolts'],
  M15: ['How does a turbofan engine work?', 'What is compressor stall?', 'Explain turbine blade cooling'],
  M7A: ['Safety precautions in aircraft maintenance?', 'Types of non-destructive testing', 'How to read an engineering drawing'],
  M7: ['Safety precautions in aircraft maintenance?', 'Types of non-destructive testing', 'How to read an engineering drawing'],
  M3: ['Explain Ohm\'s law and Kirchhoff\'s laws', 'Difference between AC and DC?', 'How does a transformer work?'],
  M4: ['How does a transistor work?', 'What is a diode and its applications?', 'Explain integrated circuits'],
  M5: ['What is a data bus in aircraft?', 'Explain binary number system', 'What is EFIS and its components?'],
};

const cleanSrc = (s: string) =>
  String(s ?? '')
    .replace(/\.pdf$/i, '')
    .replace(/AME_/g, '')
    .replace(/_/g, ' ')
    .substring(0, 34);
const isGarbled = (s: string) => /[ÆÅŶƌĐǁϭϬ]/.test(s) || s.length < 15;

/** Matches literal placeholders from bad PDF extraction ("None") but not phrases like "None of the above". */
const OPTION_PLACEHOLDER = /^(none|null|n\/?a|--?|[.])\s*$/i;

function isSubstantiveOption(v: unknown): boolean {
  if (v === null || v === undefined) return false;
  const t = String(v).trim();
  if (t.length < 2) return false;
  return !OPTION_PLACEHOLDER.test(t);
}

function substantiveOptionCount(opts: Record<string, unknown> | undefined): number {
  if (!opts || typeof opts !== 'object' || Array.isArray(opts)) return 0;
  return Object.values(opts).filter(isSubstantiveOption).length;
}

function canonicalAnswerKey(opts: Record<string, string>, raw: unknown): string | null {
  if (!raw || typeof raw !== 'string') return null;
  const ca = raw.trim().toLowerCase();
  if (!ca) return null;
  const candidates = [ca, ca.charAt(0)].filter(Boolean);
  for (const k of candidates) {
    const val = opts[k];
    if (val !== undefined && isSubstantiveOption(val)) return k;
  }
  return null;
}

function isUsablePracticeQuestion(q: PracticeQ): boolean {
  const opts = q.options;
  if (!q.question?.trim()) return false;
  if (isGarbled(q.question)) return false;
  if (!opts || typeof opts !== 'object' || Array.isArray(opts)) return false;
  if (substantiveOptionCount(opts as Record<string, unknown>) < 3) return false;
  const key = canonicalAnswerKey(opts as Record<string, string>, q.correct_answer);
  return key !== null;
}

function normQuestionStem(s: string): string {
  return s.trim().replace(/\s+/g, ' ').toLowerCase();
}

/** Fisher–Yates shuffle (avoids biased sort(() => Math.random()-0.5)). */
function shuffleInPlace<T>(arr: T[]): T[] {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function dedupePracticeQuestions(rows: PracticeQ[]): PracticeQ[] {
  const seen = new Set<string>();
  const out: PracticeQ[] = [];
  for (const q of rows) {
    const k = normQuestionStem(q.question);
    if (!k || seen.has(k)) continue;
    seen.add(k);
    out.push(q);
  }
  return out;
}

const THINKING_MESSAGES = [
  "Searching verified Source...",
  "Checking CAR sections & regulations...",
  "Cross-referencing aviation database...",
  "Preparing response..."
];

function ThinkingIndicator() {
  const [msgIndex, setMsgIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setMsgIndex((prev) => (prev + 1) % THINKING_MESSAGES.length);
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ display: 'flex', justifyContent: 'flex-start', gap: '0.625rem' }}>
      <div style={{ maxWidth: '80%' }}>
        <div style={{ padding: '0.8rem 1rem', background: '#fff', borderRadius: '14px 14px 14px 3px', border: '1px solid #e8ecf5', boxShadow: '0 1px 4px rgba(0,0,0,0.06)', display: 'flex', alignItems: 'center', gap: '10px', minHeight: '44px' }}>
          <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#1a1f3a', animation: 'pulsingDot 0.8s infinite alternate', flexShrink: 0 }} />
          <div style={{ position: 'relative', width: '240px', height: '18px', display: 'flex', alignItems: 'center' }}>
            {THINKING_MESSAGES.map((text, idx) => (
              <div
                key={idx}
                style={{
                  position: 'absolute',
                  left: 0,
                  fontSize: '13px',
                  color: 'rgba(26, 31, 58, 0.5)', /* Equivalent to rgba(255,255,255,0.5) on dark bg, but adapted for the white bubble */
                  fontFamily: 'inherit',
                  whiteSpace: 'nowrap',
                  opacity: msgIndex === idx ? 1 : 0,
                  transition: 'opacity 0.8s ease-in-out',
                  pointerEvents: 'none'
                }}
              >
                {text}
              </div>
            ))}
          </div>
        </div>
      </div>
      <style>{`
        @keyframes pulsingDot {
          0% { transform: scale(0.6); opacity: 0.3; }
          100% { transform: scale(1.1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}

interface ChatPanelProps {
  messages: Message[];
  loading: boolean;
  chatInput: string;
  setChatInput: (v: string) => void;
  sendMessage: (text?: string) => void;
  moduleName: string;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  suggestions: string[];
  onClearChat: () => void;
  typingMessageId: string | null;
  displayedContent: Record<string, string>;
}

function ChatPanel({ messages, loading, chatInput, setChatInput, sendMessage, moduleName, messagesEndRef, suggestions, onClearChat, typingMessageId, displayedContent }: ChatPanelProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
      {messages.length > 0 && (
        <button 
          onClick={onClearChat}
          style={{ position: 'absolute', top: '12px', right: '15px', background: 'rgba(255, 255, 255, 0.9)', border: 'none', color: '#9ca3af', fontSize: '0.75rem', cursor: 'pointer', zIndex: 10, padding: '4px 8px', borderRadius: '4px' }}
        >
          ✕ Clear
        </button>
      )}
      <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem', paddingTop: messages.length > 0 ? '2.5rem' : '1.25rem' }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', marginTop: '3rem' }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>✈️</div>
            <h2 style={{ fontSize: '1.2rem', color: '#172a6e', marginBottom: '0.375rem', fontFamily: 'Georgia, serif' }}>Ask anything about {moduleName}</h2>
            <p style={{ color: '#9ca3af', fontSize: '0.82rem', marginBottom: '2rem' }}>Verified answers from official DGCA source documents only</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxWidth: '520px', margin: '0 auto' }}>
              {suggestions.map(q => (
                <button key={q} onClick={() => sendMessage(q)} style={{ padding: '0.7rem 1rem', background: '#fff', border: '1px solid #e2e6f0', borderRadius: '10px', cursor: 'pointer', fontSize: '0.875rem', color: '#213b93', textAlign: 'left', fontFamily: 'Georgia, serif', transition: 'all 0.15s' }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.borderColor = '#213b93'; (e.currentTarget as HTMLElement).style.background = '#f0f3fc'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.borderColor = '#e2e6f0'; (e.currentTarget as HTMLElement).style.background = '#fff'; }}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, msgIndex) => {
          const realSources = (msg.sources || []).filter(s =>
            s.source && 
            s.source !== 'Unknown' && 
            !s.source.toLowerCase().includes('ai knowledge') &&
            !s.source.toLowerCase().includes('not found') &&
            !s.source.toLowerCase().includes('aviation knowledge')
          );

          const isTyping = msg.id === typingMessageId;
          const body = typeof msg.content === 'string' ? msg.content : '';
          const rawContent = msg.role === 'assistant'
            ? body
                .replace(/Source:\s*Aviation knowledge[^\n]*/gi, '')
                .replace(/⚠\s*Source:\s*AI Knowledge Base[^\n]*/gi, '')
                .trim()
            : body;
          const cleanText = isTyping
            ? (displayedContent[msg.id] || '')
            : (msg.role === 'assistant' && displayedContent[msg.id] !== undefined && !isTyping
              ? rawContent
              : rawContent);

          return (
          <div key={msg.id} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start', gap: '0.625rem' }}>
            <div style={{ maxWidth: '80%' }}>
              <div style={{ padding: '0.8rem 1rem', fontSize: '0.875rem', lineHeight: 1.65, whiteSpace: 'pre-wrap', borderRadius: msg.role === 'user' ? '14px 14px 3px 14px' : '14px 14px 14px 3px', background: msg.role === 'user' ? '#213b93' : '#fff', color: msg.role === 'user' ? '#fff' : '#1a1f3a', boxShadow: '0 1px 4px rgba(0,0,0,0.06)', border: msg.role === 'assistant' ? '1px solid #e8ecf5' : 'none' }}>{cleanText}</div>
              {realSources.length > 0 && !msg.sources?.some((s: {source?: string}) => s.source?.includes('AI Knowledge Base')) && (
                <div style={{ marginTop: '0.375rem', display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                  {realSources.slice(0, 3).map((s, i) => <span key={i} style={{ fontSize: '0.68rem', color: '#6b7280', background: '#f0f2f8', padding: '2px 7px', borderRadius: '4px', border: '1px solid #e2e6f0' }}>📄 {cleanSrc(s.source)}{s.page ? ` p.${s.page}` : ''}</span>)}
                </div>
              )}
              {msg.llm_used && msg.role === 'assistant' && <div style={{ fontSize: '0.65rem', color: '#c4c9d8', marginTop: '3px' }}>via {msg.llm_used}</div>}
            </div>
          </div>
          );
        })}
        {loading && <ThinkingIndicator />}
        <div ref={messagesEndRef} />
      </div>
      <div style={{ padding: '0.875rem 1.25rem', background: '#fff', borderTop: '1px solid #e2e6f0', flexShrink: 0 }}>
        <div style={{ display: 'flex', gap: '0.625rem', background: '#f8fafc', borderRadius: '12px', padding: '0.5rem 0.75rem', border: '1.5px solid #e2e6f0', alignItems: 'flex-end' }}>
          <textarea
            value={chatInput}
            onChange={e => setChatInput(e.target.value)}
            onKeyDown={e => {
              if (e.nativeEvent.isComposing) return;
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            placeholder={`Ask about ${moduleName}...`}
            rows={1}
            style={{ flex: 1, background: 'none', border: 'none', outline: 'none', resize: 'none', fontSize: '0.875rem', color: '#1a1f3a', fontFamily: 'Georgia, serif', lineHeight: 1.5, maxHeight: '100px', overflowY: 'auto' }}
          />
          <button
            onClick={() => sendMessage()}
            style={{ background: '#213b93', color: '#fff', border: 'none', borderRadius: '8px', width: '34px', height: '34px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '16px', flexShrink: 0 }}
          >→</button>
        </div>
        <p style={{ fontSize: '0.65rem', color: '#c4c9d8', marginTop: '0.35rem', textAlign: 'center' }}>Official DGCA sources only · Enter to send</p>
      </div>
    </div>
  );
}

function getExamQ(moduleId: string, stream: string): number {
  const info = EXAM_INFO[moduleId];
  if (!info) return 0;
  if (stream === 'B3') return info.B3 || 0;
  if (stream.startsWith('B1')) return info.B1 || info.A || 0;
  if (stream === 'B2' || stream === 'B2L') return info.B2 || 0;
  if (stream.startsWith('A')) return info.A || 0;
  return info.B1 || info.A || 0;
}

function getExamTime(moduleId: string, stream: string): number {
  const info = EXAM_INFO[moduleId];
  if (!info) return 0;
  if (stream === 'B3') return info.timeB3 || 0;
  if (stream.startsWith('B1')) return info.timeB1 || info.timeA || 0;
  if (stream === 'B2' || stream === 'B2L') return info.timeB2 || 0;
  if (stream.startsWith('A')) return info.timeA || 0;
  return info.timeB1 || info.timeA || 0;
}

function Accordion({ title, children, defaultOpen = false }: { title: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div style={{ marginBottom: '0.5rem', border: '1px solid #e2e6f0', borderRadius: '10px', overflow: 'hidden' }}>
      <button onClick={() => setOpen(o => !o)} style={{ width: '100%', padding: '0.625rem 0.875rem', background: open ? '#f0f3fc' : '#f8fafc', border: 'none', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#213b93', textTransform: 'uppercase', letterSpacing: '0.07em' }}>{title}</span>
        <span style={{ fontSize: '0.75rem', color: '#9ca3af', transition: 'transform 0.2s', transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}>▼</span>
      </button>
      {open && <div style={{ padding: '0.75rem 0.875rem', background: '#fff' }}>{children}</div>}
    </div>
  );
}

function ModuleContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const moduleId = (params.moduleId as string)?.toUpperCase();
  const stream = searchParams.get('stream') || 'B1.1';
  const moduleName = MODULE_NAMES[moduleId] || moduleId;
  const examQ = getExamQ(moduleId, stream);
  const examTime = getExamTime(moduleId, stream);
  const examPass = Math.ceil(examQ * 0.75);
  const syllabus = SYLLABUS[moduleId] || [];
  const sources = SOURCES[moduleId] || ['EASA Module Books', 'DGCA CAR Sections'];
  const suggestions = SUGGESTIONS[moduleId] || [`What are key topics in ${moduleName}?`];

  const [mobileTab, setMobileTab] = useState<'info' | 'chat' | 'practice'>('chat');

  // ── Progress Tracker ──────────────────────────────────────────────────────────
  const [progressStats, setProgressStats] = useState<{
    total_attempted: number;
    target_questions: number;
    pyq_attempted: number;
    ai_attempted: number;
    mind_attempted: number;
    topic_stats?: Record<string, number>;
  }>({
    total_attempted: 0,
    target_questions: 0,
    pyq_attempted: 0,
    ai_attempted: 0,
    mind_attempted: 0,
    topic_stats: {},
  });
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [goalInput, setGoalInput] = useState(5000);
  const [isSettingGoal, setIsSettingGoal] = useState(false);
  const [showGoalSetup, setShowGoalSetup] = useState(false);

  // ── Dashboard Syllabus (fetched on demand) ────────────────────────────────────
  const [dashboardSyllabus, setDashboardSyllabus] = useState<{
    module: string;
    name: string;
    topics: Record<string, { name: string; level: number; target: number }>;
  } | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);


  useEffect(() => {
    const fetchProgress = async () => {
      const uid = localStorage.getItem('user_id');
      if (!uid) return;
      try {
        const res = await fetch(`${API}/module-progress/${moduleId}?user_id=${uid}&target=0`);
        if (res.ok) {
          const data = await res.json();
          if (data.total_attempted !== undefined) {
             setProgressStats(data);
             if (data.target_questions > 0) setGoalInput(data.target_questions);
          }
        }
      } catch (e) {}

      // Check module access
      try {
        const { data: accessData } = await supabase
          .from('module_access')
          .select('access_type, access_expires_at')
          .eq('user_id', uid)
          .eq('module', moduleId)
          .single();

        if (accessData) {
          const now = new Date();
          const expiry = new Date(accessData.access_expires_at);
          const isActive = expiry > now;
          setModuleAccess({
            has_access: isActive,
            access_type: accessData.access_type,
            expires_at: accessData.access_expires_at
          });

          // Check if expiring within 24 hours
          const hoursLeft = (expiry.getTime() - now.getTime()) / (1000 * 60 * 60);
          if (hoursLeft > 0 && hoursLeft <= 24) {
            setShowExpiryNotice(true);
          }
        }
      } catch (e) {
        // no access record found — free user
      }
    };
    fetchProgress();
  }, [moduleId]);

  const trackProgress = async (mode: string) => {
    const uid = localStorage.getItem('user_id');
    if (!uid) return;
    
    let modeKey = '';
    if (mode === 'pyq') modeKey = 'pyq_attempted';
    else if (mode.includes('ai')) modeKey = 'ai_attempted';
    else if (mode.includes('mind')) modeKey = 'mind_attempted';

    setProgressStats(prev => ({
      ...prev,
      total_attempted: prev.total_attempted + 1,
      ...(modeKey ? { [modeKey]: (prev[modeKey as keyof typeof prev] as number || 0) + 1 } : {})
    }));

    try {
      await fetch(`${API}/progress/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
        body: JSON.stringify({ user_id: uid, module: moduleId, mode, target_questions: progressStats.target_questions || 5000 })
      });
    } catch (e) {}
  };

  const saveGoal = async () => {
    if (goalInput < 1000) return alert('Minimum goal is 1000 questions.');
    const uid = localStorage.getItem('user_id');
    if (!uid) return alert('Please log in using the platform.');
    setIsSettingGoal(true);
    try {
      await fetch(`${API}/progress/goal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
        body: JSON.stringify({ user_id: uid, module: moduleId, target_questions: goalInput })
      });
      setProgressStats(p => ({ ...p, target_questions: goalInput }));
      setShowGoalSetup(false);
    } catch {} finally {
      setIsSettingGoal(false);
    }
  };

  const handlePromoCheck = async () => {
    if (!promoCode.trim()) return;
    setPromoChecking(true);
    setPromoResult(null);
    try {
      const uid = localStorage.getItem('user_id');
      const res = await fetch(`${API}/promo/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          code: promoCode.trim(), 
          user_id: uid || null
        })
      });
      const data = await res.json();
      setPromoResult(data);
    } catch (e) {
      setPromoResult({ valid: false, message: 'Connection error. Please try again.' });
    } finally {
      setPromoChecking(false);
    }
  };

  const handlePromoRedeem = async () => {
    const uid = localStorage.getItem('user_id');
    if (!uid) {
      setPromoResult({ valid: false, message: 'Please log in to use a promo code.' });
      return;
    }
    setPromoRedeeming(true);
    try {
      const res = await fetch(`${API}/promo/redeem`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          code: promoCode.trim(), 
          module: moduleId, 
          user_id: uid 
        })
      });
      const data = await res.json();
      if (data.success) {
        setPromoSuccess(true);
        setTimeout(() => {
          setIsBillingOpen(false);
          setPromoSuccess(false);
          setPromoCode('');
          setPromoResult(null);
          window.location.reload();
        }, 2500);
      } else {
        setPromoResult({ valid: false, message: data.detail || 'Redemption failed.' });
      }
    } catch (e) {
      setPromoResult({ valid: false, message: 'Connection error. Please try again.' });
    } finally {
      setPromoRedeeming(false);
    }
  };

  const handleOpenReport = () => {
    if (!progressStats.target_questions || progressStats.target_questions === 0) {
      setShowGoalSetup(true);
    } else {
      setShowGoalSetup(false);
    }
    setIsReportOpen(true);
  };

  // fetch syllabus data for the dashboard whenever report is opened
  useEffect(() => {
    if (!isReportOpen || dashboardSyllabus) return; // already loaded
    const fetchSyllabus = async () => {
      setDashboardLoading(true);
      try {
        const res = await fetch(`${API}/syllabus/${moduleId}?stream=${stream}`, { headers: { 'ngrok-skip-browser-warning': 'true' } });
        if (res.ok) {
          const data = await res.json();
          setDashboardSyllabus(data);
        }
      } catch (e) {}
      finally { setDashboardLoading(false); }
    };
    fetchSyllabus();
  }, [isReportOpen, moduleId, stream, dashboardSyllabus]);

  // ── Feedback ──────────────────────────────────────────────────────────────────
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false);
  const [feedbackTab, setFeedbackTab] = useState<1 | 2 | 3>(1);
  const [feedbackMessage, setFeedbackMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [feedbackError, setFeedbackError] = useState('');

  // ── Unlock Modal ──────────────────────────────────────────────────────────────
  const [isPayModalOpen, setIsPayModalOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<{ amount: string, duration: string } | null>(null);
  const [showPromoInput, setShowPromoInput] = useState(false);
  const [isBillingOpen, setIsBillingOpen] = useState(false);
  const [usageData, setUsageData] = useState<{chat_hours_used: number, practice_sets_used: number} | null>(null);
  const [usageLoading, setUsageLoading] = useState(false);
  const [promoCode, setPromoCode] = useState('');
  const [promoChecking, setPromoChecking] = useState(false);
  const [promoResult, setPromoResult] = useState<any>(null);
  const [promoRedeeming, setPromoRedeeming] = useState(false);
  const [promoSuccess, setPromoSuccess] = useState(false);

  useEffect(() => {
    if (!isBillingOpen) return;
    const uid = localStorage.getItem('user_id');
    if (!uid) return;
    setUsageLoading(true);
    fetch(`${API}/usage/${uid}`)
      .then(r => r.json())
      .then(data => setUsageData(data))
      .catch(() => setUsageData(null))
      .finally(() => setUsageLoading(false));
  }, [isBillingOpen]);

  // ── Module Access ──────────────────────────────────────────────────────────────
  const [moduleAccess, setModuleAccess] = useState<{
    has_access: boolean;
    access_type: string;
    expires_at: string | null;
  } | null>(null);
  const [showExpiryNotice, setShowExpiryNotice] = useState(false);

  const submitFeedback = async () => {
    if (!feedbackMessage.trim()) return;
    setIsSubmitting(true);
    setFeedbackError('');
    const typeStr = feedbackTab === 1 ? 'Suggest a Change' : feedbackTab === 2 ? 'Register a Query' : 'General Feedback';
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    try {
      const res = await fetch(`${API}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
        body: JSON.stringify({ module: moduleId, type: typeStr, message: feedbackMessage }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      
      if (!res.ok) {
        throw new Error('Failed to submit feedback. Please try again later.');
      }
      
      setIsSubmitting(false);
      setShowSuccess(true);
      setTimeout(() => {
        setShowSuccess(false);
        setIsFeedbackOpen(false);
        setFeedbackMessage('');
      }, 2000);
    } catch (e: any) {
      clearTimeout(timeoutId);
      setIsSubmitting(false);
      if (e.name === 'AbortError') {
        setFeedbackError('Request timed out (10s). Please check your connection and try again.');
      } else {
        setFeedbackError(e.message || 'Failed to submit feedback.');
      }
    }
  };

  // ── Chat ──────────────────────────────────────────────────────────────────────
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [preferredLlm, setPreferredLlm] = useState('groq');
  const [chatInput, setChatInput] = useState('');
  const [userName, setUserName] = useState('');
  const [typingMessageId, setTypingMessageId] = useState<string | null>(null);
  const [displayedContent, setDisplayedContent] = useState<Record<string, string>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const aiTopicRef = useRef<HTMLInputElement>(null);
  const isSendingRef = useRef(false);
  const isFirstLoad = useRef(true);

  useEffect(() => {
    if (!messagesEndRef.current) return;
    if (isFirstLoad.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'instant' });
      isFirstLoad.current = false;
    } else {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Load user name from Supabase profile
  useEffect(() => {
    const loadUserName = async () => {
      const uid = localStorage.getItem('user_id');
      if (!uid) return;
      try {
        const { data } = await supabase.from('profiles').select('full_name').eq('id', uid).single();
        if (data?.full_name) {
          const first = data.full_name.trim().split(' ')[0];
          setUserName(first);
        }
      } catch {}
    };
    loadUserName();
  }, []);

  // Typewriter effect for new assistant messages
  useEffect(() => {
    if (!typingMessageId) return;
    const msg = messages.find(m => m.id === typingMessageId);
    if (!msg) return;
    const fullText = msg.content;
    let i = 0;
    setDisplayedContent(prev => ({ ...prev, [typingMessageId]: '' }));
    const interval = setInterval(() => {
      i += 3;
      setDisplayedContent(prev => ({ ...prev, [typingMessageId]: fullText.slice(0, i) }));
      if (i >= fullText.length) {
        clearInterval(interval);
        setTypingMessageId(null);
      }
    }, 12);
    return () => clearInterval(interval);
  }, [typingMessageId]);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(`fonus_chat_${moduleId}_${stream}`);
      if (saved) {
        const parsed = JSON.parse(saved);
        setMessages(parsed);
      }
    } catch { }
  }, [moduleId, stream]);

  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(`fonus_chat_${moduleId}_${stream}`, JSON.stringify(messages));
    }
  }, [messages, moduleId, stream]);

  const estimateTokens = (msgs: Message[]) =>
    msgs.reduce((t, m) => t + Math.ceil(m.content.length / 4), 0);

  const autoCompact = useCallback(async (currentMessages: Message[]) => {
    if (currentMessages.length < 10) return;
    try {
      const res = await fetch(`${API}/chat/compact`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'ngrok-skip-browser-warning': 'true'
        },
        body: JSON.stringify({
          messages: currentMessages.map(m => ({
            role: m.role,
            content: m.content
          })),
          module: moduleId,
          user_id: localStorage.getItem('fonus_user_id') || undefined
        })
      });
      const data = await res.json();
      
      const recent = currentMessages.slice(-5);
      
      const compactMsg: Message = {
        id: `compact_${Date.now()}`,
        role: 'assistant',
        content: `🗂️ Session summary: ${data.summary}`,
        sources: []
      };
      
      const compacted = [compactMsg, ...recent];
      setMessages(compacted);
      localStorage.setItem(`fonus_chat_${moduleId}_${stream}`, JSON.stringify(compacted));
    } catch {
      const trimmed = currentMessages.slice(-10);
      setMessages(trimmed);
      localStorage.setItem(`fonus_chat_${moduleId}_${stream}`, JSON.stringify(trimmed));
    }
  }, [moduleId, stream]);

  useEffect(() => {
    if (!loading && messages.length > 10) {
      const tokens = estimateTokens(messages);
      if (tokens > 8000) {
        autoCompact(messages);
      }
    }
  }, [messages, loading, autoCompact]);

  const handleClearChat = useCallback(() => {
    setMessages([]);
    localStorage.removeItem(`fonus_chat_${moduleId}_${stream}`);
  }, [moduleId, stream]);

  const sendMessage = useCallback(async (text?: string) => {
    if (isSendingRef.current) return;
    const q = text || chatInput.trim();
    if (!q || loading) return;
    isSendingRef.current = true;
    setChatInput('');
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: q };
    
    setMessages(p => [...p, userMsg]);
    setLoading(true);
    
    try {
      const history = messages
        .filter((m: any) => m.role === 'user' || m.role === 'assistant')
        .slice(-8)
        .map((m: any) => ({
          role: m.role,
          content: typeof m.content === 'string'
            ? m.content.slice(0, 300)
            : ((m.content as any)?.text || '').slice(0, 300)
        }));
      const resData = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
        body: JSON.stringify({
          question: q,
          module: moduleId,
          user_id: localStorage.getItem('fonus_user_id') || localStorage.getItem('user_id'),
          stream: stream,
          history: history,
          preferred_llm: preferredLlm
        })
      });
      const res = await resData.json().catch(() => ({}));
      const assistantId = (Date.now() + 1).toString();

      const formatErr = (body: Record<string, unknown>): string => {
        const d = body.detail;
        if (typeof d === 'string') return d;
        if (Array.isArray(d)) {
          return d.map((x: { msg?: string }) => x?.msg || String(x)).join('; ');
        }
        return typeof body.message === 'string' ? body.message : 'Request failed';
      };

      if (!resData.ok) {
        const errText = formatErr(res as Record<string, unknown>);
        setMessages(p => [
          ...p,
          {
            id: assistantId,
            role: 'assistant',
            content:
              resData.status === 503
                ? `${errText}\n\nTip: Groq free tier has a daily token cap per org. Add GEMINI_API_KEY or wait for reset.`
                : errText,
            sources: [],
            llm_used: 'error',
          },
        ]);
        return;
      }

      // Smart off-topic redirect: if answer is about a different domain, append guide nudge
      let finalAnswer = typeof res.answer === 'string' ? res.answer : formatErr(res as Record<string, unknown>);
      const offTopicKeywords = [
        'price of aviation fuel', 'fuel price today', 'atf price',
        'weather forecast', 'stock price', 'cricket score', 'movie',
        'politics', 'recipe', 'news today'
      ];
      const isOffTopic = offTopicKeywords.some(sig => q.toLowerCase().includes(sig));
      if (isOffTopic) {
        const nameGreet = userName ? `${userName}, ` : '';
        finalAnswer += `\n\n${nameGreet}that topic is outside ${moduleName} scope. Your DGCA exam is coming up -- want to pick up where you left off in ${moduleName}?`;
      }
      setMessages(p => [
        ...p,
        { id: assistantId, role: 'assistant', content: finalAnswer, sources: res.source, llm_used: res.llm_used }
      ]);
      setTypingMessageId(assistantId);

      // Track chat usage — estimate 1 minute per message exchange
      const uid = localStorage.getItem('user_id');
      if (uid) {
        fetch(`${API}/usage/track`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            user_id: uid, 
            type: 'chat_minutes', 
            amount: 1 
          })
        }).catch(() => {});
      }
    } catch {
      setMessages(p => [
        ...p,
        { id: (Date.now() + 1).toString(), role: 'assistant', content: 'Could not connect. Ensure backend is running on port 8000.' }
      ]);
    } finally { 
      setLoading(false); 
      isSendingRef.current = false;
    }
  }, [chatInput, loading, messages, moduleId, preferredLlm]);

  // ── Practice ──────────────────────────────────────────────────────────────────
  const [practicePhase, setPracticePhase] = useState<'select' | 'pyq' | 'ai_setup' | 'ai_active' | 'mind_setup' | 'mind_active' | 'complete'>('select');
  const [practiceQuestions, setPracticeQuestions] = useState<PracticeQ[]>([]);
  const [practiceIndex, setPracticeIndex] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [score, setScore] = useState(0);
  const [answered, setAnswered] = useState(0);
  const [timerDisplay, setTimerDisplay] = useState(0);
  const [aiTopicInput, setAiTopicInput] = useState('');
  const [generatingQuestions, setGeneratingQuestions] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timeLeftRef = useRef(0);
  const timerActiveRef = useRef(false);
  const [answeredQuestions, setAnsweredQuestions] = useState<{
    question: string;
    options: string[];
    selected: string;
    correct: string;
    explanation: string;
  }[]>([]);
  const [mindLevel, setMindLevel] = useState<'easy' | 'medium' | 'hard'>('medium');

  const startTimer = (seconds: number) => {
    timeLeftRef.current = seconds; timerActiveRef.current = true; setTimerDisplay(seconds);
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      if (!timerActiveRef.current) { clearInterval(timerRef.current!); return; }
      timeLeftRef.current -= 1; setTimerDisplay(timeLeftRef.current);
      if (timeLeftRef.current <= 0) { clearInterval(timerRef.current!); timerActiveRef.current = false; setPracticePhase('complete'); }
    }, 1000);
  };
  const stopTimer = () => { timerActiveRef.current = false; if (timerRef.current) clearInterval(timerRef.current); };
  useEffect(() => () => stopTimer(), []);

  const startPYQ = async () => {
    try {
      const res = await fetch(`${API}/practice/questions/${moduleId}?count=500`, { headers: { 'ngrok-skip-browser-warning': 'true' } });
      const data = await res.json();
      const clean = dedupePracticeQuestions(
        (data.questions || []).filter((q: PracticeQ) => isUsablePracticeQuestion(q)),
      );
      if (!clean.length) { alert('No questions available for this module yet.'); return; }
      const want = Math.min(examQ || 20, clean.length);
      const selected = shuffleInPlace([...clean]).slice(0, want);
      setPracticeQuestions(selected); setPracticeIndex(0); setScore(0); setAnswered(0);
      setSelectedAnswer(null); setVerifyResult(null);
      setPracticePhase('pyq');

      // Track practice set usage
      const uid = localStorage.getItem('user_id');
      if (uid) {
        fetch(`${API}/usage/track`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            user_id: uid, 
            type: 'practice_set', 
            amount: 1 
          })
        }).catch(() => {});
      }
    } catch { alert('Could not load questions. Check backend.'); }
  };

  const generateAiQuestions = async (topic: string, isMind: boolean) => {
    setGeneratingQuestions(true);
    const targetCount = examQ || 20;
    const allQuestions: PracticeQ[] = [];
    const batches = Math.ceil(targetCount / 10);
    for (let i = 0; i < batches; i++) {
      const batchSize = Math.min(10, targetCount - allQuestions.length);
      const prompt = isMind
        ? `Generate exactly ${batchSize} twisted/application-based DGCA CAR 66 ${moduleId} MCQ questions inspired by: "${topic}". Make them scenario-based, not direct recall. Return ONLY a JSON array:\n[{"question":"...","options":{"a":"...","b":"...","c":"...","d":"..."},"correct_answer":"a","topic":"${topic}","explanation":"..."}]`
        : `Generate exactly ${batchSize} DGCA CAR 66 ${moduleId} exam MCQ questions about: "${topic}". Based on official syllabus. Return ONLY a JSON array:\n[{"question":"...","options":{"a":"...","b":"...","c":"...","d":"..."},"correct_answer":"a","topic":"${topic}","explanation":"..."}]`;
      try {
        const res = await fetch(`${API}/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' }, body: JSON.stringify({ question: prompt, module: moduleId, preferred_llm: preferredLlm }) });
        const data = await res.json();
        const text = data.answer || '';
        const match = text.match(/\[[\s\S]*\]/);
        if (match) { try { allQuestions.push(...JSON.parse(match[0])); } catch { } }
      } catch { }
    }
    setGeneratingQuestions(false);
    const parsedFiltered = dedupePracticeQuestions(
      allQuestions.filter((q) => isUsablePracticeQuestion(q as PracticeQ)) as PracticeQ[],
    );
    if (!parsedFiltered.length) { alert('Could not generate questions. Try again.'); return; }
    const want = Math.min(targetCount, parsedFiltered.length);
    const selected = shuffleInPlace([...parsedFiltered]).slice(0, want);
    setPracticeQuestions(selected);
    setPracticeIndex(0); setScore(0); setAnswered(0); setSelectedAnswer(null); setVerifyResult(null);
    setPracticePhase(isMind ? 'mind_active' : 'ai_active');
    if (isMind) startTimer(want * 75);

    // Track practice set usage
    const uid = localStorage.getItem('user_id');
    if (uid) {
      fetch(`${API}/usage/track`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          user_id: uid, 
          type: 'practice_set', 
          amount: 1 
        })
      }).catch(() => {});
    }
  };

  const verifyAnswer = async () => {
    if (!selectedAnswer) return;
    const q = practiceQuestions[practiceIndex];
    // For AI generated, use embedded explanation if available
    if (q.explanation && q.correct_answer) {
      const result = { correct_answer: q.correct_answer, explanation: q.explanation, sources: [], llm_used: 'AI Generated' };
      setVerifyResult(result);
      setAnswered(p => p + 1);
      if (q.correct_answer === selectedAnswer) setScore(p => p + 1);
      trackProgress(practicePhase);
      // Save answered question for Previous navigation
      setAnsweredQuestions(prev => {
        const updated = [...prev];
        updated[practiceIndex] = {
          question: q.question,
          options: Object.values(q.options || {}),
          selected: selectedAnswer,
          correct: q.correct_answer,
          explanation: q.explanation || ''
        };
        return updated;
      });
      return;
    }
    setVerifying(true);
    try {
      const res = await fetch(`${API}/practice/verify`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' }, body: JSON.stringify({ question: q.question, options: q.options, module: moduleId, correct_answer: q.correct_answer }) });
      const data = await res.json();
      setVerifyResult(data); setAnswered(p => p + 1);
      if (data.correct_answer === selectedAnswer) setScore(p => p + 1);
      trackProgress(practicePhase);
      // Save answered question for Previous navigation
      setAnsweredQuestions(prev => {
        const updated = [...prev];
        updated[practiceIndex] = {
          question: q.question,
          options: Object.values(q.options || {}),
          selected: selectedAnswer,
          correct: data.correct_answer,
          explanation: data.explanation || ''
        };
        return updated;
      });
    } catch { } finally { setVerifying(false); }
  };

  const nextQuestion = () => {
    if (practiceIndex + 1 >= practiceQuestions.length) { stopTimer(); setPracticePhase('complete'); }
    else { setPracticeIndex(p => p + 1); setSelectedAnswer(null); setVerifyResult(null); }
  };

  const resetPractice = () => { stopTimer(); setPracticePhase('select'); setPracticeQuestions([]); setAiTopicInput(''); setAnsweredQuestions([]); };

  // ── Question display (shared by PYQ, AI, Mind) ────────────────────────────────
  const QuestionDisplay = () => {
    const q = practiceQuestions[practiceIndex];
    if (!q) return null;
    const isAnswered = !!verifyResult;
    const hasPrev = practiceIndex > 0 && !!answeredQuestions[practiceIndex - 1];
    const total = practiceQuestions.length;
    const optionEntries = q.options && typeof q.options === 'object' && !Array.isArray(q.options)
      ? Object.entries(q.options).filter(([, v]) => v?.trim())
      : [];

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>

        {/* Section header + back button */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              onClick={() => resetPractice()}
              style={{
                background: '#f0f3fc', border: 'none',
                color: '#213b93', width: '28px', height: '28px',
                borderRadius: '50%', cursor: 'pointer',
                fontSize: '0.9rem', display: 'flex',
                alignItems: 'center', justifyContent: 'center'
              }}
            >←</button>
            <span style={{
              fontSize: '0.65rem', fontWeight: 700,
              color: '#213b93', letterSpacing: '0.08em',
              textTransform: 'uppercase',
              fontFamily: 'system-ui, sans-serif'
            }}>
              {practicePhase === 'pyq' ? 'DGCA PYQs'
               : practicePhase === 'ai_active' ? 'AI Practice'
               : 'Mind Maintenance'}
            </span>
          </div>
          <span style={{ fontSize: '0.65rem', color: '#9ca3af', fontFamily: 'system-ui, sans-serif' }}>
            Q{practiceIndex + 1}/{total}
          </span>
        </div>

        {/* Topic tag */}
        {q.topic && (
          <div style={{
            display: 'inline-block',
            background: '#f0f3fc', color: '#213b93',
            padding: '3px 10px', borderRadius: '20px',
            fontSize: '0.65rem', fontWeight: 600,
            fontFamily: 'system-ui, sans-serif',
            alignSelf: 'flex-start'
          }}>
            {q.topic}
          </div>
        )}

        {/* Question */}
        <div style={{
          fontSize: '0.88rem', color: '#1a1f3a',
          lineHeight: 1.65, fontWeight: 500,
          fontFamily: 'Georgia, serif',
          padding: '0.875rem',
          background: '#f8faff',
          borderRadius: '12px',
          border: '1px solid #eef1f8'
        }}>
          {q.question}
        </div>

        {/* Options */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {optionEntries.map(([key, opt], i) => {
            const letter = key.toUpperCase();
            const isSelected = selectedAnswer === key;
            const isCorrect = verifyResult?.correct_answer === key;
            const isWrong = isAnswered && isSelected && !isCorrect;
            return (
              <button
                key={key}
                onClick={() => !isAnswered && setSelectedAnswer(key)}
                style={{
                  padding: '0.75rem 1rem',
                  background: isCorrect && isAnswered ? '#f0fdf4'
                    : isWrong ? '#fef2f2'
                    : isSelected ? '#f0f3fc'
                    : '#fff',
                  border: `1.5px solid ${
                    isCorrect && isAnswered ? '#86efac'
                    : isWrong ? '#fca5a5'
                    : isSelected ? '#213b93'
                    : '#eef1f8'
                  }`,
                  borderRadius: '10px',
                  cursor: isAnswered ? 'default' : 'pointer',
                  textAlign: 'left',
                  display: 'flex', alignItems: 'flex-start', gap: '0.625rem',
                  transition: 'all 0.15s', width: '100%'
                }}
              >
                <span style={{
                  width: '22px', height: '22px', borderRadius: '50%',
                  background: isCorrect && isAnswered ? '#22c55e'
                    : isWrong ? '#ef4444'
                    : isSelected ? '#213b93'
                    : '#f0f3fc',
                  color: isSelected || (isAnswered && (isCorrect || isWrong)) ? '#fff' : '#6b7280',
                  fontSize: '0.65rem', fontWeight: 700,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexShrink: 0, marginTop: '1px',
                  fontFamily: 'system-ui, sans-serif'
                }}>{letter}</span>
                <span style={{
                  fontSize: '0.82rem', color: '#1a1f3a',
                  lineHeight: 1.45, fontFamily: 'system-ui, sans-serif'
                }}>{opt}</span>
              </button>
            );
          })}
        </div>

        {/* Explanation after answer */}
        {isAnswered && verifyResult?.explanation && (
          <div style={{
            padding: '0.875rem',
            background: '#f8faff',
            borderRadius: '10px',
            border: '1px solid #eef1f8',
            fontSize: '0.78rem',
            color: '#374151',
            lineHeight: 1.6,
            fontFamily: 'system-ui, sans-serif'
          }}>
            <span style={{ fontWeight: 700, color: '#213b93' }}>Explanation: </span>
            {verifyResult.explanation.replace(/CORRECT:\s*[A-Da-d]\s*/i, '').replace(/EXPLANATION:\s*/i, '').replace(/SOURCE:.*/is, '').trim()}
          </div>
        )}

        {/* Source badges */}
        {isAnswered && verifyResult?.sources && verifyResult.sources.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
            {verifyResult.sources.map((s: any, i: number) => (
              <span key={i} style={{
                background: '#f0f3fc', color: '#213b93',
                padding: '3px 8px', borderRadius: '6px',
                fontSize: '0.6rem', fontFamily: 'system-ui, sans-serif'
              }}>📄 {cleanSrc(s.source)}{s.page ? ` p.${s.page}` : ''}</span>
            ))}
          </div>
        )}

        {/* ACTION BUTTONS */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>

          {/* Row 1: Confirm Answer + Previous */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
            <button
              onClick={() => verifyAnswer()}
              disabled={!selectedAnswer || isAnswered}
              style={{
                padding: '0.75rem',
                background: !selectedAnswer || isAnswered ? '#f4f6fb' : '#213b93',
                color: !selectedAnswer || isAnswered ? '#c4c9d8' : '#fff',
                border: 'none', borderRadius: '10px',
                fontSize: '0.78rem', fontWeight: 700,
                cursor: !selectedAnswer || isAnswered ? 'not-allowed' : 'pointer',
                fontFamily: 'Georgia, serif'
              }}
            >
              {verifying ? '⏳ Checking...' : isAnswered
                ? (selectedAnswer === verifyResult?.correct_answer ? '✅ Correct' : '❌ Wrong')
                : 'Confirm Answer'}
            </button>

            <button
              onClick={() => {
                if (hasPrev) {
                  const prev = answeredQuestions[practiceIndex - 1];
                  setSelectedAnswer(prev.selected);
                  setVerifyResult({
                    correct_answer: prev.correct,
                    explanation: prev.explanation,
                    sources: [],
                    llm_used: ''
                  });
                  setPracticeIndex(i => i - 1);
                }
              }}
              disabled={!hasPrev}
              style={{
                padding: '0.75rem',
                background: hasPrev ? '#f0f3fc' : '#f4f6fb',
                color: hasPrev ? '#213b93' : '#c4c9d8',
                border: `1px solid ${hasPrev ? '#dde2f0' : '#f4f6fb'}`,
                borderRadius: '10px',
                fontSize: '0.78rem', fontWeight: 600,
                cursor: hasPrev ? 'pointer' : 'not-allowed',
                fontFamily: 'system-ui, sans-serif'
              }}
            >
              ← Previous
            </button>
          </div>

          {/* Row 2: Next Question — full width */}
          <button
            onClick={() => nextQuestion()}
            disabled={!isAnswered}
            style={{
              padding: '0.75rem',
              background: isAnswered ? 'linear-gradient(135deg, #172a6e, #213b93)' : '#f4f6fb',
              color: isAnswered ? '#fff' : '#c4c9d8',
              border: 'none', borderRadius: '10px',
              fontSize: '0.82rem', fontWeight: 700,
              cursor: isAnswered ? 'pointer' : 'not-allowed',
              fontFamily: 'Georgia, serif',
              letterSpacing: '0.01em'
            }}
          >
            {practiceIndex + 1 >= total ? 'Finish Session →' : 'Next Question →'}
          </button>
        </div>
      </div>
    );
  };

  // ── Topic Setup Screen ────────────────────────────────────────────────────────
  const TopicSetup = ({ isMind }: { isMind: boolean }) => {
    const topics = syllabus || [];
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

        {/* Back button + header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => resetPractice()}
            style={{
              background: '#f0f3fc', border: 'none',
              color: '#213b93', width: '28px', height: '28px',
              borderRadius: '50%', cursor: 'pointer',
              fontSize: '0.9rem', display: 'flex',
              alignItems: 'center', justifyContent: 'center'
            }}
          >←</button>
          <span style={{
            fontSize: '0.72rem', fontWeight: 700,
            color: '#213b93', letterSpacing: '0.06em',
            textTransform: 'uppercase',
            fontFamily: 'system-ui, sans-serif'
          }}>
            {isMind ? 'Mind Maintenance' : 'AI Practice'}
          </span>
        </div>

        <p style={{
          fontSize: '0.78rem', color: '#6b7280',
          margin: 0, lineHeight: 1.5,
          fontFamily: 'system-ui, sans-serif'
        }}>
          {isMind
            ? 'Select difficulty level and topic — Fonus will create a mixed set of real PYQs and pattern-based questions.'
            : 'Choose a topic and generate a custom AI practice set tailored to CAR 66 exam patterns.'}
        </p>

        {/* Difficulty selector — Mind only */}
        {isMind && (
          <div>
            <p style={{
              fontSize: '0.68rem', fontWeight: 700, color: '#374151',
              marginBottom: '0.5rem', textTransform: 'uppercase',
              letterSpacing: '0.08em', fontFamily: 'system-ui, sans-serif'
            }}>Difficulty Level</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '0.5rem' }}>
              {(['easy', 'medium', 'hard'] as const).map(level => (
                <button
                  key={level}
                  onClick={() => setMindLevel(level)}
                  style={{
                    padding: '0.625rem',
                    background: mindLevel === level ? '#213b93' : '#f0f3fc',
                    color: mindLevel === level ? '#fff' : '#213b93',
                    border: `1.5px solid ${mindLevel === level ? '#213b93' : '#dde2f0'}`,
                    borderRadius: '8px', cursor: 'pointer',
                    fontSize: '0.72rem', fontWeight: 700,
                    textTransform: 'capitalize',
                    fontFamily: 'system-ui, sans-serif',
                    transition: 'all 0.15s'
                  }}
                >
                  {level === 'easy' ? '🟢 Easy' : level === 'medium' ? '🟡 Medium' : '🔴 Hard'}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Topic selection */}
        <div>
          <p style={{
            fontSize: '0.68rem', fontWeight: 700, color: '#374151',
            marginBottom: '0.5rem', textTransform: 'uppercase',
            letterSpacing: '0.08em', fontFamily: 'system-ui, sans-serif'
          }}>Select Topic</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem', marginBottom: '0.75rem' }}>
            {topics.slice(0, 12).map((topic: string) => (
              <button
                key={topic}
                onClick={() => setAiTopicInput(topic)}
                style={{
                  padding: '4px 12px',
                  background: aiTopicInput === topic ? '#213b93' : '#f0f3fc',
                  color: aiTopicInput === topic ? '#fff' : '#213b93',
                  border: `1px solid ${aiTopicInput === topic ? '#213b93' : '#dde2f0'}`,
                  borderRadius: '20px', cursor: 'pointer',
                  fontSize: '0.68rem', fontWeight: 600,
                  fontFamily: 'system-ui, sans-serif',
                  transition: 'all 0.15s'
                }}
              >
                {topic}
              </button>
            ))}
          </div>
          <input
            type="text"
            value={aiTopicInput}
            onChange={e => setAiTopicInput(e.target.value)}
            placeholder="Or type a custom topic..."
            style={{
              width: '100%', padding: '0.625rem 0.875rem',
              border: '1.5px solid #dde2f0', borderRadius: '8px',
              fontSize: '0.78rem', color: '#1a1f3a',
              background: '#f8faff', outline: 'none',
              fontFamily: 'system-ui, sans-serif',
              boxSizing: 'border-box' as const
            }}
          />
        </div>

        {/* Generate button */}
        <button
          onClick={() => generateAiQuestions(
            isMind ? `${aiTopicInput} level:${mindLevel}` : aiTopicInput,
            isMind
          )}
          disabled={!aiTopicInput.trim() || generatingQuestions}
          style={{
            padding: '0.875rem',
            background: aiTopicInput.trim() ? 'linear-gradient(135deg, #172a6e, #213b93)' : '#f4f6fb',
            color: aiTopicInput.trim() ? '#fff' : '#c4c9d8',
            border: 'none', borderRadius: '10px',
            fontSize: '0.85rem', fontWeight: 700,
            cursor: aiTopicInput.trim() ? 'pointer' : 'not-allowed',
            fontFamily: 'Georgia, serif',
            letterSpacing: '0.01em'
          }}
        >
          {generatingQuestions ? 'Generating...' : `Generate ${isMind ? 'Mind Maintenance' : 'Practice'} Set →`}
        </button>
      </div>
    );
  };


  // ── Panels ────────────────────────────────────────────────────────────────────
  const InfoPanel = () => (
    <div style={{ height: '100%', overflowY: 'auto', padding: '1rem' }}>
      <div style={{
        background: moduleAccess?.has_access 
          ? 'linear-gradient(135deg, #0d1b4b 0%, #172a6e 40%, #1e2d7a 60%, #172a6e 100%)'
          : 'linear-gradient(135deg, #172a6e, #213b93)',
        borderRadius: '12px',
        padding: '1rem',
        marginBottom: '0.5rem',
        color: '#fff',
        position: 'relative',
        overflow: 'hidden'
      }}>
        <style>{`
          @keyframes sheenMove {
            0% { transform: translateX(-100%) skewX(-15deg); }
            100% { transform: translateX(300%) skewX(-15deg); }
          }
          .module-info-sheen {
            animation: sheenMove 3s ease-in-out infinite;
            animation-delay: 1s;
          }
        `}</style>

        {moduleAccess?.has_access && (
          <>
            {/* Mirror sheen effect */}
            <div 
              className="module-info-sheen"
              style={{
                position: 'absolute', top: 0, left: 0,
                width: '40%', height: '100%',
                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)',
                pointerEvents: 'none', zIndex: 1
              }} 
            />
            {/* Gold wings in top-right corner */}
            <div 
              className="wings-badge"
              style={{
                position: 'absolute', top: '8px', right: '8px',
                zIndex: 2, lineHeight: 1
              }}
            >
              <svg width="52" height="28" viewBox="0 0 52 28" fill="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="metalGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#bf953f" />
                    <stop offset="25%" stopColor="#fcf6ba" />
                    <stop offset="50%" stopColor="#b38728" />
                    <stop offset="75%" stopColor="#fbf5b7" />
                    <stop offset="100%" stopColor="#aa771c" />
                  </linearGradient>
                </defs>
                {/* Center crown/star */}
                <polygon 
                  points="26,4 28,10 34,10 29,14 31,20 26,16.5 21,20 23,14 18,10 24,10" 
                  fill="url(#metalGrad)"
                  stroke="#c49a2a"
                  strokeWidth="0.5"
                />
                {/* Left wing upper */}
                <path d="M22,11 C18,9.5 12,7 4,9 C7,9.5 10,10.5 12,12 C9,11 6,11 2,12.5 C5,12.5 8.5,13.5 11,15 C8,14 5,14.5 2,16 C6,16 10,16 13,17.5 C11,17 9,17.5 7,19 C10,18 14,17 17,16 C19.5,15 22,13 22,11Z" 
                  fill="url(#metalGrad)"
                  stroke="#c49a2a"
                  strokeWidth="0.3"
                />
                {/* Right wing upper */}
                <path d="M30,11 C34,9.5 40,7 48,9 C45,9.5 42,10.5 40,12 C43,11 46,11 50,12.5 C47,12.5 43.5,13.5 41,15 C44,14 47,14.5 50,16 C46,16 42,16 39,17.5 C41,17 43,17.5 45,19 C42,18 38,17 35,16 C32.5,15 30,13 30,11Z" 
                  fill="url(#metalGrad)"
                  stroke="#c49a2a"
                  strokeWidth="0.3"
                />
                {/* Wing feather lines left */}
                <path d="M20,12.5 C15,11.5 9,10.5 4,11.5" stroke="#c49a2a" strokeWidth="0.5" opacity="0.7"/>
                <path d="M18,15 C13,14 8,13.5 3,15" stroke="#c49a2a" strokeWidth="0.5" opacity="0.7"/>
                <path d="M16,17.5 C12,17 8,16.5 5,17.5" stroke="#c49a2a" strokeWidth="0.5" opacity="0.6"/>
                {/* Wing feather lines right */}
                <path d="M32,12.5 C37,11.5 43,10.5 48,11.5" stroke="#c49a2a" strokeWidth="0.5" opacity="0.7"/>
                <path d="M34,15 C39,14 44,13.5 49,15" stroke="#c49a2a" strokeWidth="0.5" opacity="0.7"/>
                <path d="M36,17.5 C40,17 44,16.5 47,17.5" stroke="#c49a2a" strokeWidth="0.5" opacity="0.6"/>
              </svg>
            </div>
            {/* Thin gold top border */}
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0,
              height: '2px',
              background: 'linear-gradient(90deg, transparent, #e8b94f, transparent)',
              borderRadius: '12px 12px 0 0',
              zIndex: 2
            }} />
          </>
        )}

        <div style={{ fontSize: '2rem', fontWeight: 700, lineHeight: 1 }}>{moduleId}</div>
        <div style={{ fontSize: '0.85rem', opacity: 0.9, marginTop: '4px', fontWeight: 500 }}>{moduleName}</div>
        <div style={{ fontSize: '0.7rem', opacity: 0.6, marginTop: '2px' }}>CAR 66 Issue III Rev 2 · {stream}</div>
      </div>

      {showExpiryNotice && (
        <div style={{
          margin: '0.5rem 0',
          padding: '0.75rem',
          background: '#fffbeb',
          border: '1px solid #fcd34d',
          borderRadius: '10px',
          fontSize: '0.72rem',
          color: '#92400e',
          fontFamily: 'system-ui, sans-serif'
        }}>
          <div style={{ fontWeight: 700, marginBottom: '3px' }}>⚠️ Access expires in &lt;24 hrs</div>
          <div style={{ opacity: 0.8, marginBottom: '8px' }}>Renew to keep your progress streak going.</div>
          <button
            onClick={() => setIsBillingOpen(true)}
            style={{
              width: '100%', padding: '0.5rem',
              background: '#213b93', color: '#fff',
              border: 'none', borderRadius: '6px',
              fontSize: '0.72rem', fontWeight: 700,
              cursor: 'pointer', fontFamily: 'Georgia, serif'
            }}
          >
            Renew Access →
          </button>
        </div>
      )}

      {examQ > 0 && (
        <Accordion title="CAR 66 Exam Info" defaultOpen>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', textAlign: 'center', marginBottom: '0.5rem' }}>
            {[{ v: examQ, l: 'Questions' }, { v: `${examTime}m`, l: 'Total Time' }, { v: examPass, l: 'Pass Mark' }].map(i => (
              <div key={i.l} style={{ background: '#f8faff', borderRadius: '8px', padding: '0.5rem 0.25rem', border: '1px solid #e2e6f0' }}>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: '#213b93' }}>{i.v}</div>
                <div style={{ fontSize: '0.6rem', color: '#9ca3af' }}>{i.l}</div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: '0.68rem', color: '#9ca3af', textAlign: 'center' }}>75 sec/question · 75% pass required</p>
        </Accordion>
      )}

      {syllabus.length > 0 && (
        <Accordion title="DGCA Syllabus — CAR 66">
          {syllabus.map((s, i) => (
            <div key={i} style={{ display: 'flex', gap: '8px', padding: '0.4rem 0', borderBottom: '1px solid #f0f2f8' }}>
              <span style={{ fontSize: '0.6rem', color: '#213b93', fontWeight: 700, background: '#eef1fb', padding: '1px 5px', borderRadius: '3px', flexShrink: 0, marginTop: '2px' }}>{i + 1}</span>
              <span style={{ fontSize: '0.78rem', color: '#374151', lineHeight: 1.4 }}>{s}</span>
            </div>
          ))}
        </Accordion>
      )}

      <Accordion title="Source Documents">
        {sources.map(s => (
          <div key={s} style={{ display: 'flex', gap: '6px', padding: '4px 0', borderBottom: '1px solid #f0f2f8', alignItems: 'center' }}>
            <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
            <span style={{ fontSize: '0.78rem', color: '#374151' }}>{s}</span>
          </div>
        ))}
      </Accordion>

      <Accordion title="AI Engine">
        {[
          { id: 'groq', label: '⚡ Groq — Llama 3.3 70B', sub: 'Fast · Free · Default', locked: false },
          { id: 'gemini', label: '✨ Gemini 2.0 Flash', sub: '🔒 Unlock in Premium', locked: true },
          { id: 'gpt', label: '🧠 GPT-4o', sub: '🔒 Unlock in Premium', locked: true },
        ].map(l => (
          <button key={l.id} onClick={() => !l.locked && setPreferredLlm(l.id)} style={{ width: '100%', padding: '0.5rem 0.75rem', border: `1.5px solid ${preferredLlm === l.id ? '#213b93' : '#e2e6f0'}`, borderRadius: '8px', background: preferredLlm === l.id ? '#f0f3fc' : '#fff', cursor: l.locked ? 'not-allowed' : 'pointer', textAlign: 'left', marginBottom: '0.375rem', opacity: l.locked ? 0.55 : 1 }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#1a1f3a' }}>{l.label}</div>
            <div style={{ fontSize: '0.67rem', color: '#9ca3af' }}>{l.sub}</div>
          </button>
        ))}
      </Accordion>

      {/* Progress Tracker */}
      <div style={{ background: '#fff', borderRadius: '14px', padding: '1rem', marginBottom: '1rem', border: '1px solid #e2e6f0', borderTop: '2px solid #e8b94f' }}>
        <h3 style={{ fontSize: '0.82rem', fontWeight: 700, color: '#172a6e', margin: '0 0 0.875rem 0', fontFamily: 'Georgia, serif', textAlign: 'center' }}>Module Progress Tracker</h3>
        
        <button 
          onClick={handleOpenReport}
          style={{ width: '100%', padding: '0.625rem', background: '#f8faff', border: '1.5px solid #213b93', borderRadius: '8px', color: '#213b93', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer', fontFamily: 'Georgia, serif', transition: 'all 0.2s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
        >
          📊 View Full Report
        </button>
      </div>

      {/* Usage & Billing Button */}
      <div style={{ marginBottom: '0.5rem' }}>
        <style>{`
          @keyframes borderFlow {
            0% { border-color: rgba(33,59,147,0.4); box-shadow: 0 0 0 0 rgba(33,59,147,0); }
            50% { border-color: rgba(59,130,246,0.7); box-shadow: 0 2px 12px rgba(59,130,246,0.15); }
            100% { border-color: rgba(33,59,147,0.4); box-shadow: 0 0 0 0 rgba(33,59,147,0); }
          }
          .billing-btn {
            animation: borderFlow 3s ease-in-out infinite;
            transition: all 0.2s ease;
          }
          .billing-btn:hover {
            background: #f0f3fc !important;
            transform: none;
          }
        `}</style>
        <button
          className="billing-btn"
          onClick={() => setIsBillingOpen(true)}
          style={{
            width: '100%',
            padding: '0.75rem 0.875rem',
            background: '#f8faff',
            border: '1.5px solid #c7d2f5',
            borderRadius: '10px',
            color: '#172a6e',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontFamily: 'Georgia, serif',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '0.95rem' }}>⚡</span>
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#172a6e' }}>Usage & Billing</div>
              <div style={{ fontSize: '0.62rem', color: moduleAccess?.has_access ? '#4ade80' : '#9ca3af', marginTop: '1px' }}>
                {moduleAccess?.has_access ? '✓ Full Access Active' : 'Track · Promo · Upgrade'}
              </div>
            </div>
          </div>
          <span style={{ fontSize: '0.75rem', color: '#c7d2f5' }}>→</span>
        </button>
      </div>

      {/* Feedback Button */}
      <button 
        onClick={() => setIsFeedbackOpen(true)}
        style={{ width: '100%', padding: '0.75rem', marginTop: '1rem', background: '#fff', border: '1.5px solid #e2e6f0', borderRadius: '10px', color: '#1a1f3a', fontSize: '0.85rem', fontWeight: 600, cursor: 'pointer', transition: 'all 0.2s', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '0.5rem', fontFamily: 'Georgia, serif' }}
      >
        <span>💬</span> Give Feedback
      </button>
    </div>
  );

  // ChatPanel is defined outside ModuleContent (above) to avoid re-renders

  const PracticePanel = () => (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid #e2e6f0', flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ fontSize: '0.88rem', fontWeight: 700, color: '#172a6e' }}>Practice</h3>
          <p style={{ fontSize: '0.68rem', color: '#9ca3af' }}>PYQ · AI Session · Mind Maintenance</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          {practicePhase === 'mind_active' && <PracticeTimer timeLeft={timerDisplay} />}
          {practicePhase !== 'select' && <button onClick={resetPractice} style={{ background: 'none', border: '1px solid #e2e6f0', borderRadius: '6px', padding: '3px 10px', fontSize: '0.7rem', color: '#6b7280', cursor: 'pointer' }}>Reset</button>}
        </div>
      </div>

      {['pyq', 'ai_active', 'mind_active'].includes(practicePhase) && (
        <div style={{ padding: '0.5rem 1.25rem', flexShrink: 0 }}>
          <div style={{ height: '3px', background: '#f0f2f8', borderRadius: '2px' }}>
            <div style={{ height: '100%', background: '#213b93', borderRadius: '2px', transition: 'width 0.3s', width: `${practiceQuestions.length > 0 ? ((practiceIndex + 1) / practiceQuestions.length) * 100 : 0}%` }} />
          </div>
          <p style={{ fontSize: '0.68rem', color: '#9ca3af', marginTop: '4px' }}>Q{practiceIndex + 1}/{practiceQuestions.length} · {score}/{answered} correct</p>
        </div>
      )}

      <div style={{ flex: 1, overflowY: 'auto', padding: '1rem 1.25rem' }}>
        {practicePhase === 'select' && (
          <div>
            <p style={{ fontSize: '0.78rem', color: '#6b7280', marginBottom: '1rem', lineHeight: 1.5 }}>Choose your practice mode:</p>
            {[
              { phase: 'pyq' as const, icon: '📋', title: 'Random PYQ Session', desc: 'Real past exam questions · CAR 66 standard · 75% pass mark', color: '#213b93', bg: '#f0f3fc', border: '#c7d2f5', action: startPYQ },
              { phase: 'ai_setup' as const, icon: '🤖', title: 'AI Practice Session', desc: 'AI-generated questions on your chosen topic · Instant explanations', color: '#047857', bg: '#f0fdf4', border: '#a7f3d0', action: () => setPracticePhase('ai_setup') },
              { phase: 'mind_setup' as const, icon: '🔀', title: 'Mind Maintenance', desc: 'Twisted scenario-based questions · Exam feel · With timer', color: '#7c3aed', bg: '#faf5ff', border: '#ddd6fe', action: () => setPracticePhase('mind_setup') },
            ].map(opt => (
              <button key={opt.phase} onClick={opt.action} style={{ width: '100%', padding: '0.875rem', border: `1.5px solid ${opt.border}`, borderRadius: '12px', background: opt.bg, cursor: 'pointer', textAlign: 'left', marginBottom: '0.75rem', transition: 'all 0.15s' }}>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                  <span style={{ fontSize: '1.4rem', flexShrink: 0 }}>{opt.icon}</span>
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 700, color: opt.color, marginBottom: '3px' }}>{opt.title}</div>
                    <div style={{ fontSize: '0.73rem', color: '#6b7280', lineHeight: 1.5 }}>{opt.desc}</div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}

        {practicePhase === 'ai_setup' && <TopicSetup isMind={false} />}
        {practicePhase === 'mind_setup' && <TopicSetup isMind={true} />}

        {generatingQuestions && (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: '2rem' }}>
            <FonusLoader message={practicePhase === 'mind_setup' ? 'Building your mind maintenance set...' : 'Generating your AI practice set...'} />
          </div>
        )}

        {['pyq', 'ai_active', 'mind_active'].includes(practicePhase) && !generatingQuestions && <QuestionDisplay />}

        {practicePhase === 'complete' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

            {/* Score card */}
            <div style={{
              background: 'linear-gradient(135deg, #0d1b4b, #172a6e)',
              borderRadius: '16px', padding: '1.5rem',
              textAlign: 'center', color: '#fff',
              border: '1px solid rgba(232,185,79,0.15)'
            }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>
                {(score / Math.max(answered, 1)) * 100 >= 75 ? '🏆' : '📚'}
              </div>
              <div style={{
                fontSize: '0.65rem', fontWeight: 700,
                color: 'rgba(232,185,79,0.8)',
                letterSpacing: '0.14em', textTransform: 'uppercase',
                fontFamily: 'system-ui, sans-serif', marginBottom: '8px'
              }}>Session Complete</div>
              <div style={{
                fontSize: '3rem', fontWeight: 800,
                color: '#fff', lineHeight: 1,
                letterSpacing: '-0.02em'
              }}>
                {score}<span style={{ fontSize: '1.5rem', opacity: 0.5 }}>/{answered}</span>
              </div>
              <div style={{
                fontSize: '1.2rem', fontWeight: 700,
                color: '#e8b94f', marginTop: '4px'
              }}>
                {Math.round((score / Math.max(answered, 1)) * 100)}%
              </div>
              <div style={{
                fontSize: '0.72rem', marginTop: '8px',
                color: 'rgba(255,255,255,0.5)',
                fontFamily: 'system-ui, sans-serif'
              }}>
                Pass mark: 75%
              </div>
            </div>

            {/* Pass/fail message */}
            <div style={{
              padding: '0.875rem',
              background: (score / Math.max(answered, 1)) * 100 >= 75 ? '#f0fdf4' : '#fef2f2',
              borderRadius: '12px',
              border: `1px solid ${(score / Math.max(answered, 1)) * 100 >= 75 ? '#86efac' : '#fca5a5'}`,
              textAlign: 'center'
            }}>
              <div style={{
                fontSize: '0.85rem', fontWeight: 700,
                color: (score / Math.max(answered, 1)) * 100 >= 75 ? '#16a34a' : '#dc2626',
                fontFamily: 'Georgia, serif'
              }}>
                {(score / Math.max(answered, 1)) * 100 >= 75
                  ? '✅ Above pass mark — well done!'
                  : '❌ Below pass mark — review and retry'}
              </div>
              <div style={{
                fontSize: '0.68rem', color: '#6b7280',
                marginTop: '4px', fontFamily: 'system-ui, sans-serif'
              }}>
                {(score / Math.max(answered, 1)) * 100 >= 75
                  ? 'You are on track for your CAR 66 exam.'
                  : 'Focus on the topics you missed and try again.'}
              </div>
            </div>

            {/* Question review */}
            {answeredQuestions.filter(Boolean).length > 0 && (
              <div>
                <p style={{
                  fontSize: '0.68rem', fontWeight: 700, color: '#374151',
                  textTransform: 'uppercase', letterSpacing: '0.08em',
                  marginBottom: '0.5rem', fontFamily: 'system-ui, sans-serif'
                }}>Quick Review</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
                  {answeredQuestions.filter(Boolean).map((q, i) => (
                    <div key={i} style={{
                      padding: '0.5rem 0.75rem',
                      background: q.selected === q.correct ? '#f0fdf4' : '#fef2f2',
                      borderRadius: '8px',
                      border: `1px solid ${q.selected === q.correct ? '#86efac' : '#fca5a5'}`,
                      display: 'flex', alignItems: 'center', gap: '8px'
                    }}>
                      <span style={{ fontSize: '0.75rem', flexShrink: 0 }}>
                        {q.selected === q.correct ? '✅' : '❌'}
                      </span>
                      <span style={{
                        fontSize: '0.68rem', color: '#374151',
                        fontFamily: 'system-ui, sans-serif',
                        overflow: 'hidden', textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap', flex: 1
                      }}>Q{i+1}: {q.question}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Practice again button */}
            <button
              onClick={() => resetPractice()}
              style={{
                padding: '0.875rem',
                background: 'linear-gradient(135deg, #172a6e, #213b93)',
                color: '#fff', border: 'none', borderRadius: '10px',
                fontSize: '0.85rem', fontWeight: 700,
                cursor: 'pointer', fontFamily: 'Georgia, serif'
              }}
            >
              Practice Again →
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#f0f2f8', fontFamily: 'Georgia, serif' }}>
      <NavBar>
        <button onClick={() => router.push(`/modules?stream=${stream}`)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6b7280', fontSize: '1.1rem', padding: '4px 8px', borderRadius: '6px' }}>←</button>
        <div style={{ width: '1px', height: '16px', background: '#e2e6f0' }} />
        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#213b93', background: '#eef1fb', padding: '2px 8px', borderRadius: '5px' }}>{moduleId}</span>
        <span style={{ fontSize: '0.85rem', color: '#1a1f3a', fontWeight: 500, marginRight: '1rem' }}>{moduleName}</span>
        <span style={{ fontSize: '0.75rem', color: '#9ca3af', background: '#f0f2f8', padding: '3px 10px', borderRadius: '12px' }}>{stream}</span>
      </NavBar>

      <style>{`
        .desktop-layout { display: flex !important; }
        .mobile-layout { display: none !important; }
        @media (max-width: 900px) {
          .desktop-layout { display: none !important; }
          .mobile-layout { display: flex !important; }
        }
      `}</style>

      <div className="desktop-layout" style={{ flex: 1, overflow: 'hidden' }}>
        <div style={{ width: '248px', flexShrink: 0, background: '#fff', borderRight: '1px solid #e2e6f0', overflow: 'hidden' }}><InfoPanel /></div>
        <div style={{ flex: 1, overflow: 'hidden', minWidth: 0, display: 'flex', flexDirection: 'column' }}>
          <ChatPanel messages={messages} loading={loading} chatInput={chatInput} setChatInput={setChatInput} sendMessage={sendMessage} moduleName={moduleName} messagesEndRef={messagesEndRef} suggestions={suggestions} onClearChat={handleClearChat} typingMessageId={typingMessageId} displayedContent={displayedContent} />
        </div>
        <div style={{ width: '356px', flexShrink: 0, background: '#fff', borderLeft: '1px solid #e2e6f0', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}><PracticePanel /></div>
      </div>

      <div className="mobile-layout" style={{ flex: 1, flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{ flex: 1, overflow: 'hidden', background: '#fff' }}>
          {mobileTab === 'info' && <InfoPanel />}
          {mobileTab === 'chat' && <ChatPanel messages={messages} loading={loading} chatInput={chatInput} setChatInput={setChatInput} sendMessage={sendMessage} moduleName={moduleName} messagesEndRef={messagesEndRef} suggestions={suggestions} onClearChat={handleClearChat} typingMessageId={typingMessageId} displayedContent={displayedContent} />}
          {mobileTab === 'practice' && <PracticePanel />}
        </div>
        <div style={{ height: '56px', background: '#fff', borderTop: '1px solid #e2e6f0', display: 'flex', flexShrink: 0 }}>
          {[{ id: 'info' as const, icon: '📋', label: 'Info' }, { id: 'chat' as const, icon: '💬', label: 'Chat' }, { id: 'practice' as const, icon: '📝', label: 'Practice' }].map(tab => (
            <button key={tab.id} onClick={() => setMobileTab(tab.id)} style={{ flex: 1, height: '100%', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '3px', color: mobileTab === tab.id ? '#213b93' : '#9ca3af', borderTop: `2px solid ${mobileTab === tab.id ? '#213b93' : 'transparent'}` }}>
              <span style={{ fontSize: '1.2rem' }}>{tab.icon}</span>
              <span style={{ fontSize: '0.63rem', fontWeight: mobileTab === tab.id ? 700 : 400 }}>{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {isBillingOpen && (
  <div
    onClick={(e) => { if (e.target === e.currentTarget) setIsBillingOpen(false); }}
    style={{
      position: 'fixed', inset: 0,
      background: 'rgba(5,10,30,0.85)',
      backdropFilter: 'blur(12px)',
      zIndex: 200,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      fontFamily: 'Georgia, serif'
    }}
  >
    <style>{`
      @keyframes modalIn {
        from { opacity: 0; transform: translateY(24px) scale(0.97); }
        to { opacity: 1; transform: translateY(0) scale(1); }
      }
      @keyframes barFill {
        from { width: 0%; }
        to { width: var(--bar-width); }
      }
      .billing-modal { animation: modalIn 0.35s cubic-bezier(0.16,1,0.3,1) forwards; }
      .plan-card { transition: transform 0.15s ease, box-shadow 0.15s ease; }
      .plan-card:hover { transform: translateY(-3px); box-shadow: 0 12px 40px rgba(13,27,75,0.18); }
      .plan-card-popular:hover { box-shadow: 0 12px 40px rgba(232,185,79,0.25); }
      @media (max-width: 600px) {
        .billing-modal-wrap {
          position: fixed !important;
          bottom: 0 !important;
          left: 0 !important;
          right: 0 !important;
          max-width: 100% !important;
          border-radius: 24px 24px 0 0 !important;
          max-height: 92vh !important;
        }
      }
    `}</style>

    <div
      className="billing-modal billing-modal-wrap"
      style={{
        background: '#0a1628',
        borderRadius: '24px',
        width: '100%',
        maxWidth: '660px',
        maxHeight: '88vh',
        overflowY: 'auto',
        boxShadow: '0 40px 100px rgba(0,0,0,0.5), 0 0 0 1px rgba(232,185,79,0.12)',
        position: 'relative',
      }}
    >
      {/* Gold top accent line */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: '2px',
        background: 'linear-gradient(90deg, transparent 0%, #e8b94f 30%, #f5d07a 50%, #e8b94f 70%, transparent 100%)',
        borderRadius: '24px 24px 0 0'
      }} />

      {/* HEADER */}
      <div style={{
        padding: '2rem 2rem 1.5rem',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        position: 'sticky', top: 0,
        background: '#0a1628',
        borderRadius: '24px 24px 0 0',
        zIndex: 10
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <div style={{
              width: '6px', height: '6px', borderRadius: '50%',
              background: '#e8b94f',
              boxShadow: '0 0 8px #e8b94f'
            }} />
            <span style={{
              fontSize: '0.62rem', fontWeight: 700,
              color: 'rgba(232,185,79,0.7)',
              letterSpacing: '0.18em', textTransform: 'uppercase',
              fontFamily: 'system-ui, sans-serif'
            }}>
              Fonus · {moduleId} · {moduleName}
            </span>
          </div>
          <h2 style={{
            fontSize: '1.5rem', fontWeight: 700,
            color: '#fff', margin: 0,
            letterSpacing: '-0.02em'
          }}>Plans & Access</h2>
          <p style={{
            fontSize: '0.72rem', color: 'rgba(255,255,255,0.35)',
            margin: '4px 0 0', fontFamily: 'system-ui, sans-serif'
          }}>CAR 66 AME Exam Preparation · Per module pricing</p>
        </div>
        <button
          onClick={() => setIsBillingOpen(false)}
          style={{
            background: 'rgba(255,255,255,0.06)',
            border: '1px solid rgba(255,255,255,0.08)',
            color: 'rgba(255,255,255,0.5)',
            width: '32px', height: '32px',
            borderRadius: '50%', cursor: 'pointer',
            fontSize: '1rem', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, transition: 'all 0.15s'
          }}
        >×</button>
      </div>

      <div style={{ padding: '1.75rem 2rem 2rem' }}>

        {/* PLAN CARDS — 2x2 grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '0.75rem',
          marginBottom: '1.75rem'
        }}>
          {[
            {
              key: 'free', label: 'Free', price: '₹0', sub: 'Weekly credits',
              duration: '', amount: '', current: !moduleAccess?.has_access, popular: false,
              features: ['18 hrs AI chat / week', '9 practice sets / week', '3 per section limit', 'Basic module access'],
              accent: 'rgba(255,255,255,0.12)'
            },
            {
              key: 'week', label: '1 Week', price: '₹49', sub: '6 days unlimited',
              duration: '1 Week', amount: '₹49', current: false, popular: false,
              features: ['Unlimited AI chat', 'All PYQs unlocked', 'AI + Mind Maintenance', 'Progress dashboard'],
              accent: 'rgba(255,255,255,0.08)'
            },
            {
              key: 'month', label: '1 Month', price: '₹199', sub: '29 days unlimited',
              duration: '1 Month', amount: '₹199', current: false, popular: true,
              features: ['Unlimited ₹49 plan access for 1 month', 'Exam readiness score', 'Full progress history', 'Best for most students'],
              accent: '#e8b94f'
            },
            {
              key: '3month', label: '3 Months', price: '₹499', sub: '89 days unlimited',
              duration: '3 Months', amount: '₹499', current: false, popular: false,
              features: ['Unlimited ₹49 plan access for 3 months', 'Deepest exam prep', 'Complete topic coverage', 'Thorough preparation'],
              accent: 'rgba(255,255,255,0.08)'
            },
          ].map(plan => (
            <button
              key={plan.key}
              className={`plan-card${plan.popular ? ' plan-card-popular' : ''}`}
              onClick={() => {
                if (!plan.current && plan.amount) {
                  setSelectedPlan({ amount: plan.amount, duration: plan.duration });
                  setIsBillingOpen(false);
                  setIsPayModalOpen(true);
                }
              }}
              style={{
                padding: '1.25rem',
                border: plan.popular
                  ? '1.5px solid rgba(232,185,79,0.5)'
                  : plan.current
                  ? '1.5px solid rgba(255,255,255,0.08)'
                  : '1.5px solid rgba(255,255,255,0.08)',
                borderRadius: '16px',
                background: plan.popular
                  ? 'linear-gradient(135deg, #172a6e 0%, #1e3a8a 100%)'
                  : 'rgba(255,255,255,0.04)',
                cursor: plan.current ? 'default' : 'pointer',
                textAlign: 'left',
                position: 'relative',
                overflow: 'hidden',
                width: '100%'
              }}
            >
              {plan.popular && (
                <div style={{
                  position: 'absolute', top: 0, right: 0,
                  background: '#e8b94f', color: '#0a1628',
                  fontSize: '0.52rem', fontWeight: 800,
                  padding: '4px 10px',
                  borderRadius: '0 16px 0 8px',
                  letterSpacing: '0.1em',
                  fontFamily: 'system-ui, sans-serif'
                }}>POPULAR</div>
              )}
              {/* Subtle shine for popular */}
              {plan.popular && (
                <div style={{
                  position: 'absolute', top: 0, left: 0, right: 0,
                  height: '1px',
                  background: 'linear-gradient(90deg, transparent, rgba(232,185,79,0.6), transparent)'
                }} />
              )}
              <div style={{ marginBottom: '1rem' }}>
                <div style={{
                  fontSize: '0.65rem', fontWeight: 700,
                  color: plan.popular ? '#e8b94f' : 'rgba(255,255,255,0.7)',
                  fontFamily: 'system-ui, sans-serif',
                  letterSpacing: '0.08em', textTransform: 'uppercase',
                  marginBottom: '4px'
                }}>{plan.label}</div>
                <div style={{
                  fontSize: '2rem', fontWeight: 800,
                  color: plan.popular ? '#e8b94f' : '#fff',
                  lineHeight: 1, letterSpacing: '-0.02em'
                }}>{plan.price}</div>
                <div style={{
                  fontSize: '0.72rem',
                  color: plan.popular ? 'rgba(255,255,255,0.75)' : 'rgba(255,255,255,0.65)',
                  fontFamily: 'system-ui, sans-serif', marginTop: '4px'
                }}>{plan.sub}</div>
              </div>
              <div style={{
                borderTop: '1px solid rgba(255,255,255,0.06)',
                paddingTop: '0.75rem',
                display: 'flex', flexDirection: 'column', gap: '5px'
              }}>
                {plan.features.map(f => (
                  <div key={f} style={{ display: 'flex', gap: '6px', alignItems: 'flex-start' }}>
                    <span style={{
                      color: plan.popular ? '#e8b94f' : 'rgba(255,255,255,0.6)',
                      fontSize: '0.6rem', marginTop: '2px', flexShrink: 0
                    }}>✓</span>
                    <span style={{
                      fontSize: '0.68rem',
                      color: 'rgba(255,255,255,0.85)',
                      lineHeight: 1.4, fontFamily: 'system-ui, sans-serif'
                    }}>{f}</span>
                  </div>
                ))}
              </div>
              {plan.current && (
                <div style={{
                  marginTop: '0.75rem', textAlign: 'center',
                  fontSize: '0.6rem',
                  background: 'rgba(255,255,255,0.06)',
                  color: 'rgba(255,255,255,0.4)',
                  padding: '4px 0', borderRadius: '6px',
                  fontWeight: 600, fontFamily: 'system-ui, sans-serif'
                }}>Current Plan</div>
              )}
              {!plan.current && (
                <div style={{
                  marginTop: '0.75rem', textAlign: 'center',
                  fontSize: '0.7rem',
                  color: plan.popular ? '#e8b94f' : 'rgba(255,255,255,0.4)',
                  fontWeight: 600, fontFamily: 'system-ui, sans-serif',
                  letterSpacing: '0.04em'
                }}>Select →</div>
              )}
            </button>
          ))}
        </div>

        {/* FREE USAGE TRACKER */}
        <div style={{
          background: 'rgba(255,255,255,0.03)',
          borderRadius: '16px', padding: '1.25rem',
          marginBottom: '1.25rem',
          border: '1px solid rgba(255,255,255,0.06)'
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', marginBottom: '1rem'
          }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fff' }}>
              📊 Free Usage — This Week
            </span>
            <span style={{
              fontSize: '0.62rem', color: 'rgba(255,255,255,0.3)',
              fontFamily: 'system-ui, sans-serif'
            }}>Resets every Monday</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            {[
              {
                label: 'Chat Hours',
                used: usageLoading ? '...' : usageData ? String(usageData.chat_hours_used) : '0',
                total: 18, unit: 'hrs', icon: '💬',
                note: 'continuous or split'
              },
              {
                label: 'Practice Sets',
                used: usageLoading ? '...' : usageData ? String(usageData.practice_sets_used) : '0',
                total: 9, unit: 'sets', icon: '📝',
                note: '3 per section max'
              },
            ].map(item => {
              const usedNum = parseFloat(item.used) || 0;
              const pct = Math.min((usedNum / item.total) * 100, 100);
              const barColor = pct >= 90 ? '#ef4444' : pct >= 65 ? '#f59e0b' : '#e8b94f';
              return (
                <div key={item.label} style={{
                  background: 'rgba(255,255,255,0.04)',
                  borderRadius: '12px', padding: '1rem',
                  border: '1px solid rgba(255,255,255,0.06)'
                }}>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: '0.625rem'
                  }}>
                    <span style={{
                      fontSize: '0.65rem', color: 'rgba(255,255,255,0.45)',
                      fontFamily: 'system-ui, sans-serif'
                    }}>{item.label}</span>
                    <span style={{ fontSize: '0.85rem' }}>{item.icon}</span>
                  </div>
                  <div style={{
                    display: 'flex', alignItems: 'baseline',
                    gap: '4px', marginBottom: '8px'
                  }}>
                    <span style={{
                      fontSize: '1.75rem', fontWeight: 700,
                      color: '#fff', lineHeight: 1
                    }}>{item.used}</span>
                    <span style={{
                      fontSize: '0.62rem', color: 'rgba(255,255,255,0.3)',
                      fontFamily: 'system-ui, sans-serif'
                    }}>/ {item.total} {item.unit}</span>
                  </div>
                  <div style={{
                    height: '3px', background: 'rgba(255,255,255,0.08)',
                    borderRadius: '2px', marginBottom: '6px'
                  }}>
                    <div style={{
                      height: '100%',
                      width: `${pct}%`,
                      background: barColor,
                      borderRadius: '2px',
                      transition: 'width 0.6s cubic-bezier(0.34,1.56,0.64,1)',
                      boxShadow: `0 0 6px ${barColor}60`
                    }} />
                  </div>
                  <p style={{
                    fontSize: '0.58rem', color: 'rgba(255,255,255,0.2)',
                    margin: 0, fontFamily: 'system-ui, sans-serif'
                  }}>{item.note}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* PROMO CODE */}
        <div style={{
          background: 'rgba(232,185,79,0.05)',
          borderRadius: '16px', padding: '1.25rem',
          border: '1px solid rgba(232,185,79,0.15)',
          marginBottom: '1.25rem'
        }}>
          <div style={{
            display: 'flex', alignItems: 'center',
            gap: '8px', marginBottom: '1rem'
          }}>
            <span style={{ fontSize: '1rem' }}>🎟️</span>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#e8b94f' }}>
              Promo Code
            </span>
            <span style={{
              fontSize: '0.65rem', color: 'rgba(232,185,79,0.5)',
              fontFamily: 'system-ui, sans-serif'
            }}>— get free access instantly</span>
          </div>

          {promoSuccess ? (
            <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>🎉</div>
              <div style={{ color: '#4ade80', fontSize: '1rem', fontWeight: 700 }}>
                Access Unlocked!
              </div>
              <div style={{
                color: 'rgba(255,255,255,0.4)', fontSize: '0.72rem',
                marginTop: '4px', fontFamily: 'system-ui, sans-serif'
              }}>Refreshing your module...</div>
            </div>
          ) : (
            <>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.625rem' }}>
                <input
                  type="text"
                  value={promoCode}
                  onChange={(e) => { setPromoCode(e.target.value.toUpperCase()); setPromoResult(null); }}
                  placeholder="e.g. FONUS1MONTH"
                  style={{
                    flex: 1, padding: '0.75rem 1rem',
                    background: 'rgba(255,255,255,0.06)',
                    border: `1.5px solid ${promoResult?.valid === false ? 'rgba(239,68,68,0.5)' : promoResult?.valid === true ? 'rgba(74,222,128,0.5)' : 'rgba(232,185,79,0.2)'}`,
                    borderRadius: '10px', color: '#fff',
                    fontSize: '0.85rem', outline: 'none',
                    fontFamily: 'monospace', letterSpacing: '0.06em'
                  }}
                />
                <button
                  onClick={handlePromoCheck}
                  disabled={promoChecking || !promoCode.trim()}
                  style={{
                    padding: '0.75rem 1.25rem',
                    background: promoCode.trim() ? '#e8b94f' : 'rgba(255,255,255,0.06)',
                    color: promoCode.trim() ? '#0a1628' : 'rgba(255,255,255,0.25)',
                    border: 'none', borderRadius: '10px',
                    fontSize: '0.78rem', fontWeight: 700,
                    cursor: promoCode.trim() ? 'pointer' : 'not-allowed',
                    whiteSpace: 'nowrap',
                    fontFamily: 'system-ui, sans-serif',
                    transition: 'all 0.15s'
                  }}
                >
                  {promoChecking ? 'Checking...' : 'Apply'}
                </button>
              </div>

              {promoResult && (
                <div style={{ marginTop: '0.625rem' }}>
                  {promoResult.valid ? (
                    <div>
                      <div style={{
                        display: 'flex', alignItems: 'center', gap: '6px',
                        color: '#4ade80', fontSize: '0.75rem', fontWeight: 600,
                        marginBottom: '0.75rem', fontFamily: 'system-ui, sans-serif'
                      }}>
                        <span>✅</span>{promoResult.message}
                      </div>
                      <button
                        onClick={handlePromoRedeem}
                        disabled={promoRedeeming}
                        style={{
                          width: '100%', padding: '0.875rem',
                          background: 'linear-gradient(135deg, #172a6e, #213b93)',
                          color: '#fff', border: '1px solid rgba(232,185,79,0.3)',
                          borderRadius: '10px', fontSize: '0.9rem', fontWeight: 700,
                          cursor: promoRedeeming ? 'not-allowed' : 'pointer',
                          fontFamily: 'Georgia, serif',
                          letterSpacing: '0.01em',
                          transition: 'all 0.15s'
                        }}
                      >
                        {promoRedeeming ? 'Activating...' : '🎁 Claim Free Access →'}
                      </button>
                    </div>
                  ) : (
                    <div style={{
                      display: 'flex', alignItems: 'center', gap: '6px',
                      color: '#f87171', fontSize: '0.75rem',
                      fontFamily: 'system-ui, sans-serif'
                    }}>
                      <span>❌</span>{promoResult.message}
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* FOOTER */}
        <div style={{
          textAlign: 'center',
          paddingTop: '1rem',
          borderTop: '1px solid rgba(255,255,255,0.05)'
        }}>
          <p style={{
            fontSize: '0.62rem', color: 'rgba(255,255,255,0.2)',
            margin: '0 0 3px', fontFamily: 'system-ui, sans-serif'
          }}>Per module · No hidden fees · Free tier capped at <strong style={{color: 'rgba(255,255,255,0.35)'}}>9 practice sets / week</strong> and{' '}
            <strong style={{color: 'rgba(255,255,255,0.35)'}}>18 chat hours / week</strong> (shown above)
          </p>
          <p style={{
            fontSize: '0.62rem', color: 'rgba(232,185,79,0.45)',
            margin: '0 0 3px', fontFamily: 'system-ui, sans-serif'
          }}>
            Tester window: redeem <strong style={{letterSpacing: '0.06em'}}>FONUS1MONTH</strong> below for ~30 days all-module access once the code exists in Supabase (see{' '}
            <span style={{ fontFamily: 'monospace', fontSize: '0.58rem', color: 'rgba(255,255,255,0.35)' }}>backend/sql/promo_fonus1month.sql</span>
            ).
          </p>
          <p style={{
            fontSize: '0.62rem', color: 'rgba(255,255,255,0.15)',
            margin: 0, fontFamily: 'system-ui, sans-serif'
          }}>Contact: fonuslearning@gmail.com</p>
        </div>

      </div>
    </div>
  </div>
)}

      {isFeedbackOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#fff', borderRadius: '16px', width: '90%', maxWidth: '450px', padding: '1.5rem', boxShadow: '0 10px 25px rgba(0,0,0,0.2)', position: 'relative' }}>
            <button onClick={() => setIsFeedbackOpen(false)} style={{ position: 'absolute', top: '15px', right: '15px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem', color: '#6b7280' }}>×</button>
             <h2 style={{ fontSize: '1.25rem', color: '#172a6e', marginBottom: '1rem', fontFamily: 'Georgia, serif', fontWeight: 700 }}>Feedback</h2>
            
            {showSuccess ? (
              <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
                <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>✅</div>
                <h3 style={{ color: '#22c55e', fontSize: '1.1rem', marginBottom: '0.5rem' }}>Thank you!</h3>
                <p style={{ color: '#6b7280', fontSize: '0.85rem' }}>Your feedback has been submitted successfully.</p>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', background: '#f0f2f8', padding: '0.3rem', borderRadius: '8px' }}>
                  {[{ id: 1, label: 'Suggest Change' }, { id: 2, label: 'Query' }, { id: 3, label: 'General' }].map(tab => (
                    <button key={tab.id} onClick={() => setFeedbackTab(tab.id as 1 | 2 | 3)} style={{ flex: 1, padding: '0.5rem 0.25rem', background: feedbackTab === tab.id ? '#fff' : 'transparent', border: 'none', borderRadius: '6px', fontSize: '0.75rem', fontWeight: feedbackTab === tab.id ? 700 : 500, color: feedbackTab === tab.id ? '#213b93' : '#6b7280', boxShadow: feedbackTab === tab.id ? '0 1px 3px rgba(0,0,0,0.1)' : 'none', cursor: 'pointer', transition: 'all 0.2s' }}>
                      {tab.label}
                    </button>
                  ))}
                </div>
                <p style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.5rem' }}>Module: <strong style={{ color: '#213b93' }}>{moduleId}</strong> (Auto-selected)</p>
                <textarea
                  value={feedbackMessage}
                  onChange={e => { setFeedbackMessage(e.target.value); setFeedbackError(''); }}
                  placeholder="Type your message here..."
                  rows={4}
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1px solid #e2e6f0', fontSize: '0.85rem', fontFamily: 'inherit', resize: 'vertical', marginBottom: '1rem', boxSizing: 'border-box' }}
                />
                {feedbackError && (
                  <p style={{ color: '#ef4444', fontSize: '0.8rem', marginBottom: '0.75rem', textAlign: 'center', fontWeight: 500 }}>
                    {feedbackError}
                  </p>
                )}
                <button 
                  onClick={submitFeedback}
                  disabled={isSubmitting || !feedbackMessage.trim()}
                  style={{ width: '100%', padding: '0.75rem', background: isSubmitting || !feedbackMessage.trim() ? '#e2e6f0' : '#213b93', color: isSubmitting || !feedbackMessage.trim() ? '#9ca3af' : '#fff', border: 'none', borderRadius: '8px', fontSize: '0.9rem', fontWeight: 600, cursor: isSubmitting || !feedbackMessage.trim() ? 'not-allowed' : 'pointer' }}
                >
                  {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          EXAM READINESS DASHBOARD MODAL
          ───────────────────────────────────────────────────────────── */}
      {isReportOpen && (() => {
        if (showGoalSetup) {
          return (
            <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Georgia, serif' }}>
              <div style={{ background: '#fff', borderRadius: '16px', padding: '2.5rem', width: '90%', maxWidth: '480px', textAlign: 'center', position: 'relative' }}>
                <button onClick={() => setIsReportOpen(false)} style={{ position: 'absolute', top: '1rem', right: '1.25rem', background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.5rem', color: '#6b7280' }}>×</button>
                <div style={{ fontSize: '3rem', margin: '0 0 1rem' }}>🎯</div>
                <h2 style={{ fontSize: '1.5rem', color: '#172a6e', margin: '0 0 0.5rem', fontWeight: 700 }}>Set Your Practice Goal</h2>
                <p style={{ color: '#6b7280', marginBottom: '2rem', fontSize: '0.95rem' }}>Set a target for total questions to solve across all modes for {moduleId}. Min 1000.</p>
                <input
                  type="number" min="1000" value={goalInput}
                  onChange={e => setGoalInput(parseInt(e.target.value) || 0)}
                  style={{ width: '100%', padding: '1rem', fontSize: '1.2rem', textAlign: 'center', borderRadius: '8px', border: '2px solid #e2e6f0', outline: 'none', marginBottom: '1.5rem', color: '#1a1f3a', fontWeight: 'bold' }}
                />
                <button onClick={saveGoal} disabled={isSettingGoal}
                  style={{ width: '100%', padding: '1rem', background: '#213b93', color: '#fff', border: 'none', borderRadius: '8px', fontSize: '1rem', fontWeight: 600, cursor: isSettingGoal ? 'not-allowed' : 'pointer' }}>
                  {isSettingGoal ? 'Saving Goal...' : 'Set Goal'}
                </button>
              </div>
            </div>
          );
        }

        /* ── compute readiness from syllabus + topic_stats ── */
        const topicStats: Record<string, number> = (progressStats as any).topic_stats || {};
        const syllabusTopics: Record<string, { name: string; level: number; target: number }> = dashboardSyllabus?.topics || {};

        const topicList = Object.entries(syllabusTopics)
          .map(([id, t]) => {
            const done = topicStats[id] || 0;
            const pctOfTarget = t.target > 0 ? Math.min(done / t.target, 1) : 0;
            const contribution = pctOfTarget * t.level;
            return { id, name: t.name, level: t.level, target: t.target, done, pctOfTarget, contribution };
          })
          .sort((a, b) => b.level - a.level || a.done - b.done);   // L3 first, then by least done

        const sumWeights = topicList.reduce((s, t) => s + t.level, 0);
        const sumContrib = topicList.reduce((s, t) => s + t.contribution, 0);
        const readinessScore = sumWeights > 0 ? Math.round((sumContrib / sumWeights) * 100) : 0;

        const ringColor = readinessScore >= 75 ? '#22c55e' : readinessScore >= 50 ? '#f59e0b' : '#ef4444';
        const ringBg = readinessScore >= 75 ? '#f0fdf4' : readinessScore >= 50 ? '#fffbeb' : '#fef2f2';

        /* SVG ring math */
        const R = 62, CIRC = 2 * Math.PI * R;
        const dash = (readinessScore / 100) * CIRC;

        /* top-3 weakest: lowest pctOfTarget that aren't 100% done */
        const weakTopics = [...topicList]
          .filter(t => t.pctOfTarget < 1)
          .sort((a, b) => a.pctOfTarget - b.pctOfTarget)
          .slice(0, 3);

        const pTotal = progressStats.total_attempted || 0;
        const pTarget = progressStats.target_questions || 5000;
        const goalPct = Math.min(100, Math.round((pTotal / pTarget) * 100));

        return (
          <div style={{ position: 'fixed', inset: 0, background: '#f0f2f8', zIndex: 200, display: 'flex', flexDirection: 'column', overflowY: 'auto', fontFamily: 'Georgia, serif' }}>
            {/* ── Sticky header ── */}
            <div style={{ background: '#fff', borderBottom: '1px solid #e2e6f0', padding: '1rem 2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', position: 'sticky', top: 0, zIndex: 10, boxShadow: '0 1px 8px rgba(0,0,0,0.05)' }}>
              <div>
                <h2 style={{ fontSize: '1.25rem', color: '#172a6e', margin: 0, fontWeight: 700 }}>📊 Exam Readiness — {moduleId}</h2>
                <p style={{ fontSize: '0.72rem', color: '#9ca3af', margin: '2px 0 0' }}>{moduleName} · {stream}</p>
              </div>
              <button onClick={() => setIsReportOpen(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.75rem', color: '#6b7280', lineHeight: 1 }}>×</button>
            </div>

            <div style={{ padding: '1.5rem', maxWidth: '860px', margin: '0 auto', width: '100%', boxSizing: 'border-box' as const, display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

              {/* ══ SECTION A — Readiness Ring ══ */}
              <div style={{ background: '#fff', borderRadius: '20px', border: '1px solid #e2e6f0', overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,0.04)' }}>
                <div style={{ background: 'linear-gradient(135deg, #172a6e 0%, #213b93 60%, #2d4eb8 100%)', padding: '1rem 1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.6)', fontWeight: 700, marginBottom: '2px' }}>Section A</div>
                    <div style={{ fontSize: '1rem', color: '#fff', fontWeight: 700 }}>Exam Readiness Score</div>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)' }}>Weighted by topic level</div>
                </div>

                <div style={{ padding: '2rem', display: 'flex', gap: '2rem', alignItems: 'center', flexWrap: 'wrap' as const, justifyContent: 'center' }}>
                  {/* SVG ring */}
                  <div style={{ position: 'relative', flexShrink: 0 }}>
                    <svg width="156" height="156" viewBox="0 0 156 156">
                      <circle cx="78" cy="78" r={R} fill={ringBg} stroke="#e2e6f0" strokeWidth="12" />
                      <circle cx="78" cy="78" r={R} fill="none" stroke={ringColor} strokeWidth="12" strokeLinecap="round"
                        strokeDasharray={`${dash} ${CIRC - dash}`} strokeDashoffset={CIRC / 4} style={{ transition: 'stroke-dasharray 1.2s ease' }} />
                      <text x="78" y="70" textAnchor="middle" fill={ringColor} fontSize="28" fontWeight="800" fontFamily="Georgia, serif">{readinessScore}%</text>
                      <text x="78" y="90" textAnchor="middle" fill="#9ca3af" fontSize="11" fontFamily="Georgia,serif">ready</text>
                    </svg>
                  </div>

                  {/* right side stats */}
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <div style={{ fontSize: '1.4rem', fontWeight: 800, color: ringColor, marginBottom: '4px' }}>
                      {readinessScore >= 75 ? '✅ Exam Ready' : readinessScore >= 50 ? '🟡 On Track' : '🔴 Needs Work'}
                    </div>
                    <p style={{ fontSize: '0.82rem', color: '#6b7280', marginBottom: '1rem', lineHeight: 1.5 }}>
                      {readinessScore >= 75
                        ? 'You\'ve covered the critical topics well. Keep reviewing Level 3 areas.'
                        : readinessScore >= 50
                        ? 'Good progress. Focus on Level 3 topics to push your score above 75%.'
                        : 'Build your foundation. Start with Level 3 topics — they are exam-critical.'}
                    </p>
                    {/* Goal bar */}
                    <div style={{ fontSize: '0.72rem', color: '#9ca3af', marginBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
                      <span>Overall practice goal</span>
                      <span style={{ fontWeight: 700, color: '#213b93' }}>{pTotal} / {pTarget} Qs</span>
                    </div>
                    <div style={{ height: '8px', background: '#f0f2f8', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ height: '100%', background: 'linear-gradient(90deg, #213b93, #e8b94f)', borderRadius: '4px', width: `${goalPct}%`, transition: 'width 1s ease' }} />
                    </div>
                  </div>
                </div>
              </div>

              {/* ══ SECTION B — Topic Coverage Grid ══ */}
              <div style={{ background: '#fff', borderRadius: '20px', border: '1px solid #e2e6f0', overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,0.04)' }}>
                <div style={{ background: 'linear-gradient(135deg, #172a6e 0%, #213b93 60%, #2d4eb8 100%)', padding: '1rem 1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.6)', fontWeight: 700, marginBottom: '2px' }}>Section B</div>
                    <div style={{ fontSize: '1rem', color: '#fff', fontWeight: 700 }}>Topic Coverage Grid</div>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.5)', display: 'flex', gap: '1rem' }}>
                    <span>🟢 &gt;80%</span><span>🟡 40-80%</span><span>🔴 &lt;40%</span>
                  </div>
                </div>

                <div style={{ padding: '1.25rem' }}>
                  {topicList.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '2rem', color: '#9ca3af', fontSize: '0.85rem' }}>
                      {dashboardLoading ? '⏳ Loading syllabus...' : 'No syllabus data available for this module. Start practising — data will appear here.'}
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '0.75rem' }}>
                      {topicList.map(t => {
                        const pct = Math.round(t.pctOfTarget * 100);
                        const cardBg = pct >= 80 ? '#f0fdf4' : pct >= 40 ? '#fffbeb' : '#fef2f2';
                        const barClr = pct >= 80 ? '#22c55e' : pct >= 40 ? '#f59e0b' : '#ef4444';
                        const borderClr = pct >= 80 ? '#bbf7d0' : pct >= 40 ? '#fde68a' : '#fecaca';
                        const lvlColors = ['', '#6b7280', '#213b93', '#ef4444'];
                        const lvlBgs   = ['', '#f0f2f8', '#eef1fb', '#fef2f2'];
                        return (
                          <div key={t.id} style={{ background: cardBg, border: `1.5px solid ${borderClr}`, borderRadius: '12px', padding: '0.875rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', transition: 'transform 0.15s', cursor: 'default' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem' }}>
                              <div>
                                <div style={{ fontSize: '0.68rem', fontWeight: 800, color: '#213b93', letterSpacing: '0.04em' }}>{t.id}</div>
                                <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#1a1f3a', lineHeight: 1.3, marginTop: '2px' }}>{t.name}</div>
                              </div>
                              <div style={{ flexShrink: 0, background: lvlBgs[t.level] || '#f0f2f8', border: `1.5px solid ${t.level === 3 ? '#fecaca' : t.level === 2 ? '#c7d2f5' : '#e2e6f0'}`, borderRadius: '6px', padding: '2px 7px', fontSize: '0.68rem', fontWeight: 800, color: lvlColors[t.level] || '#6b7280', display: 'flex', alignItems: 'center', gap: '3px' }}>
                                L{t.level}{t.level === 3 ? '⚠' : ''}
                              </div>
                            </div>
                            <div style={{ fontSize: '0.72rem', color: '#6b7280' }}>{t.done} / {t.target} questions · {pct}%</div>
                            <div style={{ height: '5px', background: 'rgba(0,0,0,0.07)', borderRadius: '3px', overflow: 'hidden' }}>
                              <div style={{ height: '100%', background: barClr, borderRadius: '3px', width: `${pct}%`, transition: 'width 0.8s ease' }} />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              {/* ══ SECTION C — Study Suggestions ══ */}
              <div style={{ background: '#fff', borderRadius: '20px', border: '1px solid #e2e6f0', overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,0.04)' }}>
                <div style={{ background: 'linear-gradient(135deg, #172a6e 0%, #213b93 60%, #2d4eb8 100%)', padding: '1rem 1.5rem' }}>
                  <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'rgba(255,255,255,0.6)', fontWeight: 700, marginBottom: '2px' }}>Section C</div>
                  <div style={{ fontSize: '1rem', color: '#fff', fontWeight: 700 }}>📚 Focus Next On</div>
                </div>

                <div style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {weakTopics.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '1.5rem', color: '#22c55e', fontWeight: 700, fontSize: '1rem' }}>
                      🎉 All topics are well covered! Keep it up.
                    </div>
                  ) : (
                    weakTopics.map((t, i) => {
                      const pct = Math.round(t.pctOfTarget * 100);
                      const urgency = t.level === 3 ? { bg: '#fef2f2', border: '#fecaca', badge: '#ef4444', badgeBg: '#fee2e2', label: 'CRITICAL' } :
                                      t.level === 2 ? { bg: '#fffbeb', border: '#fde68a', badge: '#d97706', badgeBg: '#fef3c7', label: 'IMPORTANT' } :
                                                      { bg: '#f0f3fc', border: '#c7d2f5', badge: '#213b93', badgeBg: '#eef1fb', label: 'GOOD TO KNOW' };
                      return (
                        <div key={t.id} style={{ background: urgency.bg, border: `1.5px solid ${urgency.border}`, borderRadius: '12px', padding: '1rem 1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' as const }}>
                          <div style={{ display: 'flex', gap: '0.875rem', alignItems: 'center' }}>
                            <div style={{ fontWeight: 800, fontSize: '1.1rem', color: '#213b93', minWidth: '20px' }}>{i + 1}.</div>
                            <div>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '3px' }}>
                                <span style={{ fontSize: '0.9rem', fontWeight: 700, color: '#1a1f3a' }}>{t.id} — {t.name}</span>
                                <span style={{ fontSize: '0.62rem', fontWeight: 800, background: urgency.badgeBg, color: urgency.badge, border: `1px solid ${urgency.border}`, borderRadius: '4px', padding: '1px 6px', letterSpacing: '0.04em' }}>{urgency.label}</span>
                              </div>
                              <div style={{ fontSize: '0.75rem', color: '#6b7280' }}>
                                Level {t.level} · {t.done}/{t.target} questions · {pct}% complete
                              </div>
                            </div>
                          </div>
                          <button
                            onClick={() => {
                              setIsReportOpen(false);
                              setAiTopicInput(`${t.id} ${t.name}`);
                              setPracticePhase('ai_setup');
                            }}
                            style={{ flexShrink: 0, padding: '0.5rem 1rem', background: '#213b93', color: '#fff', border: 'none', borderRadius: '8px', fontSize: '0.78rem', fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap' as const, transition: 'all 0.15s' }}
                            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = '#172a6e'; }}
                            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = '#213b93'; }}
                          >
                            Start Practice →
                          </button>
                        </div>
                      );
                    })
                  )}
                  <button onClick={() => setShowGoalSetup(true)} style={{ background: 'none', border: '1.5px dashed #c7d2f5', color: '#6b7280', padding: '0.5rem 1.25rem', borderRadius: '8px', cursor: 'pointer', fontSize: '0.78rem', fontWeight: 600, marginTop: '0.25rem', alignSelf: 'center' }}>
                    ⚙️ Change Practice Goal
                  </button>
                </div>
              </div>

            </div>
          </div>
        );
      })()}

      {isPayModalOpen && (
        <div 
          onClick={() => setIsPayModalOpen(false)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(10, 20, 50, 0.85)', backdropFilter: 'blur(10px)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}
        >
          <div 
            onClick={e => e.stopPropagation()}
            style={{ background: '#0a1432', border: '1px solid #e8b94f', borderRadius: '24px', width: '100%', maxWidth: '420px', padding: '2.5rem 2rem', boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)', position: 'relative', textAlign: 'center' }}
          >
            <button 
              onClick={() => setIsPayModalOpen(false)}
              style={{ position: 'absolute', top: '1.25rem', right: '1.25rem', background: 'rgba(255,255,255,0.05)', border: 'none', borderRadius: '50%', width: '32px', height: '32px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', fontSize: '1.25rem' }}
            >
              ×
            </button>

            <div style={{ width: '64px', height: '64px', background: 'rgba(232, 185, 79, 0.1)', borderRadius: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2rem', margin: '0 auto 1.5rem' }}>
              🔓
            </div>

            <h2 style={{ fontSize: '1.75rem', color: '#fff', marginBottom: '0.75rem', fontWeight: 800, fontFamily: 'Georgia, serif' }}>
              Unlock {moduleId}
            </h2>
            <p style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: '1rem', lineHeight: 1.6, marginBottom: '2rem' }}>
              Enter a promo code or pay to unlock full access to this module.
            </p>

            {selectedPlan?.amount === '₹199' && (
              <div style={{
                background: 'rgba(232,185,79,0.08)',
                border: '1px solid rgba(232,185,79,0.2)',
                borderRadius: '12px',
                padding: '0.875rem 1rem',
                marginBottom: '0.875rem',
                textAlign: 'left'
              }}>
                <div style={{
                  fontSize: '0.72rem', fontWeight: 700,
                  color: '#e8b94f', marginBottom: '6px',
                  display: 'flex', alignItems: 'center', gap: '6px'
                }}>
                  🎁 Get 1 Month Free
                </div>
                <p style={{
                  fontSize: '0.68rem', color: 'rgba(255,255,255,0.6)',
                  margin: '0 0 8px', lineHeight: 1.6,
                  fontFamily: 'system-ui, sans-serif'
                }}>
                  Follow Fonus on Instagram, comment on our latest post 
                  and get a promo code delivered to your DM — unlock 
                  29 days of full access completely free.
                </p>
                <a
                  href="https://www.instagram.com/fonuslearning/"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: '6px',
                    fontSize: '0.68rem', fontWeight: 700,
                    color: '#e8b94f', textDecoration: 'none',
                    padding: '5px 10px',
                    background: 'rgba(232,185,79,0.1)',
                    borderRadius: '6px',
                    border: '1px solid rgba(232,185,79,0.2)',
                    transition: 'all 0.15s'
                  }}
                >
                  📸 @fonuslearning →
                </a>
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
              {!showPromoInput ? (
                <button 
                  onClick={() => setShowPromoInput(true)}
                  style={{ width: '100%', padding: '1rem', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '12px', color: '#e8b94f', fontSize: '1rem', fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s' }}
                >
                  I have a promo code
                </button>
              ) : (
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <input 
                    type="text" 
                    placeholder="Enter code..." 
                    value={promoCode}
                    onChange={e => setPromoCode(e.target.value)}
                    style={{ flex: 1, padding: '1rem', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid #e8b94f', borderRadius: '12px', color: '#fff', fontSize: '1rem', outline: 'none' }}
                  />
                  <button 
                    style={{ padding: '0 1.25rem', background: '#e8b94f', color: '#1a1f3a', border: 'none', borderRadius: '12px', fontSize: '0.9rem', fontWeight: 800, cursor: 'pointer' }}
                    onClick={() => alert(`Code ${promoCode} is invalid or expired.`)}
                  >
                    Apply
                  </button>
                </div>
              )}

              <button 
                onClick={() => alert('Payment coming soon')}
                style={{ width: '100%', padding: '1rem', background: '#e8b94f', color: '#1a1f3a', border: 'none', borderRadius: '12px', fontSize: '1rem', fontWeight: 800, cursor: 'pointer', boxShadow: '0 4px 12px rgba(232, 185, 79, 0.3)' }}
              >
                Pay {selectedPlan?.amount}
              </button>
            </div>

            <p style={{ fontSize: '0.75rem', color: 'rgba(255, 255, 255, 0.4)', marginTop: '1.5rem' }}>
              Secure payment via Razorpay · Instant Activation
            </p>
          </div>
        </div>
      )}

    </div>
  );
}

export default function ModulePage() {
  return (
    <Suspense fallback={<div style={{ padding: '2rem', textAlign: 'center', fontFamily: 'Georgia, serif', color: '#213b93' }}>Loading Fonus...</div>}>
      <ModuleContent />
    </Suspense>
  );
}

function PracticeTimer({ timeLeft }: { timeLeft: number }) {
  const mins = Math.floor(timeLeft / 60).toString().padStart(2, '0');
  const secs = (timeLeft % 60).toString().padStart(2, '0');
  return (
    <div style={{ textAlign: 'right' }}>
      <div style={{ fontSize: '1rem', fontWeight: 700, fontFamily: 'monospace', color: timeLeft < 300 ? '#ef4444' : '#213b93' }}>{mins}:{secs}</div>
      <div style={{ fontSize: '0.62rem', color: '#9ca3af' }}>remaining</div>
    </div>
  );
}

function FonusLoader({ message }: { message: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.875rem 1.125rem', background: '#fff', borderRadius: '14px 14px 14px 3px', border: '1px solid #e8ecf5', boxShadow: '0 2px 8px rgba(33,59,147,0.08)', maxWidth: '320px' }}>
      <div style={{ position: 'relative', width: '36px', height: '36px', flexShrink: 0 }}>
        {/* Orbit ring */}
        <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', border: '2px solid #e2e6f0', borderTopColor: '#213b93', animation: 'spin 1.2s linear infinite' }} />
        {/* Aircraft icon */}
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px' }}>✈️</div>
      </div>
      <div>
        <div style={{ fontSize: '0.82rem', color: '#213b93', fontWeight: 600, fontFamily: 'Georgia, serif' }}>{message}</div>
        <div style={{ display: 'flex', gap: '3px', marginTop: '4px' }}>
          {[0, 1, 2].map(i => (
            <div key={i} style={{ width: '5px', height: '5px', borderRadius: '50%', background: '#213b93', animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite` }} />
          ))}
        </div>
      </div>
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes bounce { 0%,60%,100% { transform: scale(0.6); opacity:0.4; } 30% { transform: scale(1); opacity:1; } }
      `}</style>
    </div>
  );
}