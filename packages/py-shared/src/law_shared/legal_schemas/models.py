from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    statute = "statute"
    case = "case"
    contract = "contract"
    document = "document"


class Anchor(BaseModel):
    """Pin-cite style anchors within a source.

    Examples:
      - statute: article_no, paragraph_no, subparagraph_no
      - case: section name + paragraph no
      - contract: clause path like 10.2(a)
    """

    article_no: Optional[str] = None
    paragraph_no: Optional[str] = None
    subparagraph_no: Optional[str] = None
    section_label: Optional[str] = None
    page_para: Optional[str] = None


class Document(BaseModel):
    """Canonical document container.

    Keep minimal but sufficient to support hierarchy + provenance.
    """

    doc_id: str
    title: str
    source_type: SourceType
    version: Optional[str] = None
    language: str = Field(default="ko-KR")
    source_uri: Optional[str] = None
    jurisdiction: Optional[str] = None
    court: Optional[str] = None
    statute_id: Optional[str] = None
    case_id: Optional[str] = None
    docket_no: Optional[str] = None
    date_effective: Optional[str] = None
    date_decision: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)


class Section(BaseModel):
    section_id: str
    doc_id: str
    headings_path: List[str] = Field(default_factory=list)
    title: Optional[str] = None
    order: Optional[int] = None
    anchor: Optional[Anchor] = None
    text: str
    # Optional context fields populated by enrichment
    section_synopsis: Optional[str] = None


class Chunk(BaseModel):
    chunk_id: str
    section_id: str
    doc_id: str
    order: int
    anchor: Optional[Anchor] = None
    # Raw text for quoting/citation
    chunk_text: str
    # Enriched content used only for embedding
    contextualized_text: Optional[str] = None
    # Retrieval helpers
    headings_path: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    normalized_citations: List[str] = Field(default_factory=list)


class ClaimVerificationStatus(str, Enum):
    verified = "verified"
    partial = "partial"
    stale = "stale"
    unavailable = "unavailable"


class FreshnessStatus(str, Enum):
    current = "current"
    stale = "stale"
    unknown = "unknown"


class AnswerState(str, Enum):
    answer_ready = "answer-ready"
    answer_limited = "answer-limited"
    refusal_with_next_step = "refusal-with-next-step"
    system_error = "system-error"


class NextStepType(str, Enum):
    query = "query"
    source = "source"
    note = "note"


class VerificationEvidence(BaseModel):
    id: str
    type: Literal["statute", "case", "doc"]
    title: str
    number: Optional[str] = None
    pinCite: Optional[str] = None
    snippet: str
    url: Optional[str] = None
    confidence: Optional[float] = None
    verificationStatus: ClaimVerificationStatus = ClaimVerificationStatus.verified
    freshnessStatus: FreshnessStatus = FreshnessStatus.unknown
    date: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VerificationClaim(BaseModel):
    id: str
    text: str
    citationIndices: List[int] = Field(default_factory=list)
    evidenceIds: List[str] = Field(default_factory=list)
    status: ClaimVerificationStatus
    freshnessStatus: FreshnessStatus = FreshnessStatus.unknown
    unsupportedReasons: List[str] = Field(default_factory=list)


class NextStep(BaseModel):
    type: NextStepType
    label: str
    value: str


class VerificationProvenance(BaseModel):
    retrievalMethod: str
    verifierVersion: str
    modelVersion: Optional[str] = None
    promptVersion: Optional[str] = None
    indexVersion: Optional[str] = None
    policyVersion: Optional[str] = None
    timestamp: str
    queries: List[str] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)


class LegalAnswerPayload(BaseModel):
    answerState: AnswerState
    answer: Optional[str] = None
    reason: Optional[str] = None
    missingEvidence: List[str] = Field(default_factory=list)
    nextSteps: List[NextStep] = Field(default_factory=list)
    claims: List[VerificationClaim] = Field(default_factory=list)
    evidence: List[VerificationEvidence] = Field(default_factory=list)
    provenance: VerificationProvenance
