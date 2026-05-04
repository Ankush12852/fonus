'use client';

import { Suspense, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '@/lib/supabaseClient';

function ResetPasswordForm() {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(''), 4000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  useEffect(() => {
    // Supabase automatically parses the hash fragment on load.
    // If we're on this page, the user should have just clicked a reset link
    supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === "PASSWORD_RECOVERY") {
        console.log("Password recovery event triggered");
      }
    });
  }, []);

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }

    setLoading(true);
    setError('');

    const { error: resetError } = await supabase.auth.updateUser({ password });

    if (resetError) {
      setError(resetError.message);
      setLoading(false);
    } else {
      setSuccess(true);
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f4f6fb', fontFamily: 'Georgia, serif', padding: '2rem 0' }}>
      <div style={{ background: '#fff', padding: '2.5rem', borderRadius: '16px', width: '100%', maxWidth: '420px', boxShadow: '0 8px 32px rgba(33,59,147,0.08)' }}>
        
        {success ? (
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎉</div>
            <h1 style={{ fontSize: '1.4rem', color: '#172a6e', marginBottom: '1rem', fontWeight: 700 }}>Password Updated</h1>
            <p style={{ color: '#6b7280', fontSize: '0.95rem', marginBottom: '1.5rem', lineHeight: 1.5 }}>
              Your password has been successfully reset.
            </p>
            <button 
              onClick={() => router.push('/login')}
              style={{ width: '100%', padding: '0.875rem', background: '#213b93', color: '#fff', border: 'none', borderRadius: '8px', fontSize: '1rem', fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}
            >
              Go to Login
            </button>
          </div>
        ) : (
          <>
            <h1 style={{ textAlign: 'center', fontSize: '1.8rem', color: '#172a6e', marginBottom: '0.4rem', fontWeight: 700 }}>Set New Password</h1>
            <p style={{ textAlign: 'center', color: '#6b7280', marginBottom: '2rem', fontSize: '0.9rem' }}>Enter a new password for your account.</p>

            {error && <div style={{ background: '#dc2626', color: '#ffffff', fontWeight: 'bold', padding: '0.75rem', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.85rem', textAlign: 'center' }}>{error}</div>}
            
            <form onSubmit={handleReset} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', color: '#374151', marginBottom: '0.4rem', fontWeight: 600 }}>New Password</label>
                <input 
                  type="password" 
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete="off"
                  placeholder="••••••••"
                  required
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1.5px solid #e2e6f0', fontSize: '0.95rem', outline: 'none', fontFamily: 'inherit' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', color: '#374151', marginBottom: '0.4rem', fontWeight: 600 }}>Confirm New Password</label>
                <input 
                  type="password" 
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  autoComplete="off"
                  placeholder="••••••••"
                  required
                  style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', border: '1.5px solid #e2e6f0', fontSize: '0.95rem', outline: 'none', fontFamily: 'inherit' }}
                />
              </div>
              <button 
                type="submit" 
                disabled={loading}
                style={{ width: '100%', padding: '0.875rem', background: '#213b93', color: '#fff', border: 'none', borderRadius: '8px', fontSize: '1rem', fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', fontFamily: 'inherit', marginTop: '0.2rem', opacity: loading ? 0.7 : 1, transition: 'background 0.2s' }}
              >
                {loading ? 'Updating...' : 'Update Password'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', background: '#f4f6fb' }} />}>
      <ResetPasswordForm />
    </Suspense>
  );
}
