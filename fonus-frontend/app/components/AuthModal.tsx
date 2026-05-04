'use client';

import { useState, useEffect } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { StreamSelector } from '@/app/components/StreamSelector';

const DISPOSABLE_DOMAINS = [
  'mailinator.com', 'tempmail.com', 'guerrillamail.com', '10minutemail.com', 
  'throwaway.email', 'yopmail.com', 'trashmail.com', 'fakeinbox.com', 
  'sharklasers.com', 'guerrillamailblock.com', 'grr.la', 'spam4.me', 
  'temp-mail.org', 'dispostable.com', 'maildrop.cc'
];

export default function AuthModal({ onClose, initialMode = 'signin', message = '', initialStream = '' }: { onClose: () => void, initialMode?: 'signin' | 'signup', message?: string, initialStream?: string }) {
  const [isSignUpActive, setIsSignUpActive] = useState(initialMode === 'signup');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(message);
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(''), 4000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  useEffect(() => {
    if (successMsg) {
      const timer = setTimeout(() => setSuccessMsg(''), 3000);
      return () => clearTimeout(timer);
    }
  }, [successMsg]);

  // Sign In states
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [isResetMode, setIsResetMode] = useState(false);

  // Sign Up states
  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupConfirm, setSignupConfirm] = useState('');
  const [signupOrg, setSignupOrg] = useState('');
  const [signupPosition, setSignupPosition] = useState('student');
  const [signupStream, setSignupStream] = useState(initialStream);

  const [emailExists, setEmailExists] = useState(false);
  const [checkingEmail, setCheckingEmail] = useState(false);

  // TASK — Debounced email duplicate check
  useEffect(() => {
    if (!signupEmail || !signupEmail.includes('@') || !signupEmail.includes('.')) {
      setEmailExists(false);
      return;
    }
    if (!isSignUpActive) return; // Only check on signup

    setCheckingEmail(true);
    const timer = setTimeout(async () => {
      try {
        // We use the Supabase client directly for speed and reliability
        const { data, error } = await supabase
          .from('profiles')
          .select('id')
          .eq('email', signupEmail)
          .abortSignal(AbortSignal.timeout(4000)) // Safety timeout
          .maybeSingle();

        if (!error && data) {
          setEmailExists(true);
        } else {
          setEmailExists(false);
        }
      } catch (err) {
        console.error("Email check failed:", err);
        setEmailExists(false);
      } finally {
        setCheckingEmail(false);
      }
    }, 600);
    return () => clearTimeout(timer);
  }, [signupEmail, isSignUpActive]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isResetMode) {
      handleForgotPassword(e);
      return;
    }

    setError('');
    setLoading(true);
    try {
      const { data, error: authError } = await supabase.auth.signInWithPassword({
        email: loginEmail,
        password: loginPassword,
      });

      if (authError) throw authError;
      
      if (data.user) {
        localStorage.setItem('user_id', data.user.id);
        onClose();
        window.location.reload(); 
      }
    } catch (err: any) {
      if (err.message.includes('Email not confirmed')) {
        setError('Please verify your email address first.');
      } else if (err.message.includes('Invalid login')) {
        setError('Invalid email or password.');
      } else {
        setError(err.message || 'Login failed.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');
    if (!loginEmail) return setError('Please enter your email address in the field above.');

    setLoading(true);
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(loginEmail);
      if (error) throw error;
      setSuccessMsg('Password reset link sent to your email.');
      setTimeout(() => { setIsResetMode(false); setSuccessMsg(''); }, 3000);
    } catch (err: any) {
      setError(err.message || 'Failed to send reset link.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    if (signupPassword !== signupConfirm) return setError('Passwords do not match.');
    if (signupPassword.length < 6) return setError('Password must be at least 6 characters.');
    
    const emailParts = signupEmail.split('@');
    if (emailParts.length !== 2 || !emailParts[1].includes('.')) return setError('Please enter a valid email address.');
    if (DISPOSABLE_DOMAINS.includes(emailParts[1].toLowerCase())) return setError('Temporary emails are not allowed.');

    setLoading(true);
    try {
      const { data, error: authError } = await supabase.auth.signUp({
        email: signupEmail,
        password: signupPassword,
      });

      if (authError) throw authError;

      if (data.user) {
        // Create profile in Supabase table directly via client to avoid 503 backend bugs
        const { error: profileError } = await supabase.from('profiles').insert([
          {
            id: data.user.id,
            email: signupEmail,
            full_name: signupName,
            college: signupOrg,
            stream: signupStream,
            tier: 'free' // Required by schema
          }
        ]);
        
        if (profileError) {
          console.error("Profile insert error", profileError);
        }
        
        if (data.session) {
          // Email confirmations are disabled. We are already logged in!
          localStorage.setItem('user_id', data.user.id);
          setSuccessMsg('Account created successfully! Logging you in...');
          setTimeout(() => {
              window.location.reload();
          }, 1500);
        } else {
          // Email confirmations are required
          setSuccessMsg('Account created! Please check your email to verify before logging in. (Or disable Confirm Email in Supabase)');
          setTimeout(() => {
              setIsSignUpActive(false);
              setSuccessMsg('');
          }, 4000);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Signup failed.');
    } finally {
      setLoading(false);
    }
  };

  const togglePanel = () => {
    setError('');
    setSuccessMsg('');
    setIsSignUpActive(!isSignUpActive);
    setIsResetMode(false);
  };

  return (
    <div className="auth-modal-overlay" onClick={onClose}>
      <div className={`auth-container ${isSignUpActive ? "right-panel-active" : ""}`} onClick={(e) => e.stopPropagation()}>
        
        {/* Sign Up Panel */}
        <div className="form-container sign-up-container">
          <form onSubmit={handleSignup} className="auth-form">
            <h2>Create Account</h2>
            <div className="input-field">
              <input type="text" placeholder="Name" value={signupName} onChange={e => setSignupName(e.target.value)} required />
            </div>
            <div className="input-field">
              <input type="email" placeholder="Email" value={signupEmail} onChange={e => setSignupEmail(e.target.value)} required />
              {checkingEmail && (
                <p style={{ color: '#6b7280', fontSize: '12px', marginTop: '4px', textAlign: 'left' }}>
                  Checking...
                </p>
              )}
              {emailExists && !checkingEmail && (
                <p style={{ color: '#dc2626', fontSize: '12px', marginTop: '4px', textAlign: 'left' }}>
                  Email already used. <span style={{ textDecoration: 'underline', cursor: 'pointer' }} onClick={(e) => { e.preventDefault(); togglePanel(); }}>Sign in instead?</span>
                </p>
              )}
            </div>
            <div className="input-field-group">
              <input type="password" placeholder="Password" value={signupPassword} onChange={e => setSignupPassword(e.target.value)} required />
              <input type="password" placeholder="Confirm Password" value={signupConfirm} onChange={e => setSignupConfirm(e.target.value)} required />
            </div>
            <div className="input-field">
              <input type="text" placeholder="Organization (Optional)" value={signupOrg} onChange={e => setSignupOrg(e.target.value)} />
            </div>
            <div className="input-field">
              <StreamSelector 
                value={signupStream} 
                onChange={val => setSignupStream(val)} 
              />
            </div>
            <div className="input-field">
              <select value={signupPosition} onChange={e => setSignupPosition(e.target.value)} required>
                <option value="student">Student</option>
                <option value="working">Working Professional</option>
              </select>
            </div>
            {error && !isSignUpActive === false && <p className="error-text">{error}</p>}
            {successMsg && !isSignUpActive === false && <p className="success-text">{successMsg}</p>}
            
            <button type="submit" disabled={loading || emailExists || checkingEmail} className="auth-btn submit-btn" style={{marginTop: '10px'}}>
              {loading ? 'Creating...' : 'Sign Up'}
            </button>
            
            {/* Mobile fallback switch */}
            <div className="mobile-toggle">
                Already have an account? <span onClick={togglePanel}>Log In</span>
            </div>
          </form>
        </div>

        {/* Sign In Panel */}
        <div className="form-container sign-in-container">
          <form onSubmit={handleLogin} className="auth-form">
            <h2>{isResetMode ? 'Reset Password' : 'Sign In'}</h2>
            {!isResetMode && <span className="auth-subtitle">Welcome back. Please enter your details.</span>}
            
            {isResetMode && <span className="auth-subtitle" style={{marginBottom: '1rem'}}>Enter email to receive reset link</span>}

            <div className="input-field">
                <input type="email" placeholder="Email" value={loginEmail} onChange={e => setLoginEmail(e.target.value)} required />
            </div>
            {!isResetMode && (
                <div className="input-field">
                    <input type="password" placeholder="Password" value={loginPassword} onChange={e => setLoginPassword(e.target.value)} required />
                </div>
            )}
            
            {!isResetMode && (
                <span className="forgot-password" onClick={() => setIsResetMode(true)}>Forgot your password?</span>
            )}
            
            {error && !isSignUpActive === true && <p className="error-text">{error}</p>}
            {successMsg && !isSignUpActive === true && <p className="success-text">{successMsg}</p>}
            
            <button type="submit" disabled={loading} className="auth-btn submit-btn" style={{marginTop: '10px'}}>
              {loading ? 'Wait...' : (isResetMode ? 'Send Reset Link' : 'Sign In')}
            </button>
            
            {isResetMode && (
                <span className="forgot-password" onClick={() => setIsResetMode(false)} style={{marginTop:'10px'}}>Back to Sign In</span>
            )}

            {/* Mobile fallback switch */}
            <div className="mobile-toggle">
                New here? <span onClick={togglePanel}>Create Account</span>
            </div>
          </form>
        </div>

        {/* Overlay Container (Sliding part) */}
        <div className="overlay-container">
          <div className="overlay">
            <div className="overlay-panel overlay-left">
              <h2>Welcome Back!</h2>
              <p>Keep preparing with Fonus using your existing account.</p>
              <button disabled={loading} type="button" className="auth-btn ghost" onClick={togglePanel}>Sign In</button>
            </div>
            <div className="overlay-panel overlay-right">
              <h2>Hello, Friend!</h2>
              <p>Enter your details and start your DGCA exam prep with Fonus.</p>
              <button disabled={loading} type="button" className="auth-btn ghost" onClick={togglePanel}>Sign Up</button>
            </div>
          </div>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{__html: `
        .auth-modal-overlay {
          position: fixed;
          top: 0; left: 0; width: 100vw; height: 100vh;
          background: rgba(0, 0, 0, 0.4);
          backdrop-filter: blur(8px);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 9999;
          font-family: 'Helvetica Neue', Arial, sans-serif;
        }

        .auth-container {
          background-color: #fff;
          border-radius: 20px;
          box-shadow: 0 14px 28px rgba(0,0,0,0.25), 0 10px 10px rgba(0,0,0,0.22);
          position: relative;
          overflow: visible;
          width: 768px;
          max-width: 95%;
          min-height: 540px;
        }

        .auth-container h2 {
          font-weight: bold;
          margin: 0 0 10px;
          color: #172a6e;
          font-size: 32px;
        }

        .auth-container p {
          font-size: 14px;
          font-weight: 100;
          line-height: 20px;
          letter-spacing: 0.5px;
          margin: 20px 0 30px;
          color: #fff;
        }

        .auth-subtitle {
          font-size: 12px;
          color: #6b7280;
          margin-bottom: 20px;
        }

        .auth-container span.forgot-password {
          color: #4b5563;
          font-size: 12px;
          text-decoration: none;
          margin: 15px 0;
          cursor: pointer;
          transition: color 0.2s ease;
        }
        
        .auth-container span.forgot-password:hover {
            color: #213b93;
            text-decoration: underline;
        }

        .auth-btn {
          border-radius: 20px;
          border: 1px solid #213b93;
          background-color: #213b93;
          color: #FFFFFF;
          font-size: 12px;
          font-weight: bold;
          padding: 12px 45px;
          letter-spacing: 1px;
          text-transform: uppercase;
          transition: transform 80ms ease-in, background 0.2s ease;
          cursor: pointer;
        }

        .auth-btn:active {
          transform: scale(0.95);
        }

        .auth-btn:focus {
          outline: none;
        }
        
        .auth-btn:disabled {
          background-color: #6b7280;
          border-color: #6b7280;
          cursor: not-allowed;
          opacity: 0.8;
        }

        .auth-btn.ghost {
          background-color: transparent;
          border-color: #FFFFFF;
        }
        
        .auth-btn.ghost:hover {
          background-color: rgba(255,255,255,0.1);
        }

        .auth-form {
          background-color: #FFFFFF;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-direction: column;
          padding: 0 40px;
          height: 100%;
          text-align: center;
        }

        .input-field {
          width: 100%;
          margin: 6px 0;
        }
        
        .input-field-group {
          width: 100%;
          display: flex;
          gap: 10px;
          margin: 6px 0;
        }

        .auth-container input, .auth-container select {
          background-color: #f3f4f6;
          border: none;
          border-radius: 8px;
          padding: 12px 15px;
          width: 100%;
          font-size: 14px;
          outline: none;
          font-family: inherit;
        }

        .form-container {
          position: absolute;
          top: 0;
          height: 100%;
          transition: all 0.6s ease-in-out;
        }

        .sign-in-container {
          left: 0;
          width: 50%;
          z-index: 2;
        }

        .sign-up-container {
          left: 0;
          width: 50%;
          opacity: 0;
          z-index: 1;
        }

        .auth-container.right-panel-active .sign-in-container {
          transform: translateX(100%);
        }

        .auth-container.right-panel-active .sign-up-container {
          transform: translateX(100%);
          opacity: 1;
          z-index: 5;
          animation: show 0.6s;
        }

        @keyframes show {
          0%, 49.99% { opacity: 0; z-index: 1; }
          50%, 100% { opacity: 1; z-index: 5; }
        }

        .overlay-container {
          position: absolute;
          top: 0;
          left: 50%;
          width: 50%;
          height: 100%;
          overflow: hidden;
          transition: transform 0.6s ease-in-out;
          z-index: 100;
        }

        .auth-container.right-panel-active .overlay-container {
          transform: translateX(-100%);
        }

        .overlay {
          background: #213b93;
          background: linear-gradient(to right, #172a6e, #213b93);
          background-repeat: no-repeat;
          background-size: cover;
          background-position: 0 0;
          color: #FFFFFF;
          position: relative;
          left: -100%;
          height: 100%;
          width: 200%;
          transform: translateX(0);
          transition: transform 0.6s ease-in-out;
        }

        .auth-container.right-panel-active .overlay {
          transform: translateX(50%);
        }

        .overlay-panel {
          position: absolute;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-direction: column;
          padding: 0 40px;
          text-align: center;
          top: 0;
          height: 100%;
          width: 50%;
          transform: translateX(0);
          transition: transform 0.6s ease-in-out;
        }

        .overlay-panel h2 {
            color: #fff;
        }

        .overlay-left {
          transform: translateX(-20%);
        }

        .auth-container.right-panel-active .overlay-left {
          transform: translateX(0);
        }

        .overlay-right {
          right: 0;
          transform: translateX(0);
        }

        .auth-container.right-panel-active .overlay-right {
          transform: translateX(20%);
        }

        .error-text {
            color: #ffffff;
            font-size: 13px;
            font-weight: bold;
            margin: 5px 0 10px;
            background: #dc2626;
            width: 100%;
            padding: 8px;
            border-radius: 6px;
        }
        
        .success-text {
            color: #ffffff;
            font-size: 13px;
            font-weight: bold;
            margin: 5px 0 10px;
            background: #16a34a;
            width: 100%;
            padding: 8px;
            border-radius: 6px;
        }

        .mobile-toggle {
            display: none;
            margin-top: 15px;
            font-size: 13px;
            color: #6b7280;
        }
        
        .mobile-toggle span {
            color: #213b93;
            font-weight: bold;
            cursor: pointer;
        }

        @media (max-width: 768px) {
            .overlay-container { display: none; }
            .form-container { width: 100%; }
            .sign-in-container { z-index: 5; }
            .sign-up-container { z-index: 4; }
            .auth-container.right-panel-active .sign-in-container { transform: translateX(0); z-index: 4; opacity: 0;}
            .auth-container.right-panel-active .sign-up-container { transform: translateX(0); z-index: 5; opacity: 1;}
            .mobile-toggle { display: block; }
        }
      `}} />
    </div>
  );
}
