/**
 * 법률 LLM 에이전트 컴포넌트 데모 페이지
 * 
 * 생성된 공유 UI 컴포넌트들의 사용 예시.
 */

"use client";

import { UserMenu } from "@/components/auth/UserMenu";
import { SearchBar } from "@/components/SearchBar";
import { EvidenceCard } from "@/components/EvidenceCard";
import { ClauseDiffCard } from "@/components/ClauseDiffCard";
import { RiskBadge } from "@/components/RiskBadge";
import { StatusBadge } from "@/components/StatusBadge";
import { CitationPopover } from "@/components/CitationPopover";
import { ClaimEvidenceMatrix } from "@/components/ClaimEvidenceMatrix";
import { PolicyViolationAlert } from "@/components/PolicyViolationAlert";
import { ProvenanceFooter } from "@/components/ProvenanceFooter";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import type {
  SearchFilter,
  EvidenceSource,
  ClauseDiff,
  Claim,
  ClaimEvidenceCell,
  PolicyViolation,
  Provenance,
} from "@/lib/types";

// 샘플 데이터
const sampleEvidence: EvidenceSource[] = [
  {
    id: "ev1",
    type: "statute",
    title: "민법",
    number: "제750조",
    snippet: "고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는 그 손해를 배상할 책임이 있다.",
    pinCite: "제750조",
    confidence: 0.95,
    date: "2024-01-01",
  },
  {
    id: "ev2",
    type: "case",
    title: "대법원 판례",
    number: "2020다12345",
    snippet: "불법행위로 인한 손해배상책임의 성립요건은 위법한 가해행위, 손해의 발생, 가해행위와 손해발생 사이의 인과관계이다.",
    confidence: 0.88,
    date: "2020-06-15",
  },
  {
    id: "ev3",
    type: "doc",
    title: "계약서 검토 의견",
    snippet: "면책조항은 민법상 과실책임 원칙과 충돌할 수 있으므로 신중한 검토가 필요합니다.",
    confidence: 0.75,
  },
];

const sampleDiff: ClauseDiff = {
  id: "diff1",
  before: "을은 계약 위반에 대해 어떠한 책임도 지지 않는다.",
  after: "을은 고의 또는 중과실로 인한 계약 위반에 대해서는 책임을 부담한다.",
  riskLevel: "medium",
  riskTags: ["면책조항", "과실책임"],
  citations: sampleEvidence.slice(0, 2),
  comments: "일방적 면책조항은 불공정약관으로 무효될 수 있습니다.",
};

const sampleClaims: Claim[] = [
  {
    id: "c1",
    text: "계약 당사자는 불법행위에 대해 손해배상책임을 진다.",
    paragraph: 1,
    evidenceIds: ["ev1", "ev2"],
    status: "verified",
    confidence: 0.92,
  },
  {
    id: "c2",
    text: "면책조항은 과실책임 원칙에 따라 제한적으로 해석되어야 한다.",
    paragraph: 2,
    evidenceIds: ["ev1", "ev3"],
    status: "verified",
    confidence: 0.78,
  },
  {
    id: "c3",
    text: "고의에 의한 손해는 면책 대상이 될 수 없다.",
    paragraph: 3,
    evidenceIds: ["ev1"],
    status: "unverified",
    confidence: 0.65,
  },
];

const sampleCells: ClaimEvidenceCell[] = [
  { claimId: "c1", evidenceId: "ev1", relevance: 0.95, isSupporting: true },
  { claimId: "c1", evidenceId: "ev2", relevance: 0.88, isSupporting: true },
  { claimId: "c1", evidenceId: "ev3", relevance: 0.45, isSupporting: true },
  { claimId: "c2", evidenceId: "ev1", relevance: 0.72, isSupporting: true },
  { claimId: "c2", evidenceId: "ev2", relevance: 0.55, isSupporting: true },
  { claimId: "c2", evidenceId: "ev3", relevance: 0.85, isSupporting: true },
  { claimId: "c3", evidenceId: "ev1", relevance: 0.82, isSupporting: true },
  { claimId: "c3", evidenceId: "ev2", relevance: 0.38, isSupporting: true },
];

const sampleViolations: PolicyViolation[] = [
  {
    id: "v1",
    type: "upl",
    severity: "high",
    message: "법률 자문으로 해석될 수 있는 표현이 감지되었습니다.",
    location: { paragraph: 5, start: 120, end: 180 },
    suggestion: "\"참고용이며 법률 자문이 아님\"을 명시하세요.",
    guideUrl: "https://example.com/guide/upl",
  },
  {
    id: "v2",
    type: "hallucination",
    severity: "medium",
    message: "인용 근거가 없는 주장이 포함되어 있습니다.",
    location: { paragraph: 3, start: 45, end: 98 },
    suggestion: "근거 자료를 추가하거나 주장을 삭제하세요.",
  },
];

const sampleProvenance: Provenance = {
  modelVersion: "gpt-4-turbo-2024-04-09",
  promptVersion: "v2.3.1",
  indexVersion: "idx-20240815",
  policyVersion: "policy-v1.2",
  corpusHash: "sha256:a3f8c9e2b1d4...",
  timestamp: new Date().toISOString(),
};

export default function ComponentsDemoPage() {
  const handleSearch = (filter: SearchFilter) => {
    console.log("Search:", filter);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8 dark:bg-slate-950">
      <div className="mx-auto max-w-7xl space-y-8">
        <header className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="mb-2 text-3xl font-bold text-gray-900 dark:text-gray-100">
              법률 LLM UI 컴포넌트 데모
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              공유 로직과 UI 컴포넌트의 사용 예시
            </p>
          </div>
          <UserMenu />
        </header>

        {/* Status Badges */}
        <section className="rounded-lg bg-white p-6 shadow dark:bg-slate-900">
          <h2 className="mb-4 text-xl font-bold text-gray-900 dark:text-gray-100">
            상태 뱃지
          </h2>
          <div className="flex flex-wrap gap-3">
            <StatusBadge status="draft" />
            <StatusBadge status="cite_check" />
            <StatusBadge status="policy_check" />
            <StatusBadge status="approved" />
            <RiskBadge level="high" />
            <RiskBadge level="medium" />
            <RiskBadge level="low" />
          </div>
        </section>

        {/* Search Bar */}
        <section className="rounded-lg bg-white p-6 shadow dark:bg-slate-900">
          <h2 className="mb-4 text-xl font-bold text-gray-900 dark:text-gray-100">
            검색 바
          </h2>
          <SearchBar onSearch={handleSearch} showFilters />
        </section>

        {/* Evidence Cards */}
        <section className="rounded-lg bg-white p-6 shadow dark:bg-slate-900">
          <h2 className="mb-4 text-xl font-bold text-gray-900 dark:text-gray-100">
            근거 카드
          </h2>
          <div className="space-y-4">
            {sampleEvidence.map((ev) => (
              <EvidenceCard key={ev.id} evidence={ev} />
            ))}
          </div>
        </section>

        {/* Citation Popover */}
        <section className="rounded-lg bg-white p-6 shadow dark:bg-slate-900">
          <h2 className="mb-4 text-xl font-bold text-gray-900 dark:text-gray-100">
            인용 팝오버
          </h2>
          <p className="text-gray-700 dark:text-gray-300">
            계약 당사자는{" "}
            <CitationPopover
              text="불법행위에 대해 손해배상책임을 진다"
              evidence={sampleEvidence.slice(0, 2)}
              status="verified"
            />
            . 이는 민법 제750조에 명시되어 있습니다.
          </p>
        </section>

        {/* Clause Diff Card */}
        <section className="rounded-lg bg-white p-6 shadow dark:bg-slate-900">
          <h2 className="mb-4 text-xl font-bold text-gray-900 dark:text-gray-100">
            조항 비교 카드
          </h2>
          <ClauseDiffCard
            diff={sampleDiff}
            onAccept={(id) => console.log("Accepted:", id)}
            onReject={(id) => console.log("Rejected:", id)}
            onRevise={(id) => console.log("Revise:", id)}
          />
        </section>

        {/* Claim-Evidence Matrix */}
        <section className="rounded-lg bg-white p-6 shadow dark:bg-slate-900">
          <h2 className="mb-4 text-xl font-bold text-gray-900 dark:text-gray-100">
            주장 × 근거 매트릭스
          </h2>
          <ClaimEvidenceMatrix
            claims={sampleClaims}
            evidence={sampleEvidence}
            cells={sampleCells}
            onCellClick={(claimId, evidenceId) =>
              console.log("Cell clicked:", claimId, evidenceId)
            }
          />
        </section>

        {/* Policy Violations */}
        <section className="rounded-lg bg-white p-6 shadow dark:bg-slate-900">
          <h2 className="mb-4 text-xl font-bold text-gray-900 dark:text-gray-100">
            정책 위반 알림
          </h2>
          <PolicyViolationAlert
            violations={sampleViolations}
            onResolve={(id) => console.log("Resolved:", id)}
            onViewGuide={(v) => console.log("View guide:", v)}
          />
        </section>

        {/* Loading Spinner */}
        <section className="rounded-lg bg-white p-6 shadow dark:bg-slate-900">
          <h2 className="mb-4 text-xl font-bold text-gray-900 dark:text-gray-100">
            로딩 스피너
          </h2>
          <div className="flex gap-8">
            <LoadingSpinner size="sm" label="작은 크기" />
            <LoadingSpinner size="md" label="중간 크기" />
            <LoadingSpinner size="lg" label="큰 크기" />
          </div>
        </section>

        {/* Provenance Footer */}
        <section className="overflow-hidden rounded-lg bg-white shadow dark:bg-slate-900">
          <div className="p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
              Provenance 푸터
            </h2>
          </div>
          <ProvenanceFooter
            provenance={sampleProvenance}
            auditId="audit-20241008-001"
          />
        </section>
      </div>
    </div>
  );
}
