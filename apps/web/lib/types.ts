/**
 * 법률 LLM 에이전트 - 공용 타입 정의
 */

/**
 * 근거 타입 (법령/판례/문서)
 */
export type EvidenceType = "statute" | "case" | "doc";

/**
 * 위험도 레벨
 */
export type RiskLevel = "high" | "medium" | "low";

/**
 * 인용 검증 상태
 */
export type CitationStatus = "unverified" | "verified" | "error";

/**
 * 법률 도메인
 */
export type LegalDomain = "civil" | "criminal" | "administrative" | "ip";

/**
 * 근거 소스
 */
export interface EvidenceSource {
  id: string;
  type: EvidenceType;
  title: string;
  number?: string; // 법령 번호 또는 사건 번호
  snippet: string; // 관련 스니펫
  pinCite?: string; // 예: "제10조 제2항"
  url?: string; // 원문 URL
  date?: string; // 공포일 또는 선고일
  confidence?: number; // 0-1 사이 신뢰도
}

/**
 * 조항 비교 (Diff)
 */
export interface ClauseDiff {
  id: string;
  before: string;
  after: string;
  riskLevel: RiskLevel;
  riskTags: string[];
  citations: EvidenceSource[];
  comments?: string;
}

/**
 * 주장 (Claim)
 */
export interface Claim {
  id: string;
  text: string;
  paragraph: number;
  evidenceIds: string[]; // 연결된 근거 ID 목록
  status: CitationStatus;
  confidence?: number;
}

/**
 * 주장 × 근거 매트릭스 셀
 */
export interface ClaimEvidenceCell {
  claimId: string;
  evidenceId: string;
  relevance: number; // 0-1 사이 관련도
  isSupporting: boolean; // 주장을 뒷받침하는가
}

/**
 * 검색 필터
 */
export interface SearchFilter {
  query: string;
  domain?: LegalDomain;
  corpus?: EvidenceType[];
  dateFrom?: string;
  dateTo?: string;
  caseNumber?: string;
}

/**
 * 정책 위반
 */
export interface PolicyViolation {
  id: string;
  type: "upl" | "privacy" | "scope" | "hallucination";
  severity: RiskLevel;
  message: string;
  location?: {
    paragraph: number;
    start: number;
    end: number;
  };
  suggestion?: string;
  guideUrl?: string;
}

/**
 * Provenance (출처 정보)
 */
export interface Provenance {
  modelVersion: string;
  promptVersion: string;
  indexVersion: string;
  policyVersion: string;
  corpusHash?: string;
  timestamp: string;
}
