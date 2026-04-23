'use client';

import { useState, useRef, useEffect } from 'react'

const STREAMS = [
  // Group: B1 — Mechanical
  { id: "B1.1", label: "B1.1 — Turbine Aeroplane",    group: "B1 Mechanical" },
  { id: "B1.2", label: "B1.2 — Piston Aeroplane",     group: "B1 Mechanical" },
  { id: "B1.3", label: "B1.3 — Turbine Helicopter",   group: "B1 Mechanical" },
  { id: "B1.4", label: "B1.4 — Piston Helicopter",    group: "B1 Mechanical" },
  // Group: Category A — Line Maintenance
  { id: "A1",   label: "A1 — Turbine Fixed Wing",     group: "Category A" },
  { id: "A2",   label: "A2 — Piston Fixed Wing",      group: "Category A" },
  { id: "A3",   label: "A3 — Turbine Rotorcraft",     group: "Category A" },
  { id: "A4",   label: "A4 — Piston Rotorcraft",      group: "Category A" },
  // Group: Avionics & Other
  { id: "B2",   label: "B2 — Avionics",               group: "Avionics & Other" },
  { id: "B2L",  label: "B2L — Avionics (Limited)",    group: "Avionics & Other" },
  { id: "B3",   label: "B3 — Piston Non-pressurised", group: "Avionics & Other" },
  { id: "C",    label: "C — Certifying Engineer",     group: "Avionics & Other" },
]

const GROUPS = ["B1 Mechanical", "Category A", "Avionics & Other"]

interface Props {
  value: string
  onChange: (val: string) => void
}

export function StreamSelector({ value, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const selected = STREAMS.find(s => s.id === value)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  return (
    <div ref={ref} style={{ position: 'relative', width: '100%', marginBottom: '15px' }}>
      
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%',
          padding: '12px 14px',
          background: '#fff',
          border: `1px solid ${open ? '#0A0F2C' : '#CBD5E1'}`,
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          cursor: 'pointer',
          fontSize: '14px',
          color: selected ? '#0A0F2C' : '#94A3B8',
          transition: 'border-color 0.15s',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {selected ? (
            <>
              <span style={{
                fontFamily: 'monospace',
                fontSize: '11px',
                fontWeight: 600,
                background: '#F0F4FF',
                color: '#0A0F2C',
                padding: '2px 7px',
                borderRadius: '4px',
                letterSpacing: '0.05em'
              }}>
                {selected.id}
              </span>
              <span style={{ fontWeight: 500 }}>{selected.label.split('—')[1]?.trim()}</span>
            </>
          ) : (
            <span>Select your stream</span>
          )}
        </span>
        {/* Chevron */}
        <svg
          width="14" height="14" viewBox="0 0 14 14" fill="none"
          style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}
        >
          <path d="M2 5l5 5 5-5" stroke="#64748B" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      {/* Dropdown panel */}
      {open && (
        <div style={{
          position: 'absolute',
          top: 'calc(100% + 6px)',
          left: 0,
          right: 0,
          background: '#fff',
          border: '1px solid #E2E8F0',
          borderRadius: '10px',
          boxShadow: '0 8px 24px rgba(10,15,44,0.12)',
          zIndex: 100,
          maxHeight: open ? '300px' : '0px',
          overflowY: open ? 'auto' : 'hidden',
          overflow: open ? 'auto' : 'hidden',
          opacity: 1,
          transition: 'max-height 0.2s ease, opacity 0.15s ease',
        }}>
          {GROUPS.map(group => (
            <div key={group}>
              <div style={{
                fontSize: '10px',
                fontWeight: 700,
                letterSpacing: '0.08em',
                color: '#94A3B8',
                padding: '12px 14px 6px',
                textTransform: 'uppercase',
                background: '#F8FAFC'
              }}>
                {group}
              </div>
              {STREAMS.filter(s => s.group === group).map(stream => (
                <div
                  key={stream.id}
                  onClick={() => { onChange(stream.id); setOpen(false) }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '10px 14px',
                    cursor: 'pointer',
                    fontSize: '13px',
                    color: '#0A0F2C',
                    background: value === stream.id ? '#F0F4FF' : 'transparent',
                    borderLeft: value === stream.id ? '4px solid #D4A853' : '4px solid transparent',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => {
                    if (value !== stream.id)
                      (e.currentTarget as HTMLElement).style.background = '#F8FAFC'
                  }}
                  onMouseLeave={e => {
                    if (value !== stream.id)
                      (e.currentTarget as HTMLElement).style.background = 'transparent'
                  }}
                >
                  <span style={{
                    fontFamily: 'monospace',
                    fontSize: '11px',
                    fontWeight: 700,
                    background: value === stream.id ? '#DDE4FF' : '#F1F5F9',
                    color: '#0A0F2C',
                    padding: '2px 7px',
                    borderRadius: '4px',
                    minWidth: '42px',
                    textAlign: 'center',
                  }}>
                    {stream.id}
                  </span>
                  <span style={{ fontWeight: value === stream.id ? 600 : 400 }}>
                    {stream.label.split('—')[1]?.trim()}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
