'use client';

import { useAuth } from '@/lib/auth/AuthContext';
import App from './App';
import SoftrHero from '@/components/SoftrHero';
import { useRouter } from 'next/navigation';
import {
  ArrowRightOnRectangleIcon,
  UserPlusIcon,
  SparklesIcon,
  ShieldCheckIcon,
  BoltIcon,
  DocumentMagnifyingGlassIcon,
} from '@heroicons/react/24/outline';

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  if (loading) {
    return (
      <div className="material-screen">
        <div className="material-loading">
          <div className="material-loading__spinner">
            <div className="spinner-ring"></div>
          </div>
          <p className="material-body">계정을 확인하는 중입니다…</p>
        </div>
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
          <SparklesIcon className="material-landing__brand-icon" aria-hidden="true" />
          <span className="material-title material-landing__brand-text">법률 AI 에이전트</span>
        </div>
        <div className="material-landing__actions">
          <button
            type="button"
            onClick={() => router.push('/auth/login')}
            className="material-filled-button material-filled-button--tonal"
          >
            <ArrowRightOnRectangleIcon className="material-icon" aria-hidden="true" />
            <span>로그인</span>
          </button>
          <button
            type="button"
            onClick={() => router.push('/auth/signup')}
            className="material-filled-button"
          >
            <UserPlusIcon className="material-icon" aria-hidden="true" />
            <span>회원가입</span>
          </button>
        </div>
      </div>

      <div className="material-landing__content">
        <section className="material-landing__hero">
          <div className="material-landing__hero-content">
            <h1 className="material-landing__hero-title">
              AI 기반 법률 지원
              <span className="material-landing__hero-highlight">
                더 빠르고 정확하게
              </span>
            </h1>
            <p className="material-landing__hero-description">
              최신 AI 기술로 법률 문서 분석, 판례 검색, 계약서 검토를 지원합니다.
              전문가 수준의 법률 인사이트를 빠르게 제공받으세요.
            </p>
            <div className="material-landing__hero-actions">
              <button
                type="button"
                onClick={() => router.push('/auth/signup')}
                className="material-filled-button material-landing__hero-cta"
              >
                <span>무료로 시작하기</span>
                <svg className="material-icon" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </button>
              <button
                type="button"
                onClick={() => {
                  document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
                }}
                className="material-outlined-button"
              >
                <span>기능 둘러보기</span>
              </button>
            </div>
          </div>
          <div className="material-landing__hero-visual">
            <div className="material-landing__hero-card material-landing__hero-card--1">
              <ShieldCheckIcon className="material-landing__feature-icon" aria-hidden="true" />
              <span>안전한 데이터 보호</span>
            </div>
            <div className="material-landing__hero-card material-landing__hero-card--2">
              <BoltIcon className="material-landing__feature-icon" aria-hidden="true" />
              <span>실시간 분석</span>
            </div>
            <div className="material-landing__hero-card material-landing__hero-card--3">
              <DocumentMagnifyingGlassIcon className="material-landing__feature-icon" aria-hidden="true" />
              <span>정확한 판례 검색</span>
            </div>
          </div>
        </section>

        <section id="features" className="material-landing__features">
          <SoftrHero />
        </section>
      </div>
    </main>
  );
}
