"""Lexical utilities for BM25-based retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Set, Tuple

__all__ = [
    "LexicalVariant",
    "normalize_token",
    "tokenize",
    "expand_with_synonyms",
    "build_query_variants",
]


# Synonym inventory keyed by normalized token.
_SYNONYM_MAP: Dict[str, Set[str]] = {
    "손해배상": {"배상", "손배", "손해보상"},
    "위반": {"위배", "저촉"},
    "해지": {"종료", "계약해지", "계약종료"},
    "근로자": {"노동자", "근로"},
    "사용자": {"회사", "사업주"},
    "임대차": {"전세", "임차", "렌트"},
    "가압류": {"압류", "보전처분"},
    "과태료": {"벌금", "행정벌"},
    "처분": {"제재", "징계"},
    "무효": {"취소", "효력없음"},
    "취업규칙": {"사규", "근로규칙"},
    "퇴직금": {"퇴직수당", "퇴직"},
    "손해": {"피해", "손실"},
    "재산": {"자산", "재산권"},
    "파산": {"도산", "회생"},
    "징계": {"징계처분", "징벌"},
    "부당해고": {"해고", "해고무효"},
}

_TOKEN_PATTERN = re.compile(r"[0-9A-Za-z]+|[가-힣]+")
_SUFFIXES = [
    "으로부터",
    "으로써",
    "으로서",
    "에게서",
    "로부터",
    "처럼",
    "같이",
    "만큼",
    "보다도",
    "보다가",
    "보다",
    "부터",
    "까지",
    "에게",
    "께서",
    "에서",
    "에는",
    "에도",
    "에게는",
    "에게도",
    "으로",
    "로",
    "와는",
    "와도",
    "과는",
    "과도",
    "만은",
    "만도",
    "만",
    "와",
    "과",
    "랑",
    "에",
    "이",
    "가",
    "은",
    "는",
    "을",
    "를",
    "의",
]


def tokenize(text: str) -> List[str]:
    """Split text into coarse tokens for normalization."""

    return _TOKEN_PATTERN.findall(text or "")


def _strip_suffix(token: str) -> str:
    for suffix in _SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix) + 1:
            return token[: -len(suffix)]
    return token


def normalize_token(token: str) -> str:
    token = token.strip().strip('"“”‘’').lower()
    token = re.sub(r"[·・‧]", "", token)
    token = re.sub(r"[\-_/]+", "", token)
    token = _strip_suffix(token)
    return token


def expand_with_synonyms(words: Iterable[str]) -> List[str]:
    """Return normalized words plus synonym expansions."""

    out: List[str] = []
    seen: Set[str] = set()
    for word in words:
        for token in tokenize(word):
            norm = normalize_token(token)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            out.append(norm)
            for syn in sorted(_SYNONYM_MAP.get(norm, set())):
                if syn not in seen:
                    seen.add(syn)
                    out.append(syn)
    return out


def _identifier_terms(tokens: Sequence[str]) -> List[str]:
    ident: List[str] = []
    for tok in tokens:
        if re.fullmatch(r"\d{3,}", tok):
            ident.append(tok)
        elif re.fullmatch(r"\d{2,}[가-힣]", tok):
            ident.append(tok)
        elif re.fullmatch(r"[가-힣]{2,}\d{2,}", tok):
            ident.append(tok)
    return ident


def _phrase(tokens: Sequence[str]) -> str | None:
    if len(tokens) >= 2:
        return '"' + " ".join(tokens) + '"'
    return None


@dataclass(frozen=True)
class LexicalVariant:
    name: str
    query: str
    fields: Tuple[str, ...] = ("title", "body")
    boost: float = 1.0


def build_query_variants(query: str) -> List[LexicalVariant]:
    """Generate search variants for BM25 queries."""

    raw_tokens = [normalize_token(t) for t in tokenize(query)]
    tokens = [t for t in raw_tokens if t]
    if not tokens:
        return []

    # Base variant uses normalized tokens and searches across title/body.
    base_query = " ".join(tokens)
    variants: List[LexicalVariant] = [
        LexicalVariant(name="base", query=base_query, fields=("title", "body"), boost=1.0)
    ]

    # Title-focused view to emphasize short legal document headings.
    variants.append(LexicalVariant(name="title", query=base_query, fields=("title",), boost=1.25))

    # Synonym expansion to increase recall while keeping a modest boost.
    expanded = expand_with_synonyms(tokens)
    if expanded and len(expanded) > len(tokens):
        variants.append(
            LexicalVariant(
                name="synonym",
                query=" ".join(expanded),
                fields=("title", "body"),
                boost=0.9,
            )
        )

    identifiers = _identifier_terms(tokens)
    if identifiers:
        variants.append(
            LexicalVariant(
                name="identifier",
                query=" ".join(identifiers),
                fields=("title", "body"),
                boost=1.1,
            )
        )

    phrase = _phrase(tokens)
    if phrase:
        variants.append(
            LexicalVariant(
                name="phrase",
                query=f"{base_query} {phrase}",
                fields=("body", "title"),
                boost=0.85,
            )
        )

    # Deduplicate by name to guard against accidental duplicates in future edits.
    seen_names: Set[str] = set()
    unique_variants: List[LexicalVariant] = []
    for variant in variants:
        if variant.name in seen_names:
            continue
        seen_names.add(variant.name)
        unique_variants.append(variant)
    return unique_variants

