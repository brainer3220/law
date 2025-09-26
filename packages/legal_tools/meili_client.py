"""Shared helpers for interacting with Meilisearch."""

from __future__ import annotations

import json
import os
from typing import Dict, Iterable, Optional
from urllib import error, request

DEFAULT_MEILI_URL_ENV: tuple[str, ...] = (
    "MEILI_HTTP_ADDR",
    "MEILI_URL",
    "MEILISEARCH_URL",
)
DEFAULT_MEILI_KEY_ENV: tuple[str, ...] = (
    "MEILI_SEARCH_KEY",
    "MEILI_MASTER_KEY",
    "MEILI_API_KEY",
    "MEILI_ADMIN_KEY",
)
DEFAULT_INDEX_ENV: tuple[str, ...] = (
    "MEILI_INDEX",
    "MEILI_INDEX_UID",
)


def first_env(keys: Iterable[str]) -> Optional[str]:
    """Return the first defined environment variable in ``keys``."""

    for key in keys:
        if value := os.getenv(str(key)):
            return value
    return None


def base_url() -> str:
    """Return the configured Meilisearch base URL or the local default."""

    return first_env(DEFAULT_MEILI_URL_ENV) or "http://localhost:7700"


def api_key() -> Optional[str]:
    """Return the configured Meilisearch API key, if any."""

    return first_env(DEFAULT_MEILI_KEY_ENV)


def resolve_index_uid(explicit: Optional[str] = None) -> str:
    """Return the target index UID, preferring explicit or environment values."""

    if explicit:
        return explicit
    return first_env(DEFAULT_INDEX_ENV) or "legal-docs"


def request_json(
    method: str,
    path: str,
    payload: Optional[Dict] = None,
    *,
    timeout: float = 10.0,
) -> Dict:
    """Perform an HTTP request against Meilisearch and parse the JSON response."""

    url = f"{base_url().rstrip('/')}{path}"
    headers = {"Content-Type": "application/json"}
    if key := api_key():
        headers["X-Meili-API-Key"] = key
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text) if text else {}
    except error.HTTPError as exc:  # pragma: no cover - network failure
        body = exc.read().decode("utf-8", "ignore")
        raise RuntimeError(
            f"Meilisearch {method} {path} failed: {exc.status} {body}"
        ) from exc
    except error.URLError as exc:  # pragma: no cover - network failure
        raise RuntimeError(
            f"Failed to reach Meilisearch at {url}: {exc.reason}"
        ) from exc


__all__ = [
    "DEFAULT_INDEX_ENV",
    "DEFAULT_MEILI_KEY_ENV",
    "DEFAULT_MEILI_URL_ENV",
    "api_key",
    "base_url",
    "first_env",
    "request_json",
    "resolve_index_uid",
]

