"""Shared helpers for interacting with OpenSearch."""

from __future__ import annotations

import base64
import json
import os
from typing import Dict, Iterable, Optional, Tuple
from urllib import error, request

DEFAULT_URL_ENV: tuple[str, ...] = (
    "LAW_OPENSEARCH_URL",
    "OPENSEARCH_URL",
    "OS_URL",
    "OPENSEARCH_HOST",
    "LAW_SEARCH_URL",
)
DEFAULT_API_KEY_ENV: tuple[str, ...] = (
    "LAW_OPENSEARCH_API_KEY",
    "OPENSEARCH_API_KEY",
)
DEFAULT_USERNAME_ENV: tuple[str, ...] = (
    "LAW_OPENSEARCH_USERNAME",
    "LAW_OPENSEARCH_USER",
    "OPENSEARCH_USERNAME",
    "OPENSEARCH_USER",
)
DEFAULT_PASSWORD_ENV: tuple[str, ...] = (
    "LAW_OPENSEARCH_PASSWORD",
    "OPENSEARCH_PASSWORD",
    "OPENSEARCH_PASS",
)
DEFAULT_INDEX_ENV: tuple[str, ...] = (
    "LAW_OPENSEARCH_INDEX",
    "OPENSEARCH_INDEX",
    "OPENSEARCH_INDEX_NAME",
    # Fallback to legacy Meilisearch variables for backwards compatibility
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
    """Return the configured OpenSearch base URL or the local default."""

    return first_env(DEFAULT_URL_ENV) or "http://localhost:9200"


def api_key() -> Optional[str]:
    """Return the configured OpenSearch API key, if any."""

    return first_env(DEFAULT_API_KEY_ENV)


def basic_auth() -> Tuple[Optional[str], Optional[str]]:
    """Return HTTP basic auth credentials if configured."""

    return first_env(DEFAULT_USERNAME_ENV), first_env(DEFAULT_PASSWORD_ENV)


def resolve_index_name(explicit: Optional[str] = None) -> str:
    """Return the target OpenSearch index name."""

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
    """Perform an HTTP request against OpenSearch and parse the JSON response."""

    url = f"{base_url().rstrip('/')}{path}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if key := api_key():
        headers["Authorization"] = f"ApiKey {key}"
    else:
        username, password = basic_auth()
        if username:
            token = base64.b64encode(f"{username}:{password or ''}".encode("utf-8"))
            headers["Authorization"] = f"Basic {token.decode('ascii')}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text) if text else {}
    except error.HTTPError as exc:  # pragma: no cover - network failure
        body = exc.read().decode("utf-8", "ignore")
        status = getattr(exc, "code", None) or getattr(exc, "status", "")
        raise RuntimeError(
            f"OpenSearch {method} {path} failed: {status} {body}"
        ) from exc
    except error.URLError as exc:  # pragma: no cover - network failure
        raise RuntimeError(
            f"Failed to reach OpenSearch at {url}: {exc.reason}"
        ) from exc


__all__ = [
    "DEFAULT_API_KEY_ENV",
    "DEFAULT_INDEX_ENV",
    "DEFAULT_PASSWORD_ENV",
    "DEFAULT_URL_ENV",
    "DEFAULT_USERNAME_ENV",
    "api_key",
    "base_url",
    "basic_auth",
    "first_env",
    "request_json",
    "resolve_index_name",
]

