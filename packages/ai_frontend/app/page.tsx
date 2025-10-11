'use client';

import '@material/web/button/filled-button.js';
import '@material/web/button/filled-tonal-button.js';
import '@material/web/progress/circular-progress.js';
import { useAuth } from '@/lib/auth/AuthContext';
import App from './App';
import SoftrHero from '@/components/SoftrHero';
import { useRouter } from 'next/navigation';
import {
  ArrowRightOnRectangleIcon,
  UserPlusIcon,
} from '@heroicons/react/24/outline';

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  if (loading) {
    return (
      <div className="material-screen">
        <md-circular-progress indeterminate aria-label="Loading session" />
        <p className="material-body">계정을 확인하는 중입니다…</p>
      </div>
    );
  }

  if (user) {
    return <App />;
  }

  return (
    <main className="material-landing">
      <div className="material-landing__bar">
        <div className="material-landing__brand">
          <span className="material-title">법률 AI 에이전트</span>
        </div>
        <div className="material-landing__actions">
          <md-filled-tonal-button
            type="button"
            onClick={() => router.push('/auth/login')}
          >
            <ArrowRightOnRectangleIcon slot="icon" className="material-icon" />
            로그인
          </md-filled-tonal-button>
          <md-filled-button
            type="button"
            onClick={() => router.push('/auth/signup')}
          >
            <UserPlusIcon slot="icon" className="material-icon" />
            회원가입
          </md-filled-button>
        </div>
      </div>
      <div className="material-landing__content">
        <SoftrHero />
      </div>
    </main>
  );
}
