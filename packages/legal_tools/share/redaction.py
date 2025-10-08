"""Redaction pipeline for masking sensitive information."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, MutableMapping, Sequence

from pydantic import BaseModel

__all__ = [
    "RedactionRule",
    "RedactionMatch",
    "RedactionPreview",
    "RedactionEngine",
]


@dataclass(slots=True, frozen=True)
class RedactionRule:
    """Regular-expression-based rule to detect sensitive patterns."""

    id: str
    pattern: re.Pattern[str]
    replacement: str = "****"
    description: str | None = None


class RedactionMatch(BaseModel):
    """Single redaction match within a payload field."""

    field: str
    start: int
    end: int
    value: str
    rule_id: str
    replacement: str


class RedactionPreview(BaseModel):
    """Preview of redaction results."""

    redacted: Dict[str, str]
    matches: List[RedactionMatch]


class RedactionEngine:
    """Apply a set of regex rules to redact payloads."""

    def __init__(self, rules: Sequence[RedactionRule] | None = None):
        if rules is None:
            rules = self._default_rules()
        self.rules: List[RedactionRule] = list(rules)

    def preview(self, payloads: Mapping[str, str]) -> RedactionPreview:
        """Return redacted payloads without mutating input."""

        redacted: MutableMapping[str, str] = dict(payloads)
        matches: List[RedactionMatch] = []
        for field, value in payloads.items():
            updated_value, field_matches = self._apply_rules(field, value)
            redacted[field] = updated_value
            matches.extend(field_matches)
        return RedactionPreview(redacted=dict(redacted), matches=matches)

    # ---------------------------- internals ----------------------------
    def _apply_rules(self, field: str, text: str) -> tuple[str, List[RedactionMatch]]:
        updated = text
        matches: List[RedactionMatch] = []
        for rule in self.rules:
            for match in rule.pattern.finditer(text):
                replacement = rule.replacement
                updated = updated.replace(match.group(0), replacement)
                matches.append(
                    RedactionMatch(
                        field=field,
                        start=match.start(),
                        end=match.end(),
                        value=match.group(0),
                        rule_id=rule.id,
                        replacement=replacement,
                    )
                )
        return updated, matches

    @staticmethod
    def _default_rules() -> List[RedactionRule]:
        patterns: Iterable[tuple[str, str, str]] = [
            ("api_key_like", r"\b(?:sk|ghp|AKIA)[A-Za-z0-9_-]{12,}\b", "****"),
            ("email", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "***@***"),
            (
                "phone",
                r"(?:(?:\+82|0)[- ]?)?(?:\d{2,3}[- ]?\d{3,4}[- ]?\d{4})",
                "***-****-****",
            ),
            ("resident_id", r"\b\d{6}-[1-4]\d{6}\b", "******-*******"),
        ]
        return [
            RedactionRule(
                id=rule_id, pattern=re.compile(pattern), replacement=replacement
            )
            for rule_id, pattern, replacement in patterns
        ]
