from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

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

