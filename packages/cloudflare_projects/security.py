from __future__ import annotations

import base64
import hmac
import ipaddress
import json
from hashlib import sha256
from typing import Iterable, Mapping

from .config import CloudflareProjectsConfig


def verify_zero_trust_token(token: str, cfg: CloudflareProjectsConfig) -> bool:
    """Validate the audience claim of a Zero Trust JWT.

    Signature verification should be handled upstream (e.g., Workers JWKS cache).
    This helper ensures the decoded payload contains an allowed `aud` entry.
    """

    if not token or not cfg.security.zero_trust_aud:
        return True

    try:
        parts = token.split(".")
        if len(parts) != 3:
            return False
        payload_segment = parts[1] + "=" * (-len(parts[1]) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_segment)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return False

    audience = payload.get("aud")
    if isinstance(audience, str):
        audience = [audience]
    if not isinstance(audience, Iterable):
        return False

    allowed = set(cfg.security.zero_trust_aud)
    return any(aud in allowed for aud in audience)


def verify_webhook_signature(
    *,
    headers: Mapping[str, str],
    body: bytes,
    cfg: CloudflareProjectsConfig,
) -> bool:
    secret = cfg.security.webhook_secret
    if not secret:
        return True

    header_name = cfg.security.webhook_signature_header
    provided = headers.get(header_name)
    if not provided:
        return False

    expected = hmac.new(secret.encode("utf-8"), body, sha256).hexdigest()
    return hmac.compare_digest(provided, expected)


def is_trusted_ip(ip: str, cfg: CloudflareProjectsConfig) -> bool:
    if not cfg.security.trusted_ip_ranges:
        return True

    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False

    for cidr in cfg.security.trusted_ip_ranges:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            continue
        if addr in network:
            return True
    return False


__all__ = ["is_trusted_ip", "verify_webhook_signature", "verify_zero_trust_token"]
