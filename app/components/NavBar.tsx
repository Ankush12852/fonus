'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { getCurrentUser, onAuthChange } from '@/lib/auth';
import AuthModal from './AuthModal';
import AccountDetailsModal from './AccountDetailsModal';
import { supabase } from '@/lib/supabaseClient';

export default function NavBar({ children, transparentAtTop = false }: { children?: React.ReactNode, transparentAtTop?: boolean }) {
  const [userEmail, setUserEmail] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [isSolid, setIsSolid] = useState(!transparentAtTop);

  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showAccountModal, setShowAccountModal] = useState(false);

  useEffect(() => {
    if (!transparentAtTop) return;

    const handleScroll = () => {
      setIsSolid(window.scrollY > 20);
    };

    handleScroll();
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [transparentAtTop]);

  useEffect(() => {
    let mounted = true;

    const fetchProfileName = async (uid: string) => {
      try {
        const { data } = await supabase.from('profiles').select('full_name').eq('id', uid).single();
        if (mounted && data) {
           setUserName(data.full_name);
        }
      } catch (e) {}
    };

    // Check existing session on mount
    getCurrentUser().then((user) => {
      if (mounted && user) {
        setUserEmail(user.email ?? null);
        setUserId(user.id);
        localStorage.setItem('user_id', user.id);
        localStorage.setItem('user_email', user.email ?? '');
        fetchProfileName(user.id);
      }
    });

    // Listen for future auth changes  
    const subscription = onAuthChange((user) => {
      if (!mounted) return;
      if (user) {
        setUserEmail(user.email ?? null);
        setUserId(user.id);
        localStorage.setItem('user_id', user.id);
        localStorage.setItem('user_email', user.email ?? '');
        fetchProfileName(user.id);
        setShowAuthModal(false);
      } else {
        setUserEmail(null);
        setUserId(null);
        setUserName(null);
        localStorage.removeItem('user_id');
        localStorage.removeItem('user_email');
        setShowAccountModal(false);
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const displayIdentifier = userName || (userEmail ? (userEmail.length > 18 ? userEmail.slice(0, 15) + '...' : userEmail) : null);
  const userInitial = displayIdentifier ? displayIdentifier.charAt(0).toUpperCase() : '';

  return (
    <>
      <header
        style={{
          background: isSolid ? '#fff' : 'transparent',
          borderBottom: isSolid ? '1px solid #e5e7eb' : '1px solid transparent',
          height: '64px',
          padding: '0 1.5rem',
          boxSizing: 'border-box',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: transparentAtTop ? 'fixed' : 'sticky',
          width: '100%',
          left: 0,
          top: 0,
          zIndex: 50,
          transition: 'background 0.3s ease, border-bottom 0.3s ease, box-shadow 0.3s ease',
          boxShadow: isSolid ? '0 2px 8px rgba(33,59,147,0.06)' : 'none',
        }}
      >
        {/* Left: Logo + optional extra content */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <Link href="/">
            <Image 
              src="/fonus-logo.svg" 
              alt="Fonus" 
              width={120} 
              height={42} 
              priority
              style={{ 
                transition: 'filter 0.3s ease',
                filter: isSolid ? 'none' : 'brightness(0) invert(1)',
                height: 'auto',
                width: '120px'
              }} 
            />
          </Link>
          {children}
        </div>

        {/* Right: Auth buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.2rem' }}>
          {userId ? (
            <div 
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}
              onClick={() => setShowAccountModal(true)}
            >
              <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: isSolid ? '#172a6e' : '#fff', color: isSolid ? '#fff' : '#172a6e', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.9rem', fontWeight: 600, transition: 'all 0.3s ease' }}>
                {userInitial}
              </div>
              <span style={{ fontSize: '0.9rem', color: isSolid ? '#172a6e' : '#fff', fontWeight: 600, fontFamily: 'inherit', transition: 'color 0.3s ease' }}>
                {displayIdentifier}
              </span>
            </div>
          ) : (
            <button 
              onClick={() => setShowAuthModal(true)}
              style={{ padding: '0.45rem 1.1rem', background: isSolid ? '#213b93' : '#fff', color: isSolid ? '#fff' : '#172a6e', border: '1px solid currentColor', borderRadius: '8px', fontSize: '0.85rem', fontWeight: 600, fontFamily: 'inherit', cursor: 'pointer', transition: 'all 0.3s ease' }}>
              ACCOUNT
            </button>
          )}
        </div>
      </header>

      {showAuthModal && <AuthModal onClose={() => setShowAuthModal(false)} />}
      
      {showAccountModal && userId && userEmail && (
        <AccountDetailsModal 
          onClose={() => setShowAccountModal(false)} 
          userId={userId} 
          userEmail={userEmail} 
        />
      )}
    </>
  );
}
