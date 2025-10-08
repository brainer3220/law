"""Integration tests for the sharing FastAPI application."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from packages.legal_tools.share import ShareSettings, create_app


def _create_client() -> TestClient:
    settings = ShareSettings(
        database_url="sqlite+pysqlite:///:memory:",
        external_base_url="https://share.test",
        default_link_ttl_days=7,
        token_bytes=8,
    )
    app = create_app(settings)
    return TestClient(app)


def test_share_flow_round_trip() -> None:
    client = _create_client()

    preview_payload = {
        "payloads": {
            "body": "연락처 test@example.com API 키 sk-abc1234567890",
        }
    }
    preview = client.post("/v1/redactions/preview", json=preview_payload)
    assert preview.status_code == 200
    data = preview.json()
    assert any(match["rule_id"] == "email" for match in data["matches"])
    assert any(match["rule_id"] == "api_key_like" for match in data["matches"])

    apply_payload = {
        "actor_id": "user-123",
        "resource": {
            "type": "conversation",
            "owner_id": "user-123",
            "org_id": "org-1",
            "title": "테스트 대화",
        },
        "payloads": preview_payload["payloads"],
    }
    applied = client.post("/v1/redactions/apply", json=apply_payload)
    assert applied.status_code == 200
    applied_data = applied.json()
    resource_id = applied_data["resource"]["id"]

    share_payload = {
        "resource_id": resource_id,
        "actor_id": "user-123",
        "mode": "unlisted",
        "allow_download": False,
        "allow_comments": True,
        "is_live": False,
        "create_link": True,
        "link_domain_whitelist": ["share.test"],
    }
    created = client.post("/v1/shares", json=share_payload)
    assert created.status_code == 200
    share_data = created.json()
    assert share_data["mode"] == "unlisted"
    assert share_data["links"], "Link should be created on share creation"
    share_id = share_data["id"]

    fetched = client.get(f"/v1/shares/{share_id}")
    assert fetched.status_code == 200
    fetched_data = fetched.json()
    assert fetched_data["id"] == share_id

    link_request = {"actor_id": "user-123", "domain_whitelist": ["share.test"]}
    new_link = client.post(f"/v1/shares/{share_id}/links", json=link_request)
    assert new_link.status_code == 200
    new_link_data = new_link.json()
    token = new_link_data["token"]
    assert re.match(r"^[A-Za-z0-9]+$", token)

    access = client.get(f"/v1/s/{token}")
    assert access.status_code == 200
    access_data = access.json()
    assert access_data["share"]["id"] == share_id

    permissions_payload = [
        {
            "resource_id": resource_id,
            "principal_type": "user",
            "principal_id": "viewer-1",
            "role": "viewer",
        }
    ]
    perm_resp = client.post("/v1/permissions/bulk", json=permissions_payload)
    assert perm_resp.status_code == 200
    assert perm_resp.json()[0]["principal_id"] == "viewer-1"

    audit = client.get("/v1/audit", params={"resource_id": resource_id})
    assert audit.status_code == 200
    audit_entries = audit.json()["results"]
    assert any(entry["action"] == "share.create" for entry in audit_entries)
    assert any(entry["action"] == "share.link.view" for entry in audit_entries)
