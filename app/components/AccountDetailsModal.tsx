'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabaseClient';
import { logout } from '@/lib/auth';

export default function AccountDetailsModal({ onClose, userEmail, userId }: { onClose: () => void, userEmail: string, userId: string }) {
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<any>(null);
  const [modules, setModules] = useState<string[]>([]);
  const [unlockedModules, setUnlockedModules] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [isEditingStream, setIsEditingStream] = useState(false);
  const [newStream, setNewStream] = useState('');

  useEffect(() => {
    const uid = localStorage.getItem('user_id');
    if (!uid) return;
    const fetchUnlocked = async () => {
      const now = new Date().toISOString();
      const { data } = await supabase
        .from('module_access')
        .select('module')
        .eq('user_id', uid)
        .gt('access_expires_at', now);
      if (data) {
        setUnlockedModules(data.map((d: any) => d.module));
      }
    };
    fetchUnlocked();
  }, []);

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

  useEffect(() => {
    async function fetchAccountDetails() {
      try {
        const [profileRes, accessRes] = await Promise.all([
          supabase.from('profiles').select('*').eq('id', userId).single(),
          supabase.from('module_access').select('module').eq('user_id', userId)
        ]);

        if (profileRes.error) {
           console.warn('Profile fetch error:', profileRes.error);
           // Fallback to basic email if profile missing
           setProfile({ email: userEmail, full_name: 'User', stream: 'Not Set', college: 'Not Set' });
        } else {
           setProfile(profileRes.data);
        }

        if (!accessRes.error && accessRes.data) {
          setModules(accessRes.data.map((r: any) => r.module));
        }
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    if (userId) fetchAccountDetails();
  }, [userId, userEmail]);

  const handleLogout = async () => {
    await logout();
    onClose();
  };

  const handleSaveStream = async () => {
    if (!newStream) return;
    setLoading(true);
    try {
      const { error: updateError } = await supabase
        .from('profiles')
        .update({ stream: newStream })
        .eq('id', userId);
      
      if (updateError) throw updateError;
      
      setProfile({ ...profile, stream: newStream });
      setIsEditingStream(false);
      setSuccessMsg('Stream updated successfully!');
    } catch (err: any) {
      setError(err.message || 'Failed to update stream');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="account-modal-overlay" onClick={onClose}>
      <div className="account-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="account-header">
          <h2>Account Details</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        
        {loading ? (
          <div className="account-loading">Loading details...</div>
        ) : error ? (
          <div className="account-error">{error}</div>
        ) : (
          <div className="account-body">
            <div className="account-section">
              <div className="avatar">{profile?.full_name?.charAt(0).toUpperCase() || userEmail.charAt(0).toUpperCase()}</div>
              <div className="user-info">
                <h3>{profile?.full_name || 'Fonus Student'}</h3>
                <p>{profile?.email || userEmail}</p>
              </div>
            </div>

            <div className="details-grid">
              <div className="detail-item">
                <label>Organization / College</label>
                <div>{profile?.college || 'Not specified'}</div>
              </div>
              <div className="detail-item">
                <label>Selected Stream</label>
                {isEditingStream ? (
                  <div className="stream-edit-group">
                    <select 
                      value={newStream} 
                      onChange={e => setNewStream(e.target.value)}
                      className="stream-select"
                    >
                      <option value="" disabled>Select Your Stream</option>
                      <option value="B1.1 - Aeroplanes Turbine">B1.1 - Aeroplanes Turbine</option>
                      <option value="B1.2 - Aeroplanes Piston">B1.2 - Aeroplanes Piston</option>
                      <option value="B1.3 - Helicopters Turbine">B1.3 - Helicopters Turbine</option>
                      <option value="B1.4 - Helicopters Piston">B1.4 - Helicopters Piston</option>
                      <option value="B2 - Avionics">B2 - Avionics</option>
                      <option value="B3 - Piston Non-pressurized">B3 - Piston Non-pressurized</option>
                    </select>
                    <div className="stream-edit-actions">
                      <button className="save-btn" onClick={handleSaveStream}>Save</button>
                      <button className="cancel-btn" onClick={() => setIsEditingStream(false)}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div className="stream-display">
                    <span>{profile?.stream || 'Not selected'}</span>
                    <button className="edit-btn" onClick={() => {
                      setNewStream(profile?.stream || '');
                      setIsEditingStream(true);
                    }}>Edit</button>
                  </div>
                )}
              </div>
              <div className="detail-item">
                <label>Subscription Tier</label>
                <div style={{textTransform: 'capitalize'}}>{profile?.tier || 'Free'}</div>
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#172a6e', marginBottom: '0.5rem' }}>
                Unlocked Modules
              </div>
              {unlockedModules.length === 0 ? (
                <p style={{ fontSize: '0.72rem', color: '#9ca3af', fontFamily: 'system-ui, sans-serif' }}>
                  No modules unlocked yet. Use a promo code or upgrade to unlock.
                </p>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
                  {unlockedModules.map(mod => (
                    <span key={mod} style={{
                      background: 'linear-gradient(135deg, #172a6e, #213b93)',
                      color: '#e8b94f',
                      padding: '3px 10px',
                      borderRadius: '20px',
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      fontFamily: 'system-ui, sans-serif',
                      border: '1px solid rgba(232,185,79,0.3)'
                    }}>
                      {mod}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="account-actions">
              <button className="logout-btn" onClick={handleLogout}>Log Out</button>
            </div>
          </div>
        )}
      </div>

      <style dangerouslySetInnerHTML={{__html: `
        .account-modal-overlay {
          position: fixed;
          top: 0; left: 0; width: 100vw; height: 100vh;
          background: rgba(0, 0, 0, 0.4);
          backdrop-filter: blur(8px);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 9999;
          font-family: inherit;
        }

        .account-modal-content {
          background-color: #fff;
          border-radius: 16px;
          box-shadow: 0 14px 28px rgba(0,0,0,0.25);
          width: 480px;
          max-width: 95%;
          overflow: hidden;
          animation: slideUp 0.3s ease-out;
        }

        @keyframes slideUp {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }

        .account-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px 24px;
          border-bottom: 1px solid #e5e7eb;
          background: #f8fafc;
        }

        .account-header h2 {
          margin: 0;
          font-size: 1.25rem;
          color: #172a6e;
          font-weight: 700;
        }

        .close-btn {
          background: none;
          border: none;
          font-size: 1.5rem;
          color: #6b7280;
          cursor: pointer;
          line-height: 1;
        }

        .close-btn:hover { color: #172a6e; }

        .account-loading {
          padding: 40px;
          text-align: center;
          color: #6b7280;
        }

        .account-error {
          background: #dc2626;
          color: white;
          padding: 10px;
          margin: 0 20px;
          border-radius: 6px;
          font-weight: bold;
          font-size: 13px;
          text-align: center;
        }

        .account-success {
          background: #16a34a;
          color: white;
          padding: 10px;
          margin: 0 20px;
          border-radius: 6px;
          font-weight: bold;
          font-size: 13px;
          text-align: center;
        }

        .stream-display {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .edit-btn {
          background: none;
          border: none;
          color: #2563eb;
          cursor: pointer;
          font-size: 0.875rem;
        }

        .edit-btn:hover {
          text-decoration: underline;
        }

        .stream-edit-group {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-top: 4px;
        }

        .stream-select {
          width: 100%;
          padding: 8px;
          border: 1px solid #d1d5db;
          border-radius: 6px;
          font-size: 14px;
        }

        .stream-edit-actions {
          display: flex;
          gap: 8px;
        }

        .save-btn {
          background: #2563eb;
          color: white;
          border: none;
          padding: 4px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 13px;
        }

        .save-btn:hover {
          background: #1d4ed8;
        }

        .cancel-btn {
          background: #f3f4f6;
          color: #374151;
          border: 1px solid #d1d5db;
          padding: 4px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 13px;
        }

        .cancel-btn:hover {
          background: #e5e7eb;
        }

        .account-body {
          padding: 24px;
        }

        .account-section {
          display: flex;
          align-items: center;
          gap: 16px;
          margin-bottom: 24px;
        }

        .avatar {
          width: 56px;
          height: 56px;
          border-radius: 50%;
          background: #213b93;
          color: #fff;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.5rem;
          font-weight: bold;
        }

        .user-info h3 {
          margin: 0 0 4px;
          color: #1a1f3a;
          font-size: 1.1rem;
        }

        .user-info p {
          margin: 0;
          color: #6b7280;
          font-size: 0.9rem;
        }

        .details-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          margin-bottom: 24px;
        }

        .detail-item {
          background: #f8fafc;
          padding: 12px;
          border-radius: 8px;
          border: 1px solid #e5e7eb;
        }

        .detail-item label {
          display: block;
          font-size: 0.75rem;
          color: #6b7280;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 4px;
          font-weight: 600;
        }

        .detail-item div {
          color: #1a1f3a;
          font-weight: 500;
          font-size: 0.9rem;
        }

        .modules-section {
          margin-bottom: 32px;
        }

        .modules-section label {
          display: block;
          font-size: 0.85rem;
          color: #1a1f3a;
          margin-bottom: 12px;
          font-weight: 600;
        }

        .modules-list {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .module-badge {
          background: #eef2ff;
          color: #213b93;
          padding: 6px 12px;
          border-radius: 20px;
          font-size: 0.85rem;
          font-weight: 600;
          border: 1px solid #c7d2fe;
        }

        .no-modules {
          margin: 0;
          color: #9ca3af;
          font-size: 0.9rem;
          font-style: italic;
        }

        .account-actions {
          display: flex;
          justify-content: flex-end;
          border-top: 1px solid #e5e7eb;
          padding-top: 20px;
        }

        .logout-btn {
          background: #fff;
          color: #ef4444;
          border: 1px solid #fca5a5;
          padding: 8px 24px;
          border-radius: 8px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }

        .logout-btn:hover {
          background: #fef2f2;
          border-color: #ef4444;
        }
      `}} />
    </div>
  );
}
