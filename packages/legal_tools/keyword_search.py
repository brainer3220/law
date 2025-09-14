from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class KeywordResult:
    path: Path
    doc_id: str
    title: str
    snippet: str
    score: float


def search_files(query: str, *, limit: int, data_dir: Path) -> List[KeywordResult]:
    """Naïve keyword search over local JSON documents.

    Each JSON file is expected to contain the schema produced by importer scripts
    (``{"info": {"doc_id", "title"}, "taskinfo": {"sentences": [...]}}``).
    The search checks that all whitespace-separated query tokens appear in the
    concatenated title+sentences text.
    """
    tokens = [t for t in re.split(r"\s+", query.lower().strip()) if t]
    if not tokens:
        return []

    hits: List[KeywordResult] = []
    for p in sorted(data_dir.rglob("*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        title = str(obj.get("info", {}).get("title", ""))
        sentences = obj.get("taskinfo", {}).get("sentences", []) or []
        body = " ".join(sentences)
        text = f"{title} {body}".strip()
        low = text.lower()
        if all(tok in low for tok in tokens):
            first_pos = min((low.index(tok) for tok in tokens if tok in low), default=0)
            start = max(0, first_pos - 40)
            end = min(len(text), first_pos + 40)
            snippet = text[start:end].strip()
            score = float(sum(low.count(tok) for tok in tokens))
            doc_id = str(obj.get("info", {}).get("doc_id", ""))
            hits.append(KeywordResult(path=p, doc_id=doc_id, title=title, snippet=snippet, score=score))
            if len(hits) >= limit:
                break
    hits.sort(key=lambda h: -h.score)
    return hits
