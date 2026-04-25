'use client';

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import { Playfair_Display, DM_Sans } from 'next/font/google';

const HeroBackground = dynamic(() => import('./components/HeroBackground'), { ssr: false });
import NavBar from '@/app/components/NavBar';
import { supabase } from '@/lib/supabaseClient';
import { motion, useInView, animate } from 'framer-motion';
import { BrainCircuit, ClipboardList, Zap, Target, ArrowRight, Instagram, Youtube } from 'lucide-react';

const playfair = Playfair_Display({ subsets: ['latin'], weight: ['400', '700'] });
const dmSans = DM_Sans({ subsets: ['latin'], weight: ['400', '500', '600', '700'] });

// --- Existing Stream Logic ---
const STREAMS = [
  { id: 'Cat-A', label: 'Cat-A', title: 'Category A',  desc: 'Line Maintenance Certifying Mechanic',   icon: '🔧' },
  { id: 'B1',    label: 'B1',    title: 'Stream B1',   desc: 'Mechanical — Maintenance Certifying Technician', icon: '✈️' },
  { id: 'B1.1',  label: 'B1.1',  title: 'Turbine Aeroplane',  desc: 'Mechanical — Jet aircraft maintenance',      icon: '✈️' },
  { id: 'B1.2',  label: 'B1.2',  title: 'Piston Aeroplane',   desc: 'Mechanical — Piston aircraft maintenance',   icon: '🛩️' },
  { id: 'B1.3',  label: 'B1.3',  title: 'Turbine Helicopter', desc: 'Mechanical — Helicopter (turbine)',           icon: '🚁' },
  { id: 'B1.4',  label: 'B1.4',  title: 'Piston Helicopter',  desc: 'Mechanical — Helicopter (piston)',            icon: '🚁' },
  { id: 'A1',    label: 'A1',    title: 'Cat-A Turbine Fixed', desc: 'Line Maintenance — Turbine fixed wing',      icon: '🔧' },
  { id: 'A2',    label: 'A2',    title: 'Cat-A Piston Fixed',  desc: 'Line Maintenance — Piston fixed wing',       icon: '🔧' },
  { id: 'A3',    label: 'A3',    title: 'Cat-A Turbine Rotor', desc: 'Line Maintenance — Turbine rotorcraft',      icon: '🔧' },
  { id: 'A4',    label: 'A4',    title: 'Cat-A Piston Rotor',  desc: 'Line Maintenance — Piston rotorcraft',       icon: '🔧' },
  { id: 'B2',    label: 'B2',    title: 'Avionics',             desc: 'Avionics systems & instruments',             icon: '📡' },
  { id: 'B3',    label: 'B3',    title: 'Piston Engine (B3)',   desc: 'Mechanical — Light aircraft piston engines', icon: '⚙️' },
  { id: 'C',     label: 'C',     title: 'Certifying Engineer',  desc: 'Full scope — all systems & aircraft types',  icon: '🎓' },
];

function StatCounter({ to, suffix = "" }: { to: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, margin: "-50px" });

  useEffect(() => {
    if (isInView) {
      animate(0, to, { duration: 2, ease: "easeOut", onUpdate: (v) => setCount(Math.round(v)) });
    }
  }, [isInView, to]);

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <span ref={ref}>{count}{suffix}</span>
      {isInView && (
        <motion.div 
          initial={{ scaleX: 0 }} 
          animate={{ scaleX: 1 }} 
          transition={{ duration: 1, delay: 0.5 }}
          style={{ position: 'absolute', bottom: '-2px', left: '-10%', right: '-10%', height: '2px', background: '#e8b94f', transformOrigin: 'left' }} 
        />
      )}
    </div>
  );
}

const ANIM_CONVOS = [
  [
    { q: "What is the SHELL model?", a: "The SHELL model is a human factors \nframework in aviation maintenance. It stands \nfor Software, Hardware, Environment, and \nLiveware (self and others).", s: "CAR 66 M9 · Human Factors ✓" }
  ],
  [
    { q: "What is washout in rotor blades?", a: "Washout is a gradual decrease in the \nangle of incidence from root to tip of a \nrotor blade, reducing the risk of tip stall \nat high angles of attack.", s: "EASA Part 66 M08 · Page 56 ✓" }
  ],
  [
    { q: "How does an AC motor differ from DC?", a: "AC motors use alternating current and \nrely on electromagnetic induction with no \nbrushes. DC motors use direct current with \nbrushes and commutators for rotation.", s: "CAR 66 M03 · Electrical Fundamentals ✓" }
  ],
  [
    { q: "What causes metal fatigue?", a: "Metal fatigue results from repeated \ncyclic stress below ultimate tensile strength, \nleading to microscopic crack initiation and \npropagation over time.", s: "CAR 66 M06 · Materials & Hardware ✓" }
  ],
  [
    { q: "How do rotor blades generate lift?", a: "Rotor blades generate lift through \naerofoil shape and angle of attack. As blades \nrotate, pressure difference between upper and \nlower surfaces creates upward lift force.", s: "CAR 66 M08 · Aerodynamics ✓" }
  ],
  [
    { q: "What is hydraulic cavitation?", a: "Cavitation occurs when hydraulic fluid \npressure drops below vapour pressure, forming \nbubbles that collapse violently — causing \nnoise, vibration and component damage.", s: "CAR 66 M11A · Hydraulics ✓" }
  ]
];

function LinearHeroMockup() {
  const [convIdx, setConvIdx] = useState(0);
  const [step, setStep] = useState(0);

  useEffect(() => {
    let isCancelled = false;
    const runSequence = async () => {
      setStep(1); // fade user in
      await new Promise(r => setTimeout(r, 950)); 
      if (isCancelled) return;

      setStep(2); // character reveal start
      const aiText = ANIM_CONVOS[convIdx][0].a;
      // We'll wait long enough for the character stagger to finish (roughly 0.02s per char)
      const revealTime = Math.min(aiText.length * 20, 2500); 
      await new Promise(r => setTimeout(r, revealTime));
      if (isCancelled) return;

      setStep(3); // source badge in
      await new Promise(r => setTimeout(r, 400));
      if (isCancelled) return;

      await new Promise(r => setTimeout(r, 4500)); // Hold full convo
      if (isCancelled) return;

      setStep(0); // fade out both
      await new Promise(r => setTimeout(r, 500));
      if (isCancelled) return;

      setConvIdx((i) => (i + 1) % ANIM_CONVOS.length);
    };

    runSequence();
    return () => { isCancelled = true; };
  }, [convIdx]);

  const convo = ANIM_CONVOS[convIdx][0];

  return (
    <motion.div 
      initial={{ y: -8 }}
      animate={{ y: 8 }}
      transition={{ duration: 3, ease: "easeInOut", repeat: Infinity, repeatType: "reverse" }}
      style={{
        width: '100%',
        maxWidth: '480px',
        backgroundColor: '#111827',
        borderRadius: '16px',
        boxShadow: '0 25px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(232,185,79,0.1)',
        border: '1px solid rgba(255,255,255,0.08)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        position: 'relative',
        zIndex: 10
      }}
    >
      {/* Header */}
      <div style={{ height: '44px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 16px', background: '#1a2540', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div style={{ display: 'flex', gap: '6px' }}>
          <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ff5f57' }} />
          <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#febc2e' }} />
          <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#28c840' }} />
        </div>
        <div style={{ color: '#fff', fontSize: '13px', fontWeight: 600 }}>
          Fonus AI
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#10b981', fontSize: '12px', fontWeight: 600 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', boxShadow: '0 0 5px #10b981' }} />
          Live
        </div>
      </div>

      {/* Chat Area */}
      <div style={{ height: '300px', padding: '20px', overflow: 'hidden', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        
        <div style={{ opacity: step === 0 ? 0 : 1, transition: 'opacity 0.5s ease', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {/* User Message */}
          {step >= 1 && (
            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              style={{ alignSelf: 'flex-end', background: '#e8b94f', color: '#0d1b4b', padding: '10px 14px', borderRadius: '12px 12px 0 12px', fontSize: '14px', fontWeight: 600, maxWidth: '85%' }}
            >
              {convo.q}
            </motion.div>
          )}
          
          {/* AI Message */}
          {step >= 2 && (
            <div style={{ alignSelf: 'flex-start', background: '#1e2d4a', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '12px 12px 12px 0', padding: '12px 14px', maxWidth: '90%' }}>
              <div style={{ color: 'rgba(255,255,255,0.85)', fontSize: '13px', lineHeight: 1.6, marginBottom: '8px' }}>
                <motion.div
                  key={convIdx}
                  initial="hidden"
                  animate="visible"
                  variants={{
                    visible: {
                      transition: {
                        staggerChildren: 0.015,
                      }
                    }
                  }}
                >
                  {convo.a.split('').map((char, index) => (
                    <motion.span
                      key={index}
                      variants={{
                        hidden: { opacity: 0 },
                        visible: { opacity: 1 }
                      }}
                    >
                      {char}
                    </motion.span>
                  ))}
                </motion.div>
              </div>
              {step >= 3 && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.3 }}
                  style={{ display: 'inline-block', padding: '3px 8px', background: 'rgba(232,185,79,0.1)', color: '#e8b94f', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}
                >
                  📄 {convo.s}
                </motion.div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Input Bar */}
      <div style={{ height: '48px', background: '#1a2540', borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', padding: '0 16px' }}>
        <div style={{ flex: 1, color: 'rgba(255,255,255,0.25)', fontSize: '14px' }}>
          Ask about CAR 66...
        </div>
        <div style={{ width: 28, height: 28, borderRadius: '50%', background: '#e8b94f', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
           <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#0d1b4b" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
        </div>
      </div>
    </motion.div>
  );
}

const FAQS = [
  { q: "What is Fonus?", a: "Fonus is India's first AI-powered exam preparation platform built specifically for DGCA CAR 66 AME licensing exams. It gives you verified answers from official sources, real past exam questions, unlimited AI mock tests, and a personal progress tracker — all in one place." },
  { q: "Is Fonus free to use?", a: "Yes — you can start using Fonus for free. Free access includes limited questions per week and basic AI answers. To unlock full access including unlimited practice and progress tracking, you can rent any module starting at just ₹49 for a week." },
  { q: "Which AME license streams does Fonus support?", a: "Fonus currently supports B1.1 (Turbine Aeroplane), B1.2 (Piston Aeroplane), B1.3 (Turbine Helicopter), B2 (Avionics), and Category A (Line Maintenance). Each stream shows only the modules relevant to your specific license." },
  { q: "How is Fonus different from ChatGPT or other AI tools?", a: "Generic AI tools like ChatGPT are not trained on DGCA CAR 66 material. They frequently give confident but incorrect answers with no source reference. Fonus answers only from verified official DGCA documents — every answer comes with the exact chapter, module, and page reference." },
  { q: "What is the rental system? Why not a subscription?", a: "Most students prepare one module at a time. A full subscription forces you to pay for everything even when you need only one module. Fonus lets you rent exactly the module you are studying — ₹49 for a week, ₹199 for a month, or ₹499 for 3 months." },
  { q: "What are the 3 practice modes?", a: "Fonus has three practice modes: Random PYQ Session (real past DGCA exam questions), AI Practice Session (AI-generated topic-based questions that never repeat), and Mind Maintenance (twisted, scenario-based advanced questions that simulate real exam pressure)." },
  { q: "What is Mind Maintenance?", a: "Mind Maintenance is Fonus's advanced practice mode. It generates scenario-based, twisted questions designed to simulate the actual difficulty and style of DGCA exams. It is built for students who want mastery — not just a pass mark." },
  { q: "How does the progress tracker work?", a: "Every question you attempt across all three practice modes is counted toward your module progress. You set your own target (recommended 5,000+ questions per module), and the tracker shows your completion, weak topics, strong topics, and exam readiness score." },
  { q: "Is Fonus available on mobile?", a: "Yes — Fonus works on all modern browsers on both desktop and mobile. A dedicated mobile app is on our roadmap." },
  { q: "What stage is Fonus at right now?", a: "Fonus is currently in its testing phase. We are actively gathering student feedback to improve the platform before full launch. Every piece of feedback directly shapes what we build next. Your experience matters." }
];

export default function HomePage() {
  const router = useRouter();
  const [selected, setSelected] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);
  const [feedbackTab, setFeedbackTab] = useState<1 | 2 | 3>(1);
  const [feedbackMsg, setFeedbackMsg] = useState("");
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [feedbackSuccess, setFeedbackSuccess] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const handleFeedbackSubmit = async () => {
    if (!feedbackMsg.trim() || isSubmittingFeedback) return;
    setIsSubmittingFeedback(true);
    
    const typeMap = { 1: 'feedback', 2: 'bug', 3: 'suggestion' };
    
    try {
      const { data } = await supabase.auth.getSession();
      const token = data?.session?.access_token;
      
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          module: 'landing_page',
          message: feedbackMsg,
          type: typeMap[feedbackTab]
        })
      });
      
      setFeedbackSuccess(true);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleStart = async () => {
    if (!selected) return;

    const userId = localStorage.getItem('user_id');
    if (userId) {
      try {
        const { data } = await supabase.auth.getSession();
        const token = data?.session?.access_token;
        await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/profile/stream`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {})
          },
          body: JSON.stringify({ user_id: userId, stream: selected })
        });
      } catch (e) {
        console.error("Failed to save stream", e);
      }
    }

    router.push(`/modules?stream=${selected}`);
  };

  // TASK 5 — Stream card click logic: Now always routes to modules. Login check happens on the modules page.
  const handleStreamSelect = async (streamId: string) => {
    setSelected(streamId);
    const { data: { session } } = await supabase.auth.getSession();
    
    // If logged in, update profile. If not, just proceed to modules (guest mode)
    if (session) {
      try {
        await supabase.from('profiles').update({ stream: streamId }).eq('id', session.user.id);
      } catch (e) {
        console.error('Failed to save stream to profile', e);
      }
    }
    
    router.push(`/modules?stream=${streamId}`);
  };

  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  // TASK 6 — Smart CTA: Always scroll to stream selection. Auth check happens at the module level.
  const handleHeroCTA = () => {
    scrollToSection('stream-selection');
  };

  return (
    <div style={{ backgroundColor: '#fff', color: '#172a6e', fontFamily: 'Inter, sans-serif' }}>
      {/* SECTION 1 — NAVBAR */}
      <NavBar transparentAtTop />

      <main>
        {/* SECTION 2 — HERO */}
        <section 
          className="w-full relative overflow-hidden flex items-center justify-center pt-24 lg:pt-0"
          style={{ minHeight: '100vh', background: '#0d1b4b' }}
        >

          {mounted && <HeroBackground />}



          {/* Container rendered only on client for stability */}
          {mounted && (
            <div className="w-full mx-auto relative z-10 grid grid-cols-1 lg:grid-cols-[55%_45%] items-center px-6 lg:px-[80px] max-w-[1400px]">
              
              {/* Left Content */}
              <div className="flex flex-col mb-16 lg:mb-0 w-full items-start" style={{ paddingBottom: '40px' }}>
                <div 
                  style={{ 
                    fontFamily: 'var(--font-jetbrains), monospace',
                    color: '#e8b94f', 
                    fontSize: '20px', 
                    fontWeight: 600, 
                    letterSpacing: '0.18em', 
                    marginBottom: '24px',
                    textTransform: 'uppercase'
                  }}
                  className="text-left hero-tagline"
                >
                  INDIA'S FIRST AI-POWERED AME EXAM PREP PLATFORM
                </div>
                
                <h1 
                  style={{ 
                    fontSize: 'clamp(48px, 6vw, 72px)', 
                    fontWeight: 800, 
                    lineHeight: 1.05, 
                    margin: 0, 
                    marginBottom: '28px', 
                    color: '#fff', 
                    letterSpacing: '-0.03em' 
                  }}
                  className="text-left hero-h1"
                >
                  <div className="block">
                    <motion.span initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: "easeOut", delay: 0.08 }} style={{ display: 'inline-block' }}>Stop&nbsp;</motion.span>
                    <motion.span initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: "easeOut", delay: 0.16 }} style={{ display: 'inline-block' }}>Guessing.</motion.span>
                  </div>
                  <div className="block">
                    <motion.span initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: "easeOut", delay: 0.24 }} style={{ display: 'inline-block' }}>Start&nbsp;</motion.span>
                    <motion.span initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: "easeOut", delay: 0.32 }} style={{ display: 'inline-block' }}>Preparing.</motion.span>
                  </div>
                  <div className="block" style={{ color: '#e8b94f' }}>
                    <motion.span initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: "easeOut", delay: 0.40 }} style={{ display: 'inline-block' }}>Start&nbsp;</motion.span>
                    <motion.span initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: "easeOut", delay: 0.48 }} style={{ display: 'inline-block' }}>Clearing.</motion.span>
                  </div>
                </h1>
                
                <motion.p 
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.8, delay: 0.6 }}
                  style={{ 
                    fontSize: '20px', 
                    color: 'rgba(255,255,255,0.6)', 
                    lineHeight: 1.85, 
                    margin: 0, 
                    marginBottom: '40px', 
                    maxWidth: '460px',
                    fontWeight: 400,
                    letterSpacing: '0.01em'
                  }}
                  className="text-left hero-paragraph"
                >
                  The only AI platform built for CAR 66 AME exam preparation. Verified answers from official DGCA sources. Real PYQs. Unlimited practice.
                </motion.p>
                
                <div className="flex flex-col sm:flex-row items-start justify-start gap-4" style={{ width: '100%', marginBottom: '20px' }}>
                  <button 
                    onClick={handleHeroCTA}
                    className="btn-gold"
                    style={{ 
                      padding: '14px 28px', color: '#0d1b4b', fontWeight: 700, borderRadius: '8px', 
                      border: 'none', cursor: 'pointer', fontSize: '16px', background: '#e8b94f' 
                    }}
                  >
                    Start Preparing — Free
                  </button>
                  <button 
                    onClick={() => scrollToSection('how-it-works')}
                    className="btn-outline"
                    style={{ 
                      padding: '14px 28px', color: '#fff', fontWeight: 600, borderRadius: '8px', 
                      background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', cursor: 'pointer', fontSize: '16px' 
                    }}
                  >
                    See How It Works ↓
                  </button>
                </div>

                <div className="flex flex-wrap justify-start gap-[20px] mt-2 stats-ticker" style={{ fontSize: '13px', color: 'rgba(255,255,255,0.45)', width: '100%' }}>
                  <span className="flex items-center gap-1">✓ Verified DGCA Sources</span>
                  <span className="flex items-center gap-1">✓ Every Module You Need</span>
                  <span className="flex items-center gap-1">✓ Free to Start</span>
                </div>
              </div>

              {/* Right Mockup */}
              <div className="flex justify-center flex-col items-center w-full">
                <LinearHeroMockup />
              </div>
            </div>
          )}
        </section>

        {/* SECTION 3 — STATS BAR */}
        <section
          style={{
            width: '100%',
            height: '110px',
            background: '#ffffff',
            borderTop: '3px solid #e8b94f',
            borderBottom: '1px solid #e8e8e8',
          }}
        >
          <div
            style={{
              maxWidth: '1200px',
              height: '100%',
              margin: '0 auto',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-evenly',
              gap: '0px',
              padding: '0 16px',
              boxSizing: 'border-box',
            }}
            className="fonus-stats-row"
          >
            <style>{`
              .fonus-stats-row .stats-item:hover .stats-label { color: #e8b94f !important; }
              .fonus-stats-row .stats-item:hover .stats-icon { transform: scale(1.15); }
            `}</style>

            <div className="stats-item" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '8px', cursor: 'default' }}>
              <div className="stats-icon" style={{ fontSize: '28px', color: '#e8b94f', lineHeight: 1, transition: 'transform 0.2s ease' }}>✈</div>
              <div className="stats-label" style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#172a6e', transition: 'color 0.2s ease' }}>AME&apos;s Only</div>
            </div>
            <div style={{ width: '1px', height: '45px', background: '#e0e0e0', alignSelf: 'center' }} />

            <div className="stats-item" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '8px', cursor: 'default' }}>
              <div className="stats-icon" style={{ fontSize: '28px', color: '#e8b94f', lineHeight: 1, transition: 'transform 0.2s ease' }}>📋</div>
              <div className="stats-label" style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#172a6e', transition: 'color 0.2s ease' }}>All CAR 66 Modules</div>
            </div>
            <div style={{ width: '1px', height: '45px', background: '#e0e0e0', alignSelf: 'center' }} />

            <div className="stats-item" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '8px', cursor: 'default' }}>
              <div className="stats-icon" style={{ fontSize: '28px', color: '#e8b94f', lineHeight: 1, transition: 'transform 0.2s ease' }}>🎯</div>
              <div className="stats-label" style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#172a6e', transition: 'color 0.2s ease' }}>Topic Wise DGCA PYQ</div>
            </div>
            <div style={{ width: '1px', height: '45px', background: '#e0e0e0', alignSelf: 'center' }} />

            <div className="stats-item" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '8px', cursor: 'default' }}>
              <div className="stats-icon" style={{ fontSize: '28px', color: '#e8b94f', lineHeight: 1, transition: 'transform 0.2s ease' }}>⚡</div>
              <div className="stats-label" style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#172a6e', transition: 'color 0.2s ease' }}>Unlimited Questions</div>
            </div>
            <div style={{ width: '1px', height: '45px', background: '#e0e0e0', alignSelf: 'center' }} />

            <div className="stats-item" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '8px', cursor: 'default' }}>
              <div className="stats-icon" style={{ fontSize: '28px', color: '#e8b94f', lineHeight: 1, transition: 'transform 0.2s ease' }}>✅</div>
              <div className="stats-label" style={{ fontSize: '13px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#172a6e', transition: 'color 0.2s ease' }}>100% Verified Sources</div>
            </div>
          </div>
        </section>

        {/* OLD CODE PRESERVED (TASK 1) 
        <section style={{ width: '100%', background: '#ffffff', padding: '120px 80px' }}>
          <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', gap: '40px' }}>
            <div style={{ width: '50%', position: 'relative' }}>
              <div style={{ position: 'sticky', top: 120, alignSelf: 'flex-start' }}>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: 0 }}
                  style={{
                    fontFamily: dmSans.style.fontFamily,
                    fontSize: '12px',
                    fontWeight: 800,
                    color: '#e8b94f',
                    letterSpacing: '0.12em',
                    textTransform: 'uppercase',
                    marginBottom: '18px',
                  }}
                >
                  // THE PROBLEM
                </motion.div>

                <motion.h2
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: 0 }}
                  style={{
                    fontFamily: playfair.style.fontFamily,
                    fontSize: '52px',
                    fontWeight: 700,
                    color: '#0d1b4b',
                    lineHeight: 1.15,
                    margin: 0,
                    marginBottom: '24px',
                  }}
                >
                  Every AME Student<br />Faces the Same Wall.
                </motion.h2>

                <motion.p
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: 0 }}
                  style={{
                    fontFamily: dmSans.style.fontFamily,
                    fontSize: '17px',
                    color: '#64748b',
                    lineHeight: 1.8,
                    maxWidth: '420px',
                    margin: 0,
                    marginBottom: '40px',
                  }}
                >
                  The CAR 66 syllabus is vast. The sources are scattered. And most students walk into the DGCA exam having practiced the wrong things — from the wrong places.
                </motion.p>

                <div style={{ width: '60px', height: '3px', background: '#e8b94f', borderRadius: '2px' }} />
              </div>
            </div>

            <div style={{ width: '50%' }}>
              {[
                {
                  n: '01',
                  title: 'The Resource Maze',
                  body: 'CAR 66 spans thousands of pages across multiple manuals. Without a targeted system, students spend more time searching than actually studying.',
                },
                {
                  n: '02',
                  title: 'Unverified Answers',
                  body: 'Generic AI tools like ChatGPT were not built for DGCA. They confidently give wrong answers with no source — and students don’t realise until the exam.',
                },
                {
                  n: '03',
                  title: 'Practising Blind',
                  body: 'Without knowing which topics appear most in DGCA PYQs, students study everything equally — and master nothing specifically.',
                },
              ].map((c, i) => (
                <motion.div
                  key={c.n}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-50px' }}
                  transition={{ duration: 0.7, delay: i * 0.12 }}
                  style={{
                    background: '#f8f9fc',
                    borderRadius: '14px',
                    padding: '32px 28px',
                    borderLeft: '4px solid #e8b94f',
                    position: 'relative',
                    overflow: 'hidden',
                    marginBottom: i < 2 ? '20px' : 0,
                  }}
                >
                  <div style={{ position: 'absolute', right: 20, bottom: -20, fontSize: 120, fontWeight: 900, color: 'rgba(13,27,75,0.04)', pointerEvents: 'none' }}>
                    {c.n}
                  </div>
                  <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 19, fontWeight: 700, color: '#0d1b4b', marginBottom: 10 }}>
                    {c.title}
                  </div>
                  <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 15, color: '#64748b', lineHeight: 1.75 }}>
                    {c.body}
                  </div>
                  <div style={{ marginTop: 14, fontFamily: dmSans.style.fontFamily, fontSize: 12, fontWeight: 800, letterSpacing: '0.12em', color: 'rgba(13,27,75,0.55)', textTransform: 'uppercase' }}>
                    {c.n}
                  </div>
                </motion.div>
              ))}

              <div style={{ marginTop: 12, fontFamily: dmSans.style.fontFamily, fontSize: 15, fontWeight: 600, color: '#e8b94f' }}>
                Fonus was built to solve all three.
              </div>
            </div>
          </div>
        </section> 
        */}

        {/* SECTION 1 — THE PROBLEM (REDESIGNED V2 - PREVIOUS LAYOUT WITH NEW TEXT) */}
        <section style={{ width: '100%', background: '#ffffff', padding: '120px 80px' }}>
          <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', gap: '40px' }} className="problem-grid">
            {/* LEFT STICKY COLUMN */}
            <div style={{ width: '50%', position: 'relative' }}>
              <div style={{ position: 'sticky', top: 120, alignSelf: 'flex-start' }}>
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: 0 }}
                  style={{
                    fontFamily: dmSans.style.fontFamily,
                    fontSize: '12px',
                    fontWeight: 800,
                    color: '#e8b94f',
                    letterSpacing: '0.12em',
                    textTransform: 'uppercase',
                    marginBottom: '18px',
                  }}
                >
                  // THE PROBLEM
                </motion.div>

                <motion.h2
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: 0 }}
                  style={{
                    fontFamily: playfair.style.fontFamily,
                    fontSize: '52px',
                    fontWeight: 700,
                    color: '#0d1b4b',
                    lineHeight: 1.15,
                    margin: 0,
                    marginBottom: '24px',
                  }}
                >
                  Every AME Student<br />Hits the Same Wall.
                </motion.h2>

                <motion.p
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: 0 }}
                  style={{
                    fontFamily: dmSans.style.fontFamily,
                    fontSize: '17px',
                    color: '#64748b',
                    lineHeight: 1.8,
                    maxWidth: '420px',
                    margin: 0,
                    marginBottom: '40px',
                  }}
                >
                  The CAR 66 syllabus is vast. The sources are scattered. And most students walk into the DGCA exam having practiced the wrong things — from the wrong places.
                </motion.p>

                <div style={{ width: '60px', height: '3px', background: '#e8b94f', borderRadius: '2px' }} />
              </div>
            </div>

            {/* RIGHT CARDS */}
            <div style={{ width: '50%' }}>
              {[
                {
                  n: '01',
                  title: 'Lost in 10,000 Pages',
                  body: 'CAR 66 spans textbooks, DGCA regulations, and advisory circulars across 17 modules. Without a targeted system, you spend more time searching than studying.',
                },
                {
                  n: '02',
                  title: 'AI That Lies Confidently',
                  body: 'Generic AI were never trained on DGCA. They give wrong regulation numbers, outdated rules, and zero sources — and you won\'t know until the exam.',
                },
                {
                  n: '03',
                  title: 'Practicing Without a Map',
                  body: 'Without knowing which topics appear most in DGCA PYQs, students study equally across all topics — and get blindsided by patterns they never saw coming.',
                },
              ].map((c, i) => (
                <motion.div
                  key={c.n}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  whileHover={{ y: -5, transition: { duration: 0.2 } }}
                  viewport={{ once: true, margin: '-50px' }}
                  transition={{ duration: 0.7, delay: i * 0.12 }}
                  style={{
                    background: '#f8f9fc',
                    borderRadius: '14px',
                    padding: '32px 28px',
                    borderLeft: '4px solid #e8b94f',
                    position: 'relative',
                    overflow: 'hidden',
                    marginBottom: i < 2 ? '20px' : 0,
                  }}
                >
                  <div style={{ position: 'absolute', right: 20, bottom: -20, fontSize: 120, fontWeight: 900, color: 'rgba(232, 185, 79, 0.08)', pointerEvents: 'none' }}>
                    {c.n}
                  </div>
                  <div style={{ position: 'relative', zIndex: 1 }}>
                    <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 19, fontWeight: 700, color: '#0d1b4b', marginBottom: 10 }}>
                      {c.title}
                    </div>
                    <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 15, color: '#64748b', lineHeight: 1.75 }}>
                      {c.body}
                    </div>
                    <div style={{ marginTop: 14, fontFamily: dmSans.style.fontFamily, fontSize: 12, fontWeight: 800, letterSpacing: '0.12em', color: 'rgba(13,27,75,0.55)', textTransform: 'uppercase' }}>
                      {c.n}
                    </div>
                  </div>
                </motion.div>
              ))}

              <motion.div 
                initial={{ opacity: 0 }} 
                whileInView={{ opacity: 1 }} 
                viewport={{ once: true }} 
                transition={{ duration: 0.7, delay: 0.5 }}
                style={{ marginTop: 24, paddingLeft: 8, fontFamily: dmSans.style.fontFamily, fontSize: 16, fontWeight: 600, color: '#e8b94f', fontStyle: 'italic' }}
              >
                Fonus was built to solve all three — with verified sources, real PYQs, and topic-level tracking.
              </motion.div>
            </div>
          </div>
        </section>

        {/* OLD CODE PRESERVED (TASK 2) 
        <section style={{ width: '100%', background: '#0d1b4b', padding: '120px 80px' }}>
          <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, fontWeight: 800, color: '#e8b94f', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 18 }}
            >
              // WHY FONUS
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: playfair.style.fontFamily, fontSize: 52, fontWeight: 700, color: '#ffffff', margin: 0, marginBottom: 16, lineHeight: 1.15 }}
            >
              ChatGPT Doesn't Know<br />CAR 66. Fonus Does.
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: dmSans.style.fontFamily, fontSize: 17, color: 'rgba(255,255,255,0.55)', margin: 0, marginBottom: 72, lineHeight: 1.8, maxWidth: 820 }}
            >
              Generic AI gives confident wrong answers. Fonus answers only from verified official DGCA sources — with proof.
            </motion.p>

            <div style={{ width: '100%', maxWidth: 900, margin: '0 auto' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1.3fr 1fr 0.9fr', background: 'rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.1)', padding: '16px 24px' }}>
                <div style={{ fontFamily: dmSans.style.fontFamily, color: 'rgba(255,255,255,0.55)', fontSize: 14, fontWeight: 700 }}>Feature</div>
                <div style={{ fontFamily: dmSans.style.fontFamily, color: 'rgba(255,255,255,0.55)', fontSize: 14, fontWeight: 700, textAlign: 'center' }}>
                  Generic AI (ChatGPT/Gemini)
                </div>
                <div style={{ fontFamily: dmSans.style.fontFamily, color: '#e8b94f', fontSize: 14, fontWeight: 700, textAlign: 'center', borderTop: '3px solid #e8b94f' }}>
                  Fonus
                </div>
              </div>

              {[
                { f: 'DGCA CAR 66 Specific Training', g: '✗', f2: '✓' },
                { f: 'Verified Source Citations', g: '✗', f2: '✓ (Chapter & Page)' },
                { f: 'Real DGCA PYQ Database', g: '✗', f2: '✓' },
                { f: 'AME Stream Filtering', g: '✗', f2: '✓ (B1.1 / B1.2 / B1.3 / B2 / A)' },
                { f: 'Module-Specific Answers', g: '✗', f2: '✓' },
                { f: 'Unlimited AI Mock Tests', g: 'Limited / Generic', f2: '✓ DGCA Pattern Only' },
                { f: 'Mind Maintenance Mode', g: '✗', f2: '✓' },
                { f: 'Progress Tracking', g: '✗', f2: '✓' },
                { f: 'Hallucination Risk', g: 'HIGH ⚠', f2: 'ZERO — Verified Only' },
                { f: 'Built for Indian AME Students', g: '✗', f2: '✓ India\'s First' },
              ].map((r, i) => (
                <motion.div
                  key={r.f}
                  initial={{ opacity: 0, x: -20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: i * 0.05 }}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1.3fr 1fr 0.9fr',
                    padding: '18px 24px',
                    borderBottom: '1px solid rgba(255,255,255,0.06)',
                    background: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent',
                    fontFamily: dmSans.style.fontFamily,
                    fontSize: 14,
                    color: 'rgba(255,255,255,0.75)',
                  }}
                >
                  <div>{r.f}</div>
                  <div style={{ textAlign: 'center' }}>
                    {r.g === '✗' ? (
                      <span style={{ color: '#ef4444', fontWeight: 800, fontSize: 20 }}>✗</span>
                    ) : r.g.includes('HIGH') ? (
                      <span style={{ color: '#ef4444', fontWeight: 800 }}>{r.g}</span>
                    ) : (
                      <span style={{ color: 'rgba(255,255,255,0.75)', fontWeight: 700 }}>{r.g}</span>
                    )}
                  </div>
                  <div
                    style={{
                      textAlign: 'center',
                      background: 'rgba(232,185,79,0.04)',
                      borderLeft: '1px solid rgba(232,185,79,0.15)',
                      borderRight: '1px solid rgba(232,185,79,0.15)',
                      padding: '0 10px',
                      color: '#e8b94f',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: 8,
                    }}
                  >
                    {r.f2.includes('(') ? (
                      <>
                        <span style={{ fontWeight: 800 }}>{r.f2.split('(')[0].trim()}</span>
                        <span
                          style={{
                            marginLeft: 8,
                            fontSize: 12,
                            color: '#e8b94f',
                            opacity: 0.95,
                            border: '1px solid rgba(232,185,79,0.35)',
                            padding: '2px 8px',
                            borderRadius: 999,
                            fontWeight: 800,
                          }}
                        >
                          {r.f2.split('(')[1].replace(')', '').trim()}
                        </span>
                      </>
                    ) : (
                      <span style={{ fontWeight: 800 }}>{r.f2}</span>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ textAlign: 'center', marginTop: 40 }}
            >
              <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 16, color: 'rgba(255,255,255,0.45)', fontStyle: 'italic', marginBottom: 0 }}>
                The difference isn't just features.<br />
                It's the difference between a wrong answer and a cleared exam.
              </div>
            </motion.div>
          </div>
        </section>
        */}

        {/* SECTION 2 — WHY FONUS BEATS GENERIC AI (REDESIGNED) */}
        <section style={{ width: '100%', background: '#0d1b4b', padding: '120px 24px' }}>
          <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, fontWeight: 800, color: '#e8b94f', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 18 }}
            >
              // WHY FONUS
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.1 }}
              style={{ fontFamily: playfair.style.fontFamily, fontSize: 'clamp(40px, 5vw, 52px)', fontWeight: 700, color: '#ffffff', margin: 0, marginBottom: 12, lineHeight: 1.15 }}
            >
              Generic AI Doesn't Know CAR 66.<br />
              <span style={{ color: '#e8b94f' }}>Fonus Does.</span>
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.2 }}
              style={{ fontFamily: dmSans.style.fontFamily, fontSize: 17, color: 'rgba(255,255,255,0.6)', margin: 0, marginBottom: 60, lineHeight: 1.8, maxWidth: 820 }}
            >
              Generic AI answers from memory. Fonus answers only from verified DGCA-approved sources /Manual — with the chapter and page to prove it.
            </motion.p>

            <div style={{ width: '100%', maxWidth: 900, margin: '0 auto' }} className="comparison-table-wrapper">
              {/* Table Header */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1.2fr', background: 'rgba(255,255,255,0.04)', borderBottom: '1px solid rgba(255,255,255,0.1)', padding: '16px 24px', borderRadius: '12px 12px 0 0' }}>
                <div style={{ fontFamily: dmSans.style.fontFamily, color: 'rgba(255,255,255,0.55)', fontSize: 14, fontWeight: 700 }}>Feature</div>
                <div style={{ fontFamily: dmSans.style.fontFamily, color: 'rgba(255,255,255,0.4)', fontSize: 14, fontWeight: 700, textAlign: 'center' }}>
                  Generic AI
                </div>
                <div style={{ position: 'relative', fontFamily: dmSans.style.fontFamily, color: '#e8b94f', fontSize: 14, fontWeight: 700, textAlign: 'center' }}>
                  <div style={{ position: 'absolute', top: '-16px', left: 0, right: 0, height: '3px', background: '#e8b94f' }} />
                  Fonus
                </div>
              </div>

              {[
                { f: 'DGCA CAR 66 Specific', g: '✗', f2: '✓' },
                { f: 'Answers with Source & Page', g: '✗', f2: '✓ Chapter + Page' },
                { f: 'Real DGCA PYQ Database', g: '✗', f2: '✓ 2,000+ Questions' },
                { f: 'Module-Specific Answers', g: '✗', f2: '✓ 17 Modules' },
                { f: 'Topic-wise Progress Tracking', g: '✗', f2: '✓ Syllabus-mapped' },
                { f: 'AI Mock Tests (DGCA Pattern)', g: 'Limited', f2: '✓ Unlimited' },
                { f: 'Mind Maintenance Mode', g: '✗', f2: '✓' },
                { f: 'Hallucination Risk', g: 'HIGH ⚠', f2: 'ZERO — Verified Only' },
                { f: 'Built for Indian AME Students', g: '✗', f2: '✓ India\'s First' },
              ].map((r, i) => (
                <motion.div
                  key={r.f}
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-20px' }}
                  transition={{ duration: 0.5, delay: i * 0.08 }} // staggered slide up
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1.4fr 1fr 1.2fr',
                    borderBottom: '1px solid rgba(255,255,255,0.06)',
                    background: i % 2 === 0 ? 'rgba(255,255,255,0.02)' : 'transparent',
                    fontFamily: dmSans.style.fontFamily,
                    fontSize: 15,
                    color: 'rgba(255,255,255,0.85)',
                  }}
                >
                  <div style={{ fontWeight: 500, padding: '20px 24px', display: 'flex', alignItems: 'center' }}>{r.f}</div>
                  
                  {/* Generic AI Column - Muted */}
                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '20px 24px' }}>
                    <div style={{ 
                      color: r.g === '✗' ? 'rgba(239, 68, 68, 0.6)' : 'rgba(255,255,255,0.3)', 
                      opacity: r.g === '✗' ? 1 : 0.8,
                      fontSize: r.g === '✗' ? '20px' : '14px',
                      ...(r.g.includes('HIGH') && { color: '#ef4444', fontWeight: 700, background: 'rgba(239, 68, 68, 0.15)', padding: '6px 12px', borderRadius: '6px', fontSize: '13px' }) 
                    }}>
                      {r.g}
                    </div>
                  </div>
                  
                  {/* Fonus Column - Alive/Gold */}
                  <div style={{ display: 'flex', justifyContent: 'center', height: '100%', alignItems: 'center', padding: '20px 24px', background: 'rgba(232,185,79,0.04)', borderLeft: '1px solid rgba(232,185,79,0.15)', borderRight: '1px solid rgba(232,185,79,0.15)' }}>
                    <div style={{
                      color: r.f2.includes('ZERO') ? '#0d1b4b' : '#e8b94f',
                      background: r.f2.includes('ZERO') ? '#e8b94f' : 'transparent',
                      padding: r.f2.includes('ZERO') ? '6px 16px' : '0',
                      borderRadius: r.f2.includes('ZERO') ? '20px' : '0',
                      fontWeight: r.f2.includes('ZERO') ? 800 : 700,
                      fontSize: r.f2.includes('ZERO') ? '13px' : '15px',
                      whiteSpace: 'nowrap'
                    }}>
                      {r.f2}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.6 }}
              style={{ textAlign: 'center', marginTop: 40 }}
            >
              <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 16, color: 'rgba(255,255,255,0.45)', fontStyle: 'italic', marginBottom: 0 }}>
                The difference isn't just features.<br />
                It's the difference between a wrong answer and a cleared exam.
              </div>
            </motion.div>
          </div>
        </section>

        {/* SECTION 3 — FEATURES */}
        <section style={{ width: '100%', background: '#ffffff', padding: '120px 80px' }}>
          <div style={{ maxWidth: 1200, margin: '0 auto' }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, fontWeight: 800, color: '#e8b94f', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 18 }}
            >
              // WHAT YOU GET
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: playfair.style.fontFamily, fontSize: 52, fontWeight: 700, color: '#0d1b4b', margin: 0, marginBottom: 8, lineHeight: 1.15 }}
            >
              Four Tools. One Goal.
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: dmSans.style.fontFamily, fontSize: 18, color: '#94a3b8', margin: 0, marginBottom: 72, lineHeight: 1.8 }}
            >
              Built for the way DGCA exams actually work.
            </motion.p>

            <div style={{ display: 'grid', gridTemplateColumns: '60% 40%', gap: 20 }} className="tools-grid">
              {/* Card 1 - larger top left */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 0 * 0.12 }}
                style={{ background: '#0d1b4b', borderRadius: 20, padding: '48px 44px', color: '#fff', position: 'relative', overflow: 'hidden' }}
              >
                <div style={{ width: 48, height: 3, background: '#e8b94f', borderRadius: 0, marginBottom: 28 }} />
                <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 24, fontWeight: 700, marginBottom: 14 }}>AI Answer Engine</div>
                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 15, color: 'rgba(255,255,255,0.6)', lineHeight: 1.8 }}>
                  Every answer comes with a source. Not just a chapter — the exact page, the exact module, the exact reference. Ask anything in CAR 66. Get a verified answer in seconds.
                </div>
                <div style={{ marginTop: 32, fontSize: 12, color: '#e8b94f', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 800, fontFamily: dmSans.style.fontFamily }}>
                  Powered by official DGCA documents
                </div>
              </motion.div>

              {/* Card 2 - smaller top right */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 1 * 0.12 }}
                style={{ background: '#f0f4ff', borderRadius: 20, padding: '40px 36px', gridColumn: '2 / 3' }}
              >
                <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 22, fontWeight: 700, color: '#0d1b4b', marginBottom: 14 }}>Real PYQ Practice</div>
                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 15, color: '#64748b', lineHeight: 1.75 }}>
                  Practice from an actual bank of past DGCA exam questions — not AI-generated guesses. Know the real pattern before exam day.
                </div>
                <div style={{ marginTop: 26, display: 'flex', flexDirection: 'column' }}>
                  <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 48, fontWeight: 800, color: '#e8b94f', lineHeight: 1 }}>1000+</div>
                  <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, color: '#94a3b8', fontWeight: 600, marginTop: -2 }}>Real DGCA PYQs</div>
                </div>
              </motion.div>

              {/* Card 3 - smaller bottom left (40% width) */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 2 * 0.12 }}
                style={{ background: '#f0f4ff', borderRadius: 20, padding: '40px 36px', gridColumn: '1 / 2' }}
              >
                <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 22, fontWeight: 700, color: '#0d1b4b', marginBottom: 14 }}>Unlimited Mock Tests</div>
                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 15, color: '#64748b', lineHeight: 1.75 }}>
                  AI generates fresh questions every session. Topic-based or random. Timed or relaxed. Practice is never the same twice.
                </div>
                <div style={{ marginTop: 26, display: 'flex', flexDirection: 'column' }}>
                  <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 48, fontWeight: 800, color: '#e8b94f', lineHeight: 1 }}>∞</div>
                  <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, color: '#94a3b8', fontWeight: 600, marginTop: -2 }}>Questions Available</div>
                </div>
              </motion.div>

              {/* Card 4 - larger bottom right */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 3 * 0.12 }}
                style={{ background: '#0d1b4b', borderRadius: 20, padding: '48px 44px', color: '#fff', gridColumn: '2 / 3' }}
              >
                <div style={{ width: 48, height: 3, background: '#e8b94f', borderRadius: 0, marginBottom: 28 }} />
                <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 24, fontWeight: 700, marginBottom: 14 }}>Mind Maintenance</div>
                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 15, color: 'rgba(255,255,255,0.6)', lineHeight: 1.8 }}>
                  Scenario-based. Twisted. Exam-pressure accurate. These aren't textbook questions — they are the kind that separate a pass from a distinction. Built for students who refuse to just scrape through.
                </div>
                <div style={{ marginTop: 32, fontSize: 12, color: '#e8b94f', letterSpacing: '0.1em', textTransform: 'uppercase', fontWeight: 800, fontFamily: dmSans.style.fontFamily }}>
                  Advanced Mode — Not for beginners
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* SECTION 4 — HOW IT WORKS */}
        <section id="how-it-works" style={{ width: '100%', background: '#f8f9fc', padding: '120px 80px' }}>
          <div style={{ maxWidth: 1000, margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: 80 }}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 0 }}
                style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, fontWeight: 800, color: '#e8b94f', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 18 }}
              >
                // THE PROCESS
              </motion.div>

              <motion.h2
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 0 }}
                style={{ fontFamily: playfair.style.fontFamily, fontSize: 52, fontWeight: 700, color: '#0d1b4b', margin: 0, lineHeight: 1.15 }}
              >
                Three Steps to<br />CAR 66 Clearance.
              </motion.h2>
            </div>

            <div style={{ position: 'relative' }}>
              <div style={{ position: 'absolute', left: '5%', right: '5%', top: 32, borderTop: '2px dashed #e8b94f', zIndex: 0 }} />

              <div style={{ display: 'flex', gap: 0, justifyContent: 'space-between' }} className="steps-grid">
                {[
                  {
                    num: 1,
                    title: 'Choose Your Stream',
                    desc: 'Select your AME license stream. Fonus filters your exact modules — B1.1, B1.2, B1.3, B2, or Category A. No irrelevant content.',
                  },
                  {
                    num: 2,
                    title: 'Rent One Module',
                    desc: 'Pay only for what you are studying. ₹49 for a week. ₹199 for a month. No full-course commitments. No wasted money.',
                  },
                  {
                    num: 3,
                    title: 'Study Until You Are Ready',
                    desc: 'AI answers, real PYQs, unlimited mock tests, and a progress dashboard that tells you exactly when you are exam-ready.',
                  },
                ].map((s, i) => (
                  <div key={s.num} style={{ width: '33%', textAlign: 'center', position: 'relative', zIndex: 1 }}>
                    <motion.div
                      initial={{ opacity: 0, scale: 0.8 }}
                      whileInView={{ opacity: 1, scale: 1 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.7, delay: 0 }}
                      style={{
                        width: 64,
                        height: 64,
                        background: '#e8b94f',
                        color: '#0d1b4b',
                        fontSize: 24,
                        fontWeight: 800,
                        borderRadius: '50%',
                        margin: '0 auto 28px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: '0 0 0 10px rgba(232,185,79,0.1), 0 0 0 20px rgba(232,185,79,0.05)',
                      }}
                    >
                      {s.num}
                    </motion.div>

                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.7, delay: 0 }}
                      style={{ fontFamily: dmSans.style.fontFamily }}
                    >
                      <div style={{ fontSize: 20, fontWeight: 700, color: '#0d1b4b', marginBottom: 12 }}>{s.title}</div>
                      <div style={{ fontSize: 15, color: '#64748b', lineHeight: 1.8 }}>
                        {s.desc}
                      </div>
                    </motion.div>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', justifyContent: 'center', marginTop: 64 }}>
                <motion.button
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: 0 }}
                  onClick={handleHeroCTA}
                  style={{
                    padding: '18px 40px',
                    background: '#e8b94f',
                    color: '#0d1b4b',
                    border: 'none',
                    borderRadius: 10,
                    fontWeight: 700,
                    fontSize: 16,
                    cursor: 'pointer',
                    fontFamily: dmSans.style.fontFamily,
                  }}
                  whileHover={{ scale: 1.02 }}
                >
                  Start Preparing — It&apos;s Free →
                </motion.button>
              </div>

              <div style={{ textAlign: 'center', marginTop: 12, fontFamily: dmSans.style.fontFamily, fontSize: 13, color: '#94a3b8' }}>
                No credit card required. Free access to start.
              </div>
            </div>
          </div>
        </section>

        
        {/* OLD CODE PRESERVED (TASK 3 V2) */}
        {/* 
        <section style={{ width: '100%', background: '#0d1b4b', padding: '120px 24px' }}>
          <div style={{ maxWidth: 800, margin: '0 auto', textAlign: 'center' }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{
                fontFamily: dmSans.style.fontFamily,
                fontSize: 12,
                fontWeight: 800,
                color: '#e8b94f',
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                marginBottom: 18,
              }}
            >
              // GET FULL ACCESS
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.1 }}
              style={{
                fontFamily: playfair.style.fontFamily,
                fontSize: 'clamp(40px, 5vw, 52px)',
                fontWeight: 700,
                color: '#ffffff',
                textAlign: 'center',
                margin: 0,
                marginBottom: 60,
                lineHeight: 1.15,
              }}
            >
              Your Career is Worth<br />More Than a <span style={{ fontStyle: 'italic', color: '#e8b94f' }}>Guess</span>.
            </motion.h2>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0.2 }}
              style={{
                background: 'linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01))',
                borderRadius: 24,
                padding: '56px 48px',
                textAlign: 'center',
                position: 'relative',
                border: '1px solid rgba(232, 185, 79, 0.3)',
                boxShadow: '0 32px 80px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)',
                maxWidth: 600,
                margin: '0 auto',
              }}
            >
              <div style={{ display: 'inline-block', background: 'rgba(232, 185, 79, 0.1)', color: '#e8b94f', fontSize: 13, fontWeight: 800, letterSpacing: '0.15em', padding: '8px 20px', borderRadius: 20, marginBottom: 24, textTransform: 'uppercase' }}>
                Fonus Premium
              </div>

              <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 72, fontWeight: 700, color: '#ffffff', lineHeight: 1, display: 'flex', justifyContent: 'center', alignItems: 'baseline', gap: '8px' }}>
                ₹499 <span style={{ fontFamily: dmSans.style.fontFamily, fontSize: 18, color: 'rgba(255,255,255,0.5)', fontWeight: 500 }}>/ month</span>
              </div>
              
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', margin: '40px 0' }} />

              <div style={{ display: 'flex', flexDirection: 'column', gap: 16, alignItems: 'flex-start', textAlign: 'left', fontFamily: dmSans.style.fontFamily, fontSize: 16, margin: '0 auto', maxWidth: 'fit-content' }}>
                {[
                  'Complete CAR 66 verified access',
                  '2,000+ Real DGCA PYQs',
                  'Chapter & Page citations for every answer',
                  'Unlimited AI Mock Tests (Timer built-in)',
                  'Mind Maintenance Mode'
                ].map((t) => (
                  <div key={t} style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <span style={{ color: '#e8b94f', fontWeight: 900, fontSize: 20 }}>✓</span>
                    <span style={{ color: '#ffffff', fontWeight: 500 }}>{t}</span>
                  </div>
                ))}
              </div>

              <button
                onClick={() => selected ? handleStart() : scrollToSection('stream-selection')}
                style={{
                  width: '100%',
                  marginTop: 48,
                  border: 'none',
                  background: '#e8b94f',
                  color: '#0d1b4b',
                  padding: '20px 32px',
                  borderRadius: 12,
                  fontWeight: 800,
                  fontSize: 18,
                  fontFamily: dmSans.style.fontFamily,
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  boxShadow: '0 8px 32px rgba(232, 185, 79, 0.2)',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 12px 40px rgba(232, 185, 79, 0.3)';
                  e.currentTarget.style.background = '#f2ce76';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 8px 32px rgba(232, 185, 79, 0.2)';
                  e.currentTarget.style.background = '#e8b94f';
                }}
              >
                Start Preparing for Free
              </button>

              <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, color: 'rgba(255,255,255,0.4)', marginTop: 16, fontWeight: 500 }}>
                7-day free trial. Cancel anytime.
              </div>
            </motion.div>
          </div>
        </section>
        */}

        {/* SECTION 5 — PRICING (RESTORED GRID) */}
        <section style={{ width: '100%', background: '#0d1b4b', padding: '120px 80px' }}>
          <div style={{ maxWidth: '1100px', margin: '0 auto', textAlign: 'center' }}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{
                fontFamily: dmSans.style.fontFamily,
                fontSize: 12,
                fontWeight: 800,
                color: '#e8b94f',
                letterSpacing: '0.12em',
                textTransform: 'uppercase',
                marginBottom: 18,
              }}
            >
              // GET FULL ACCESS
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{
                fontFamily: playfair.style.fontFamily,
                fontSize: 52,
                fontWeight: 700,
                color: '#ffffff',
                textAlign: 'center',
                margin: 0,
                marginBottom: 60,
                lineHeight: 1.15,
              }}
            >
              Your Career is Worth<br />More Than a <span style={{ fontStyle: 'italic', color: '#e8b94f' }}>Guess</span>.
            </motion.h2>

            <style>{`
              .pricing-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 24px; max-width: 960px; margin: 0 auto; }
              @media (max-width: 980px) { .pricing-grid { grid-template-columns: 1fr; } }
              .pricing-cta-ghost:hover { border-color: #ffffff !important; background: rgba(255,255,255,0.05) !important; }
              .pricing-card-popular { transform: scale(1.05); box-shadow: 0 32px 80px rgba(232,185,79,0.25); }
              .pricing-cta-popular:hover { background: #172a6e !important; }
            `}</style>

            <div className="pricing-grid">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 0 * 0.12 }}
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 20,
                  padding: '48px 40px',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, fontWeight: 700, letterSpacing: '0.2em', color: 'rgba(255,255,255,0.4)', marginBottom: 24, textTransform: 'uppercase' }}>
                  1 WEEK
                </div>
                <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 64, fontWeight: 800, color: '#ffffff', lineHeight: 1 }}>₹49</div>
                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, color: 'rgba(255,255,255,0.35)', marginBottom: 32 }}>per module</div>
                <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', margin: '32px 0' }} />

                <div style={{ textAlign: 'left', fontFamily: dmSans.style.fontFamily, fontSize: 14 }}>
                  {[
                    'Full AI answer access',
                    'Real PYQ practice',
                    'AI mock test sessions',
                    'Progress tracking',
                    '100 questions/week limit',
                  ].map((t) => (
                    <div key={t} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 10 }}>
                      <span style={{ color: '#e8b94f', fontWeight: 900, lineHeight: '18px' }}>✓</span>
                      <span style={{ color: '#ffffff' }}>{t}</span>
                    </div>
                  ))}
                </div>

                <button
                  className="pricing-cta-ghost"
                  onClick={() => selected ? handleStart() : scrollToSection('stream-selection')}
                  style={{
                    width: '100%',
                    marginTop: 28,
                    border: '1px solid rgba(255,255,255,0.2)',
                    background: 'transparent',
                    color: '#ffffff',
                    padding: '14px 32px',
                    borderRadius: 8,
                    fontWeight: 600,
                    fontFamily: dmSans.style.fontFamily,
                    cursor: 'pointer',
                  }}
                >
                  Try for ₹49
                </button>

                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, color: 'rgba(255,255,255,0.3)', marginTop: 20, fontWeight: 500 }}>
                  Best for: First time users
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 1 * 0.12 }}
                className="pricing-card-popular"
                style={{
                  background: '#e8b94f',
                  borderRadius: 20,
                  padding: '48px 40px',
                  textAlign: 'center',
                  position: 'relative',
                }}
              >
                <div style={{ display: 'inline-block', background: '#0d1b4b', color: '#e8b94f', fontSize: 11, fontWeight: 700, letterSpacing: '0.15em', padding: '6px 16px', borderRadius: 20, marginBottom: 20, textTransform: 'uppercase' }}>
                  MOST POPULAR
                </div>

                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, fontWeight: 700, letterSpacing: '0.2em', color: 'rgba(13,27,75,0.6)', marginBottom: 10, textTransform: 'uppercase' }}>
                  1 MONTH
                </div>
                <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 64, fontWeight: 800, color: '#0d1b4b', lineHeight: 1 }}>₹199</div>
                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, color: 'rgba(13,27,75,0.5)', marginBottom: 32, marginTop: 12 }}>per module</div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 12, alignItems: 'flex-start', textAlign: 'left', fontFamily: dmSans.style.fontFamily, fontSize: 14 }}>
                  {[
                    'Full AI answer access',
                    'Unlimited PYQ practice',
                    'Unlimited mock tests',
                    'Progress dashboard',
                    'Weak topic identification',
                    'No question limits',
                  ].map((t) => (
                    <div key={t} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                      <span style={{ color: '#0d1b4b', fontWeight: 900, lineHeight: '18px' }}>✓</span>
                      <span style={{ color: '#0d1b4b', fontWeight: 600 }}>{t}</span>
                    </div>
                  ))}
                </div>

                <button
                  className="pricing-cta-popular"
                  onClick={() => selected ? handleStart() : scrollToSection('stream-selection')}
                  style={{
                    width: '100%',
                    marginTop: 28,
                    border: 'none',
                    background: '#0d1b4b',
                    color: '#e8b94f',
                    padding: '16px 32px',
                    borderRadius: 8,
                    fontWeight: 700,
                    fontFamily: dmSans.style.fontFamily,
                    cursor: 'pointer',
                  }}
                >
                  Start for ₹199
                </button>

                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, color: 'rgba(13,27,75,0.5)', marginTop: 20, fontWeight: 600 }}>
                  Best for: Regular exam prep
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 2 * 0.12 }}
                style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  borderRadius: 20,
                  padding: '48px 40px',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, fontWeight: 700, letterSpacing: '0.2em', color: 'rgba(255,255,255,0.4)', marginBottom: 24, textTransform: 'uppercase' }}>
                  3 MONTHS
                </div>
                <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 64, fontWeight: 800, color: '#ffffff', lineHeight: 1 }}>₹499</div>
                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, color: 'rgba(255,255,255,0.35)', marginBottom: 32 }}>per module</div>
                <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', margin: '32px 0' }} />

                <div style={{ textAlign: 'left', fontFamily: dmSans.style.fontFamily, fontSize: 14 }}>
                  {[
                    'Everything in 1 Month',
                    '3 months full access',
                    'Exam readiness score',
                    'Complete progress history',
                    'Priority support',
                  ].map((t) => (
                    <div key={t} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 10 }}>
                      <span style={{ color: '#e8b94f', fontWeight: 900, lineHeight: '18px' }}>✓</span>
                      <span style={{ color: '#ffffff' }}>{t}</span>
                    </div>
                  ))}
                </div>

                <button
                  className="pricing-cta-ghost"
                  onClick={() => selected ? handleStart() : scrollToSection('stream-selection')}
                  style={{
                    width: '100%',
                    marginTop: 28,
                    border: '1px solid rgba(255,255,255,0.2)',
                    background: 'transparent',
                    color: '#ffffff',
                    padding: '14px 32px',
                    borderRadius: 8,
                    fontWeight: 600,
                    fontFamily: dmSans.style.fontFamily,
                    cursor: 'pointer',
                  }}
                >
                  Get 3 Months
                </button>

                <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, color: 'rgba(255,255,255,0.3)', marginTop: 20, fontWeight: 500 }}>
                  Best for: Thorough preparation
                </div>
              </motion.div>
            </div>

            <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 14, color: 'rgba(255,255,255,0.3)', textAlign: 'center', marginTop: 40, lineHeight: 1.8 }}>
              Per module · No hidden fees · No full course forced on you
            </div>
          </div>
        </section>

{/* OLD CODE PRESERVED (TASK 4) —— remove only when user says "delete the preserved changes"
        <section id="stream-selection" style={{ width: '100%', background: '#ffffff', padding: '120px 80px' }}>
          <div style={{ maxWidth: 900, margin: '0 auto', textAlign: 'center' }}>
            <style>{`
              .stream-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; max-width: 900px; margin: 0 auto; }
              @media (max-width: 900px) { .stream-grid { grid-template-columns: 1fr; } }
              .stream-card {
                background: #f8f9fc;
                border-radius: 16px;
                padding: 32px 28px;
                border: 2px solid transparent;
                cursor: pointer;
                transition: all 0.25s ease;
                display: flex;
                align-items: center;
                gap: 20px;
                text-align: left;
              }
              .stream-card:hover {
                border-color: #e8b94f;
                background: #ffffff;
                box-shadow: 0 8px 32px rgba(232,185,79,0.12);
              }
              .stream-card:hover .stream-arrow { opacity: 1; transform: translateX(4px); }
              .stream-arrow { margin-left: auto; color: #e8b94f; font-size: 20px; opacity: 0; transition: opacity 0.2s, transform 0.2s; transform: translateX(0px); }
              .stream-card.selected {
                border-color: #e8b94f;
                background: linear-gradient(135deg, rgba(232,185,79,0.06), rgba(232,185,79,0.02));
              }
              .stream-card.selected .stream-arrow { opacity: 1; transform: translateX(4px); }
              .stream-cta:hover { transform: scale(1.02); background: #d4a843 !important; }
            `}</style>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: 'monospace', fontSize: 12, fontWeight: 800, color: '#e8b94f', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 18 }}
            >
              // GET STARTED
            </motion.div>

            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: playfair.style.fontFamily, fontSize: 52, fontWeight: 700, color: '#0d1b4b', margin: 0, marginBottom: 16, lineHeight: 1.15 }}
            >
              Your License.<br />
              Your Modules.<br />
              Your Exam.
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: dmSans.style.fontFamily, fontSize: 17, color: '#94a3b8', margin: 0, marginBottom: 64, lineHeight: 1.8 }}
            >
              Select your AME license category below.
              Fonus shows only the modules relevant to you —
              nothing extra, nothing missing.
            </motion.p>

            <div className="stream-grid">
              {STREAMS.map((stream, i) => (
                <motion.button
                  key={stream.id}
                  type="button"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.7, delay: i * 0.12 }}
                  onClick={() => {
                    setSelected(stream.id);
                    setTimeout(() => {
                      document.getElementById('stream-cta-btn')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }, 100);
                  }}
                  className={`stream-card ${selected === stream.id ? 'selected' : ''}`}
                  style={undefined}
                >
                  <div style={{ width: 48, height: 48, borderRadius: 12, background: 'rgba(13,27,75,0.06)', padding: 12, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span style={{ fontSize: 26, color: '#172a6e' }}>{stream.icon}</span>
                  </div>

                  <div>
                    <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, fontWeight: 700, letterSpacing: '0.12em', color: '#e8b94f', textTransform: 'uppercase', marginBottom: 4 }}>
                      {stream.id}
                    </div>
                    <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 18, fontWeight: 700, color: '#0d1b4b', marginBottom: 6 }}>
                      {stream.title}
                    </div>
                    <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 14, color: '#94a3b8', lineHeight: 1.6 }}>
                      {stream.desc}
                    </div>
                  </div>

                  <div className="stream-arrow">→</div>
                </motion.button>
              ))}
            </div>

            <motion.button
              id="stream-cta-btn"
              type="button"
              onClick={handleStart}
              disabled={!selected}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              className="stream-cta"
              style={{
                marginTop: 48,
                background: selected ? '#e8b94f' : '#e2e8f0',
                color: selected ? '#0d1b4b' : '#94a3b8',
                fontWeight: 700,
                padding: '18px 48px',
                borderRadius: 10,
                fontSize: 16,
                display: 'block',
                marginLeft: 'auto',
                marginRight: 'auto',
                border: 'none',
                cursor: selected ? 'pointer' : 'not-allowed',
                width: 'fit-content',
                fontFamily: dmSans.style.fontFamily,
                transition: 'background 0.2s ease',
              }}
              whileHover={selected ? { scale: 1.02 } : undefined}
            >
              View My Modules →
            </motion.button>
          </div>
        </section>
        */}

        {/* SECTION 6 — STREAM SELECTOR (TASK 4 REDESIGN) */}
        <section id="stream-selection" style={{ width: '100%', background: '#ffffff', padding: '100px 60px' }}>
          <style>{`
            .scat-label { font-size: 11px; font-weight: 800; letter-spacing: 0.15em; color: #e8b94f; text-transform: uppercase; margin-bottom: 14px; }
            .scat-row { display: grid; gap: 16px; margin-bottom: 10px; }
            .scat-row-4 { grid-template-columns: repeat(4, 1fr); }
            .scat-row-3 { grid-template-columns: repeat(3, 1fr); }
            @media (max-width: 1024px) { .scat-row-4 { grid-template-columns: repeat(2, 1fr); } }
            @media (max-width: 640px) { .scat-row-4, .scat-row-3 { grid-template-columns: 1fr; } }
            .scat-card {
              background: #f8f9fc;
              border: 2px solid transparent;
              border-radius: 16px;
              padding: 24px 20px;
              cursor: pointer;
              transition: all 0.22s ease;
              text-align: left;
              display: flex;
              flex-direction: column;
              gap: 6px;
              position: relative;
            }
            .scat-card:hover {
              border-color: #e8b94f;
              background: #ffffff;
              box-shadow: 0 8px 32px rgba(232,185,79,0.14);
              transform: scale(1.02);
            }
            .scat-card.scat-selected {
              border-color: #e8b94f;
              background: linear-gradient(135deg, rgba(232,185,79,0.07), rgba(232,185,79,0.02));
            }
            .scat-card.scat-selected::after {
              content: '✓';
              position: absolute;
              top: 12px;
              right: 14px;
              color: #e8b94f;
              font-size: 16px;
              font-weight: 900;
            }
          `}</style>

          <div style={{ maxWidth: 1080, margin: '0 auto' }} className="stream-grid">
            {/* Section header */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
              style={{ textAlign: 'center', marginBottom: 64 }}
            >
              <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, fontWeight: 800, color: '#e8b94f', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 16 }}>
                // GET STARTED
              </div>
              <h2 style={{ fontFamily: playfair.style.fontFamily, fontSize: 'clamp(38px, 5vw, 52px)', fontWeight: 700, color: '#0d1b4b', margin: 0, marginBottom: 16, lineHeight: 1.15 }}>
                Your License.<br />
                Your Modules.<br />
                Your Exam.
              </h2>
              <p style={{ fontFamily: dmSans.style.fontFamily, fontSize: 17, color: '#94a3b8', margin: '0 auto', maxWidth: 520, lineHeight: 1.8 }}>
                Select your AME license category below. Fonus shows only the modules relevant to you — nothing extra, nothing missing.
              </p>
            </motion.div>

            {/* ROW 1 — B1 Mechanical */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.05 }}
              style={{ marginBottom: 36 }}
            >
              <div className="scat-label">B1 Mechanical</div>
              <div className="scat-row scat-row-4">
                {[
                  { id: 'B1.1', title: 'Turbine Aeroplane',  desc: 'Mechanical — Jet aircraft maintenance',   icon: '✈️' },
                  { id: 'B1.2', title: 'Piston Aeroplane',   desc: 'Mechanical — Piston aircraft maintenance', icon: '🛩️' },
                  { id: 'B1.3', title: 'Turbine Helicopter', desc: 'Mechanical — Helicopter (turbine)',         icon: '🚁' },
                  { id: 'B1.4', title: 'Piston Helicopter',  desc: 'Mechanical — Helicopter (piston)',          icon: '🚁' },
                ].map((s, i) => (
                  <motion.button
                    key={s.id}
                    type="button"
                    initial={{ opacity: 0, y: 16 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: 0.1 + i * 0.08 }}
                    onClick={() => handleStreamSelect(s.id)}
                    className={`scat-card ${selected === s.id ? 'scat-selected' : ''}`}
                  >
                    <span style={{ fontSize: 22, marginBottom: 4 }}>{s.icon}</span>
                    <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 11, fontWeight: 700, letterSpacing: '0.14em', color: '#e8b94f', textTransform: 'uppercase' }}>{s.id}</div>
                    <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 16, fontWeight: 700, color: '#0d1b4b', lineHeight: 1.3 }}>{s.title}</div>
                    <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, color: '#94a3b8', lineHeight: 1.5 }}>{s.desc}</div>
                  </motion.button>
                ))}
              </div>
            </motion.div>

            {/* ROW 2 — Category A */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.1 }}
              style={{ marginBottom: 36 }}
            >
              <div className="scat-label">Category A — Line Maintenance</div>
              <div className="scat-row scat-row-4">
                {[
                  { id: 'A1', title: 'Turbine Fixed Wing',  desc: 'Line Maintenance — Turbine fixed wing',    icon: '🔧' },
                  { id: 'A2', title: 'Piston Fixed Wing',   desc: 'Line Maintenance — Piston fixed wing',     icon: '🔧' },
                  { id: 'A3', title: 'Turbine Rotorcraft',  desc: 'Line Maintenance — Turbine rotorcraft',    icon: '🔧' },
                  { id: 'A4', title: 'Piston Rotorcraft',   desc: 'Line Maintenance — Piston rotorcraft',     icon: '🔧' },
                ].map((s, i) => (
                  <motion.button
                    key={s.id}
                    type="button"
                    initial={{ opacity: 0, y: 16 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: 0.15 + i * 0.08 }}
                    onClick={() => handleStreamSelect(s.id)}
                    className={`scat-card ${selected === s.id ? 'scat-selected' : ''}`}
                  >
                    <span style={{ fontSize: 22, marginBottom: 4 }}>{s.icon}</span>
                    <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 11, fontWeight: 700, letterSpacing: '0.14em', color: '#e8b94f', textTransform: 'uppercase' }}>{s.id}</div>
                    <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 16, fontWeight: 700, color: '#0d1b4b', lineHeight: 1.3 }}>{s.title}</div>
                    <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, color: '#94a3b8', lineHeight: 1.5 }}>{s.desc}</div>
                  </motion.button>
                ))}
              </div>
            </motion.div>

            {/* ROW 3 — Avionics & Others */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.15 }}
              style={{ marginBottom: 56 }}
            >
              <div className="scat-label">Avionics &amp; Others</div>
              <div className="scat-row scat-row-3">
                {[
                  { id: 'B2', title: 'Avionics',            desc: 'Avionics systems & instruments',             icon: '📡' },
                  { id: 'B3', title: 'Piston Engine (B3)',  desc: 'Mechanical — Light aircraft piston engines',  icon: '⚙️' },
                  { id: 'C',  title: 'Certifying Engineer', desc: 'Full scope — all systems & aircraft types',   icon: '🎓' },
                ].map((s, i) => (
                  <motion.button
                    key={s.id}
                    type="button"
                    initial={{ opacity: 0, y: 16 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: 0.2 + i * 0.08 }}
                    onClick={() => handleStreamSelect(s.id)}
                    className={`scat-card ${selected === s.id ? 'scat-selected' : ''}`}
                  >
                    <span style={{ fontSize: 22, marginBottom: 4 }}>{s.icon}</span>
                    <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 11, fontWeight: 700, letterSpacing: '0.14em', color: '#e8b94f', textTransform: 'uppercase' }}>{s.id}</div>
                    <div style={{ fontFamily: playfair.style.fontFamily, fontSize: 16, fontWeight: 700, color: '#0d1b4b', lineHeight: 1.3 }}>{s.title}</div>
                    <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, color: '#94a3b8', lineHeight: 1.5 }}>{s.desc}</div>
                  </motion.button>
                ))}
              </div>
            </motion.div>

            {/* Helper text */}
            <motion.p
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.3 }}
              style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, color: '#94a3b8', textAlign: 'center' }}
            >
              Click your stream to continue. Already have an account? You&apos;ll go straight to your modules.
            </motion.p>
          </div>
        </section>

        {/* SECTION B — TESTING PHASE HONEST BOX */}
        <section style={{ width: '100%', background: '#ffffff', padding: '80px', display: 'flex', justifyContent: 'center' }}>
          <div style={{ maxWidth: '760px', width: '100%', textAlign: 'center' }}>
            <div style={{
              background: 'rgba(232,185,79,0.1)',
              border: '1px solid rgba(232,185,79,0.3)',
              borderRadius: 30,
              padding: '8px 20px',
              display: 'inline-block',
              marginBottom: 32,
              fontSize: 13,
              fontWeight: 600,
              color: '#e8b94f',
              letterSpacing: '0.05em'
            }}>
              🧪 Currently in Testing Phase
            </div>

            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: playfair.style.fontFamily, fontSize: 42, fontWeight: 700, color: '#0d1b4b', margin: 0, marginBottom: 16 }}
            >
              We Are Building This<br />For You. Tell Us How.
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: dmSans.style.fontFamily, fontSize: 16, color: '#64748b', lineHeight: 1.8, marginBottom: 48 }}
            >
              Fonus is in its early testing phase.<br />
              We are not a finished product — we are a team obsessed with getting this right.<br />
              Every student who tests Fonus and shares feedback is directly shaping what we build next.<br />
              Your single message matters more than you think.
            </motion.p>

            <div style={{ background: '#f8f9fc', borderRadius: 20, padding: 48, border: '1px solid #e8e8e8', textAlign: 'center' }}>
              {feedbackSuccess ? (
                <div>
                  <div style={{ color: '#e8b94f', fontSize: 48, marginBottom: 12 }}>✅</div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: '#0d1b4b', fontFamily: dmSans.style.fontFamily }}>
                    Thank you. We read every message.
                  </div>
                </div>
              ) : (
                <>
                  <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginBottom: 20, flexWrap: 'wrap' }}>
                    {[
                      { id: 1 as const, label: '💬 Share Feedback' },
                      { id: 2 as const, label: '🐛 Report a Bug' },
                      { id: 3 as const, label: '💡 Suggest a Feature' }
                    ].map(tab => (
                      <button
                        key={tab.id}
                        onClick={() => { setFeedbackTab(tab.id); setFeedbackMsg(''); }}
                        style={{
                          background: feedbackTab === tab.id ? '#e8b94f' : 'transparent',
                          color: feedbackTab === tab.id ? '#0d1b4b' : '#94a3b8',
                          fontWeight: feedbackTab === tab.id ? 700 : 500,
                          padding: '10px 20px',
                          borderRadius: 8,
                          border: feedbackTab === tab.id ? 'none' : '1px solid #e8e8e8',
                          cursor: 'pointer',
                          fontFamily: dmSans.style.fontFamily,
                          transition: 'all 0.2s',
                          fontSize: 14
                        }}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>

                  <textarea
                    value={feedbackMsg}
                    onChange={(e) => setFeedbackMsg(e.target.value)}
                    placeholder={
                      feedbackTab === 1 ? "What do you think about Fonus?\nWhat's working well? What could be better?" :
                      feedbackTab === 2 ? "Describe the bug — what happened,\nwhich page, what you expected vs what you saw..." :
                      "What feature would make Fonus more\nuseful for your exam prep?"
                    }
                    style={{
                      width: '100%',
                      minHeight: 120,
                      background: '#ffffff',
                      border: '1px solid #e0e0e0',
                      borderRadius: 10,
                      padding: 16,
                      fontSize: 15,
                      color: '#0d1b4b',
                      resize: 'vertical',
                      margin: '0 0 20px 0',
                      fontFamily: dmSans.style.fontFamily,
                      boxSizing: 'border-box'
                    }}
                  />

                  <button
                    onClick={handleFeedbackSubmit}
                    disabled={isSubmittingFeedback || !feedbackMsg.trim()}
                    style={{
                      width: '100%',
                      background: isSubmittingFeedback || !feedbackMsg.trim() ? '#e2e8f0' : '#e8b94f',
                      color: '#0d1b4b',
                      fontWeight: 700,
                      padding: '14px 36px',
                      borderRadius: 8,
                      fontSize: 15,
                      border: 'none',
                      cursor: isSubmittingFeedback || !feedbackMsg.trim() ? 'not-allowed' : 'pointer',
                      fontFamily: dmSans.style.fontFamily,
                      transition: 'background 0.2s'
                    }}
                    onMouseEnter={(e) => { if (!isSubmittingFeedback && feedbackMsg.trim()) e.currentTarget.style.background = '#d4a843'; }}
                    onMouseLeave={(e) => { if (!isSubmittingFeedback && feedbackMsg.trim()) e.currentTarget.style.background = '#e8b94f'; }}
                  >
                    {isSubmittingFeedback ? 'Submitting...' : 'Submit →'}
                  </button>
                </>
              )}
            </div>

            <div style={{ display: 'flex', gap: 32, justifyContent: 'center', marginTop: 40, flexWrap: 'wrap' }}>
              <div style={{ fontSize: 13, color: '#94a3b8', fontFamily: dmSans.style.fontFamily }}>👁 Every message is read by the team</div>
              <div style={{ fontSize: 13, color: '#94a3b8', fontFamily: dmSans.style.fontFamily }}>⚡ We respond to bugs within 48 hours</div>
              <div style={{ fontSize: 13, color: '#94a3b8', fontFamily: dmSans.style.fontFamily }}>🔒 Your feedback is private</div>
            </div>
          </div>
        </section>

        {/* SECTION A — FAQ */}
        <section style={{ width: '100%', background: '#f8f9fc', padding: '120px 80px' }} className="faq-wrapper">
          <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            <div style={{ textAlign: 'center', marginBottom: 64 }}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 0 }}
                style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, fontWeight: 800, color: '#e8b94f', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 18 }}
              >
                // FAQ
              </motion.div>
              <motion.h2
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 0 }}
                style={{ fontFamily: playfair.style.fontFamily, fontSize: 52, fontWeight: 700, color: '#0d1b4b', margin: 0, marginBottom: 16 }}
              >
                Questions?<br />We Have Answers.
              </motion.h2>
              <motion.p
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, delay: 0 }}
                style={{ fontFamily: dmSans.style.fontFamily, fontSize: 17, color: '#94a3b8', margin: 0 }}
              >
                Everything you need to know about<br />Fonus — before you start.
              </motion.p>
            </div>

            <div>
              {FAQS.map((faq, i) => {
                const isOpen = openFaq === i;
                return (
                  <div
                    key={i}
                    style={{
                      background: '#ffffff',
                      borderRadius: 12,
                      border: `1px solid ${isOpen ? '#e8b94f' : '#e8e8e8'}`,
                      marginBottom: 12,
                      overflow: 'hidden',
                      transition: 'all 0.3s ease',
                      boxShadow: isOpen ? '0 4px 20px rgba(232,185,79,0.08)' : 'none'
                    }}
                  >
                    <div
                      onClick={() => setOpenFaq(isOpen ? null : i)}
                      style={{
                        padding: '24px 28px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        cursor: 'pointer',
                        fontFamily: dmSans.style.fontFamily
                      }}
                    >
                      <div style={{ fontSize: 16, fontWeight: 600, color: '#0d1b4b' }}>
                        {faq.q}
                      </div>
                      <div style={{ 
                        fontSize: 20, 
                        color: '#e8b94f', 
                        transition: 'transform 0.3s ease', 
                        transform: isOpen ? 'rotate(45deg)' : 'rotate(0deg)',
                        lineHeight: 1
                      }}>
                        +
                      </div>
                    </div>
                    {isOpen && (
                      <div style={{
                        padding: '0 28px 24px',
                        fontSize: 15,
                        color: '#64748b',
                        lineHeight: 1.8,
                        borderTop: '1px solid #f0f0f0',
                        marginTop: -8,
                        paddingTop: 24,
                        fontFamily: dmSans.style.fontFamily
                      }}>
                        {faq.a}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* SECTION 7 — PRE-FOOTER CTA BAND */}
        <section style={{ width: '100%', background: '#e8b94f', padding: '80px 80px', textAlign: 'center' }} className="prefooter-band">
          <div style={{ maxWidth: 1000, margin: '0 auto' }}>
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: playfair.style.fontFamily, fontSize: 48, fontWeight: 700, color: '#0d1b4b', margin: 0, marginBottom: 16, lineHeight: 1.15 }}
            >
              Your CAR 66 License<br />
              Won't Clear Itself.
            </motion.h2>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              style={{ fontFamily: dmSans.style.fontFamily, fontSize: 18, color: 'rgba(13,27,75,0.7)', margin: 0, marginBottom: 40, lineHeight: 1.8 }}
            >
              Join students who stopped guessing<br />
              and started preparing — the right way.
            </motion.p>

            <motion.button
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.7, delay: 0 }}
              onClick={handleHeroCTA}
              style={{
                padding: '18px 48px',
                background: '#0d1b4b',
                color: '#e8b94f',
                fontWeight: 700,
                borderRadius: 10,
                fontSize: 16,
                border: 'none',
                cursor: 'pointer',
                fontFamily: dmSans.style.fontFamily,
              }}
              whileHover={{ backgroundColor: '#172a6e' }}
            >
              Start Preparing — Free →
            </motion.button>
          </div>
        </section>

      </main>

      {/* SECTION 8 — FOOTER */}
      <footer style={{ background: '#0a0f2e', color: '#fff', padding: '80px 80px 40px 80px' }}>
        <style>{`
          .footer-social-link { text-decoration: none; display: inline-flex; }
          .footer-social-box { width: 40px; height: 40px; border-radius: 10px; padding: 10px; background: rgba(255,255,255,0.06); display: flex; align-items: center; justify-content: center; color: rgba(255,255,255,0.5); transition: all 0.2s ease; }
          .footer-social-link:hover .footer-social-box { background: rgba(232,185,79,0.15); color: #e8b94f; }
          .footer-link { text-decoration: none; font-size: 14px; color: rgba(255,255,255,0.5); transition: color 0.2s ease; fontFamily: inherit; }
          .footer-link:hover { color: #e8b94f; }
        `}</style>

        <div style={{ maxWidth: 1200, margin: '0 auto', display: 'grid', gridTemplateColumns: '35% 1fr 1fr 1fr', columnGap: 60, rowGap: 40 }} className="footer-grid">
          {/* COLUMN 1 — Brand */}
          <div>
            <Image
              src="/fonus-logo.svg"
              alt="Fonus"
              width={140}
              height={40}
              priority
              style={{ filter: 'brightness(0) invert(1)', marginBottom: 20, height: 'auto', width: '140px' }}
            />
            <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 15, color: 'rgba(255,255,255,0.45)', lineHeight: 1.7, maxWidth: 260, marginBottom: 32 }}>
              India&apos;s First AI-Powered<br />DGCA AME Exam Platform.
            </div>

            <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
              <a href="#" className="footer-social-link" aria-label="Instagram">
                <div className="footer-social-box">
                  <Instagram size={20} />
                </div>
              </a>
              <a href="#" className="footer-social-link" aria-label="YouTube">
                <div className="footer-social-box">
                  <Youtube size={20} />
                </div>
              </a>
            </div>
          </div>

          {/* COLUMN 2 — Platform */}
          <div>
            <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 11, fontWeight: 700, letterSpacing: '0.15em', color: 'rgba(255,255,255,0.3)', marginBottom: 24 }}>
              PLATFORM
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <a className="footer-link" href="#">Browse Modules</a>
              <a className="footer-link" href="#">How It Works</a>
              <a className="footer-link" href="#">Pricing</a>
              <a className="footer-link" href="#">Progress Tracker</a>
            </div>
          </div>

          {/* COLUMN 3 — Company */}
          <div>
            <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 11, fontWeight: 700, letterSpacing: '0.15em', color: 'rgba(255,255,255,0.3)', marginBottom: 24 }}>
              COMPANY
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <a className="footer-link" href="#">About Fonus</a>
              <a className="footer-link" href="#">FAQ</a>
              <a className="footer-link" href="#">Give Feedback</a>
              <a className="footer-link" href="#">Contact Us</a>
            </div>
          </div>

          {/* COLUMN 4 — Legal & Contact */}
          <div>
            <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 11, fontWeight: 700, letterSpacing: '0.15em', color: 'rgba(255,255,255,0.3)', marginBottom: 24 }}>
              LEGAL
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <a className="footer-link" href="#">Privacy Policy</a>
              <a className="footer-link" href="#">Terms of Service</a>
              <a className="footer-link" href="#">Refund Policy</a>
            </div>

            <div style={{ marginTop: 28 }}>
              <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 11, fontWeight: 700, letterSpacing: '0.15em', color: 'rgba(255,255,255,0.3)', marginBottom: 14 }}>
                CONTACT
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ color: '#e8b94f', fontSize: 14, lineHeight: 1 }}>✉</span>
                <a className="footer-link" href="mailto:fonuslearning@gmail.com" style={{ fontSize: 14 }}>
                  fonuslearning@gmail.com
                </a>
              </div>
            </div>
          </div>
        </div>

        <div style={{ maxWidth: 1200, margin: '60px auto 0 auto', paddingTop: 24, borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 20 }} className="footer-bottom">
          <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, color: 'rgba(255,255,255,0.25)' }}>
            © 2026 Fonus. All rights reserved.
          </div>
          <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 12, color: 'rgba(255,255,255,0.15)' }}>
            Made with &hearts; for Indian Aviation
          </div>
          <div style={{ fontFamily: dmSans.style.fontFamily, fontSize: 13, color: 'rgba(255,255,255,0.25)' }}>
            Built for AME students across India.
          </div>
        </div>
      </footer>
    </div>
  );
}
