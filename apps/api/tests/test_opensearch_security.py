from __future__ import annotations

from law_shared.legal_tools import opensearch_search
from law_shared.legal_tools.opensearch_client import redact_url_credentials


def test_search_limit_is_clamped(monkeypatch):
    captured = {}

    def fake_request_json(method, path, payload):
        captured["payload"] = payload
        return {"hits": {"hits": []}}

    monkeypatch.setattr(opensearch_search, "request_json", fake_request_json)

    opensearch_search.search_opensearch("민법", limit=10_000)

    assert captured["payload"]["size"] == opensearch_search.MAX_OPENSEARCH_LIMIT


def test_opensearch_url_redacts_inline_credentials():
    redacted = redact_url_credentials("https://user:secret@example.com:9200/index")

    assert redacted == "https://example.com:9200/index"
    assert "secret" not in redacted
