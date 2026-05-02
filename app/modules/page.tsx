'use client';

import { useEffect, useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';
import AuthModal from '@/app/components/AuthModal';
import NavBar from '@/app/components/NavBar';

const ALL_MODULES = [
  { id: 'M3',  name: 'Electrical Fundamentals',                              streams: ['B1.1','B1.2','B1.3','B1.4','A1','A2','A3','A4','B2','B3','C'] },
  { id: 'M4',  name: 'Electronic Fundamentals',                             streams: ['B1.1','B1.2','B1.3','B1.4','A1','A2','A3','A4','B2','C'] },
  { id: 'M5',  name: 'Digital Techniques',                                  streams: ['B1.1','B1.2','B1.3','B1.4','A1','A2','A3','A4','B2','B3','C'] },
  { id: 'M6',  name: 'Materials & Hardware',                                streams: ['B1.1','B1.2','B1.3','B1.4','A1','A2','A3','A4','B2','B3','C'] },
  { id: 'M7',  name: 'Maintenance Practices',                               streams: ['B1.1','B1.2','B1.3','B1.4','A1','A2','A3','A4','B2','B3','C'] },
  { id: 'M8',  name: 'Basic Aerodynamics',                                  streams: ['B1.1','B1.2','B1.3','B1.4','A1','A2','A3','A4','B2','B3','C'] },
  { id: 'M9',  name: 'Human Factors',                                       streams: ['B1.1','B1.2','B1.3','B1.4','A1','A2','A3','A4','B2','B3','C'] },
  { id: 'M10', name: 'Aviation Legislation',                                streams: ['B1.1','B1.2','B1.3','B1.4','A1','A2','A3','A4','B2','B3','C'] },
  { id: 'M11A', name: 'Turbine Aeroplane Aerodynamics, Structures & Systems', streams: ['B1.1','A1','C'] },
  { id: 'M11B', name: 'Piston Aeroplane Aerodynamics, Structures & Systems',  streams: ['B1.2','A2','B3','C'] },
  { id: 'M12', name: 'Helicopter Aerodynamics, Structures & Systems',        streams: ['B1.3','B1.4','A3','A4','C'] },
  { id: 'M13', name: 'Aircraft Aerodynamics, Structures & Systems (B2)',     streams: ['B2','C'] },
  { id: 'M14', name: 'Propulsion',                                          streams: ['B2','C'] },
  { id: 'M15', name: 'Gas Turbine Engine',                                  streams: ['B1.1','B1.3','A1','A3','C'] },
  { id: 'M16', name: 'Piston Engine',                                       streams: ['B1.2','B1.4','A2','A4','B3','C'] },
  { id: 'M17', name: 'Propeller',                                           streams: ['B1.1','B1.2','A1','A2','B3','C'] },
];

const STREAM_MODULE_MAP: Record<string, string[]> = {
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

function ModulesContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const stream = searchParams.get('stream') || 'B1.1';
  const relevantIds = STREAM_MODULE_MAP[stream] || [];
  
  const [session, setSession] = useState<any>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    });
  }, []);

  const handleModuleClick = (moduleId: string) => {
    if (!session) {
      setShowAuthModal(true);
    } else {
      router.push(`/module/${moduleId}?stream=${stream}`);
    }
  };

  const modules = ALL_MODULES.filter((m) => relevantIds.includes(m.id));

  return (
    <main style={{ minHeight: '100vh', background: '#f4f6fb' }}>
      <NavBar>
        <span
          style={{
            background: '#f0f3fc',
            color: '#213b93',
            padding: '4px 12px',
            borderRadius: '20px',
            fontSize: '0.8rem',
            fontWeight: 600,
          }}
        >
          {stream}
        </span>
      </NavBar>

      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '2rem 1rem' }}>
        <h1
          style={{
            fontSize: '1.6rem',
            color: '#172a6e',
            marginBottom: '0.5rem',
            fontFamily: 'Georgia, serif',
          }}
        >
          Your Modules
        </h1>
        <p style={{ color: '#6b7280', marginBottom: '2rem', fontSize: '0.95rem' }}>
          Select a module to start studying. Free tier: up to{' '}
          <strong>18 hours of AI chat per week</strong> and{' '}
          <strong>9 practice sets per week</strong> (per module, resets Monday) — same limits shown in Plans & Access.
        </p>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
            gap: '1rem',
          }}
        >
          {modules.map((mod, i) => {
            return (
              <div
                key={mod.id}
                className="module-card"
                onClick={() => handleModuleClick(mod.id)}
                style={{
                  background: '#fff',
                  border: '1px solid #dde2f0',
                  borderRadius: '14px',
                  padding: '1.5rem',
                  boxShadow: '0 2px 8px rgba(33,59,147,0.04)',
                  animationDelay: `${i * 0.05}s`,
                  opacity: 0,
                  animation: `fadeIn 0.4s ease ${i * 0.05}s forwards`,
                  cursor: 'pointer'
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '0.75rem',
                  }}
                >
                   <span
                    style={{
                      background: '#f0f3fc',
                      color: '#213b93',
                      padding: '4px 10px',
                      borderRadius: '6px',
                      fontSize: '0.8rem',
                      fontWeight: 700,
                      fontFamily: 'Georgia, serif',
                    }}
                  >
                    {mod.id}
                  </span>
                </div>

                <h3
                  style={{
                    fontSize: '1rem',
                    fontWeight: 600,
                    color: '#1a1f3a',
                    marginBottom: '1rem',
                    lineHeight: 1.3,
                    fontFamily: 'Georgia, serif',
                  }}
                >
                  {mod.name}
                </h3>

                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <span
                    style={{
                      fontSize: '0.8rem',
                      color: '#22c55e',
                      fontWeight: 500,
                    }}
                  >
                    ● Free access
                  </span>
                  <span style={{ fontSize: '1.2rem', color: '#213b93' }}>→</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {showAuthModal && (
        <AuthModal 
          onClose={() => setShowAuthModal(false)} 
          initialMode="signup"
          message="No account found. Create One"
          initialStream={stream}
        />
      )}
    </main>
  );
}

export default function ModulesPage() {
  return (
    <Suspense fallback={<div style={{ padding: '2rem', textAlign: 'center' }}>Loading...</div>}>
      <ModulesContent />
    </Suspense>
  );
}
