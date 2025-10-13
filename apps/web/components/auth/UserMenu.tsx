'use client';

import { useAuth } from '@/lib/auth/AuthContext';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export function UserMenu() {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  if (!user) {
    return null;
  }

  const initials = user.email?.[0]?.toUpperCase() ?? '?';

  const handleSignOut = async () => {
    setLoading(true);
    try {
      await signOut();
      router.push('/auth/login');
      router.refresh();
    } catch (error) {
      console.error('Error signing out:', error);
    } finally {
      setLoading(false);
      setIsOpen(false);
    }
  };

  return (
    <div className="material-user-menu">
      <button
        onClick={() => setIsOpen((open) => !open)}
        className="material-user-chip"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        type="button"
      >
        <span className="material-user-chip__avatar" aria-hidden="true">
          {initials}
        </span>
        <span className="material-user-chip__label">{user.email}</span>
      </button>

      {isOpen && (
        <>
          <div
            className="material-user-menu__scrim"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />
          <div className="material-user-menu__surface" role="menu">
            <div className="material-user-menu__headline">
              {user.user_metadata?.full_name || user.email}
            </div>
            <button
              type="button"
              onClick={handleSignOut}
              disabled={loading}
              className="material-user-menu__item"
            >
              {loading ? '로그아웃 중…' : '로그아웃'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}
