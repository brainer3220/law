"""
Public schemas for legal documents, sections, and chunks.

These models are intentionally minimal and Pydantic v2-compatible.
They capture IDs, hierarchy, provenance, anchors, and text fields
required by the contextual RAG pipeline.
"""

from .models import (
    Anchor,
    AnswerState,
    Chunk,
    ClaimVerificationStatus,
    Document,
    FreshnessStatus,
    LegalAnswerPayload,
    NextStep,
    NextStepType,
    Section,
    SourceType,
    VerificationClaim,
    VerificationEvidence,
    VerificationProvenance,
)

__all__ = [
    "Anchor",
    "AnswerState",
    "Chunk",
    "ClaimVerificationStatus",
    "Document",
    "FreshnessStatus",
    "LegalAnswerPayload",
    "NextStep",
    "NextStepType",
    "Section",
    "SourceType",
    "VerificationClaim",
    "VerificationEvidence",
    "VerificationProvenance",
]
