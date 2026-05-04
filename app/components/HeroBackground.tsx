'use client';

import { motion } from 'framer-motion';

export default function HeroBackground() {
  return (
    <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 0, pointerEvents: 'none', overflow: 'hidden' }}>
      {/* Sparkles */}
      {[...Array(25)].map((_, i) => (
        <motion.div
          key={`sparkle-${i}`}
          initial={{ 
            opacity: Math.random() * 0.4 + 0.1, 
            scale: Math.random() * 0.5 + 0.5,
            left: (Math.random() * 100) + "%", 
            top: (Math.random() * 100) + "%" 
          }}
          animate={{ 
            opacity: [0.1, 0.6, 0.1],
            scale: [0.5, 1, 0.5],
            y: [0, -15, 0] 
          }}
          transition={{ 
            duration: Math.random() * 3 + 3, 
            repeat: Infinity,
            ease: "easeInOut"
          }}
          style={{
            position: 'absolute',
            width: '2px',
            height: '2px',
            background: '#e8b94f',
            borderRadius: '50%',
            boxShadow: '0 0 4px #e8b94f'
          }}
        />
      ))}
      
      {/* Gradient Glow */}
      <div className="absolute right-0 lg:right-[15%] top-1/2 -translate-y-1/2" style={{
        width: '600px', height: '600px', background: 'radial-gradient(circle, rgba(232,185,79,0.06) 0%, transparent 70%)'
      }} />

      {/* Clouds */}
      {[ 
        { w: 160, h: 70, op: 0.12, t: '12%', l: '8%', xMove: [0, 25], dur: 14 },
        { w: 110, h: 50, op: 0.10, t: '18%', r: '25%', xMove: [0, -20], dur: 11 },
        { w: 80, h: 36, op: 0.08, t: '55%', r: '8%', xMove: [0, 18], dur: 16 },
        { w: 140, h: 60, op: 0.09, t: 'auto', b: '20%', l: '20%', xMove: [0, -22], dur: 12 },
        { w: 100, h: 45, op: 0.07, t: '38%', l: '45%', xMove: [0, 15], dur: 18 }
      ].map((cloud, i) => (
        <motion.svg 
          key={`cloud-${i}`} viewBox="0 0 200 80" width={cloud.w} height={cloud.h}
          style={{ 
            position: 'absolute', top: cloud.t, bottom: cloud.b, left: cloud.l, right: cloud.r, 
            opacity: cloud.op, color: '#fff', zIndex: 1 
          }}
          animate={{ x: cloud.xMove }} 
          transition={{ duration: cloud.dur, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
        >
          <path d="M 30 60 Q 10 60 10 45 Q 10 30 25 28 Q 22 10 40 8 Q 55 6 60 20 Q 70 10 85 14 Q 100 8 105 22 Q 120 15 125 28 Q 140 25 142 40 Q 145 58 125 60 Z" fill="currentColor"/>
        </motion.svg>
      ))}
    </div>
  );
}
