from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
import time

from law_shared.legal_tools.file_store import (
    append_failure,
    ensure_layout,
    load_sync_state,
    save_snapshot,
    save_sync_state,
    sanitize_token,
    utc_now,
    utc_now_iso,
)
from law_shared.legal_tools.law_go_kr import (
    LawInterpretationResult,
    LawSearchResult,
    fetch_law_detail,
    fetch_law_interpretation,
    search_law,
    search_law_interpretations,
)

SourceType = Literal["statute", "interpretation"]


def sync_source(
    *,
    source_type: SourceType,
    data_dir: Path,
    query: Optional[str] = None,
    start_page: int = 1,
    max_pages: int = 1,
    display: int = 100,
    timeout: float = 10.0,
    sleep_seconds: float = 0.0,
) -> Dict[str, Any]:
    if max_pages < 1:
        raise ValueError("max_pages must be >= 1")
    if display < 1:
        raise ValueError("display must be >= 1")

    ensure_layout(data_dir)
    state = load_sync_state(data_dir)
    source_state = state.setdefault("sources", {}).setdefault(source_type, {})

    now = utc_now()
    run_started_at = utc_now_iso()
    saved_count = 0
    failed_count = 0
    scanned_count = 0
    pages_scanned = 0
    current_page = max(1, int(start_page))

    for _ in range(max_pages):
        pages_scanned += 1
        if source_type == "statute":
            response = search_law(
                query=query,
                page=current_page,
                display=min(100, int(display)),
                timeout=timeout,
            )
            items = response.results
        else:
            response = search_law_interpretations(
                query=query,
                page=current_page,
                display=min(100, int(display)),
                timeout=timeout,
            )
            items = response.results

        if not items:
            break

        for item in items:
            scanned_count += 1
            try:
                if source_type == "statute":
                    saved = _sync_statute_item(item=item, data_dir=data_dir, collected_at=now)
                else:
                    saved = _sync_interpretation_item(
                        item=item,
                        data_dir=data_dir,
                        collected_at=now,
                    )
                if saved:
                    saved_count += 1
            except Exception as exc:
                failed_count += 1
                append_failure(
                    data_dir,
                    {
                        "source_type": source_type,
                        "source_id": _item_source_id(item),
                        "query": query,
                        "page": current_page,
                        "error": str(exc),
                        "failed_at": utc_now_iso(),
                    },
                )

        current_page += 1
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    source_state.update(
        {
            "last_started_at": run_started_at,
            "last_completed_at": utc_now_iso(),
            "last_query": query,
            "last_start_page": start_page,
            "last_next_page_hint": current_page,
            "last_pages_scanned": pages_scanned,
            "last_scanned_count": scanned_count,
            "last_saved_count": saved_count,
            "last_failed_count": failed_count,
            "strategy": "manual_sync_snapshot",
        }
    )
    save_sync_state(data_dir, state)

    return {
        "source_type": source_type,
        "query": query,
        "pages_scanned": pages_scanned,
        "scanned_count": scanned_count,
        "saved_count": saved_count,
        "failed_count": failed_count,
        "next_page_hint": current_page,
    }


def _item_source_id(item: LawSearchResult | LawInterpretationResult) -> str:
    if isinstance(item, LawSearchResult):
        return str(item.law_id or item.serial_number or "unknown")
    return str(item.serial_no or item.case_no or "unknown")


def _version_for_statute(item: LawSearchResult, detail: Dict[str, Any]) -> str:
    parts: List[str] = []
    promulgation_date = detail.get("promulgation_date") or item.promulgation_date
    if promulgation_date:
        parts.append(sanitize_token(str(promulgation_date)))
    promulgation_number = detail.get("promulgation_number") or item.promulgation_number
    if promulgation_number:
        parts.append(sanitize_token(str(promulgation_number)))
    enforcement_date = detail.get("enforcement_date") or item.enforcement_date
    if enforcement_date:
        parts.append(sanitize_token(str(enforcement_date)))
    if not parts:
        parts.append("snapshot")
    return "-".join(parts)


def _version_for_interpretation(item: LawInterpretationResult, detail: Dict[str, Any]) -> str:
    parts: List[str] = []
    if detail.get("interpretation_date"):
        parts.append(sanitize_token(str(detail["interpretation_date"])))
    if item.reply_date:
        parts.append(sanitize_token(str(item.reply_date)))
    if item.case_no:
        parts.append(sanitize_token(str(item.case_no)))
    if not parts:
        parts.append("snapshot")
    return "-".join(parts)


def _sync_statute_item(*, item: LawSearchResult, data_dir: Path, collected_at: datetime) -> bool:
    source_id = str(item.law_id or item.serial_number or "unknown")
    detail = fetch_law_detail(law_id=item.law_id)
    detail_payload = asdict(detail)
    version = _version_for_statute(item, detail_payload)
    payload: Dict[str, Any] = {
        "source_type": "statute",
        "source_id": source_id,
        "version": version,
        "collected_at": collected_at.replace(microsecond=0).isoformat() + "Z",
        "search_result": asdict(item),
        "detail": detail_payload,
    }
    save_snapshot(
        data_dir=data_dir,
        source_type="statute",
        source_id=source_id,
        version=version,
        payload=payload,
        collected_at=collected_at,
    )
    return True


def _sync_interpretation_item(
    *,
    item: LawInterpretationResult,
    data_dir: Path,
    collected_at: datetime,
) -> bool:
    source_id = str(item.serial_no or item.case_no or "unknown")
    detail = fetch_law_interpretation(interpretation_id=item.serial_no)
    detail_payload = asdict(detail)
    version = _version_for_interpretation(item, detail_payload)
    payload: Dict[str, Any] = {
        "source_type": "interpretation",
        "source_id": source_id,
        "version": version,
        "collected_at": collected_at.replace(microsecond=0).isoformat() + "Z",
        "search_result": asdict(item),
        "detail": detail_payload,
    }
    save_snapshot(
        data_dir=data_dir,
        source_type="interpretation",
        source_id=source_id,
        version=version,
        payload=payload,
        collected_at=collected_at,
    )
    return True
