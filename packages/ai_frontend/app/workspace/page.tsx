'use client'

import ProjectTimeline from '@/components/workspace/ProjectTimeline'
import { 
  CheckCircleIcon,
  LightBulbIcon,
} from '@heroicons/react/24/outline'
import { useWorkspaceLayout } from './layout'

export default function WorkspacePage() {
  const {
    projects,
    projectsLoading,
    projectsError,
    requestUserId,
  } = useWorkspaceLayout()

  return (
    <>
      <section className="material-workspace__surface">
        <div className="material-workspace__surface-header">
          <div className="material-workspace__status">
            <CheckCircleIcon className="material-icon" aria-hidden="true" />
            <span className="material-caption">On track</span>
          </div>
        </div>
        <ProjectTimeline
          projects={projects}
          loading={projectsLoading}
          error={projectsError}
          userId={requestUserId}
        />
      </section>

      <aside className="material-workspace__sidebar">
        <div className="material-workspace__hint">
          <div className="material-workspace__hint-icon">
            <LightBulbIcon className="material-icon" aria-hidden="true" />
          </div>
          <div className="material-workspace__hint-content">
            <h3 className="material-caption material-workspace__hint-title">
              프로젝트 기반 작업
            </h3>
            <p className="material-body material-workspace__hint-body">
              각 프로젝트는 독립적인 컨텍스트와 지침 버전 이력을 관리하며, 정책 변경 사항을 추적합니다.
            </p>
          </div>
        </div>

        <div className="material-workspace__quick-tips">
          <h4 className="material-workspace__tips-title">빠른 팁</h4>
          <ul className="material-workspace__tips-list">
            <li>
              <span className="material-workspace__tip-emoji">📋</span>
              <span>프로젝트를 클릭하여 상세 정보 확인</span>
            </li>
            <li>
              <span className="material-workspace__tip-emoji">✏️</span>
              <span>업데이트로 진행 상황 기록</span>
            </li>
            <li>
              <span className="material-workspace__tip-emoji">👥</span>
              <span>팀원 초대로 협업 시작</span>
            </li>
          </ul>
        </div>
      </aside>
    </>
  )
}
