"""FOCUX audit hygiene — secrets never enter receipts.

Pattern from CopilotKit OpenBot `server/src/audit.ts` (MIT): the trail records
that a secret was requested and how long it was, never what it said. Our
receipts (hash-evidence, FIDES provenance) must never log API keys, tokens,
credentials, prompts, or tool arguments — a receipt is evidence, not a dump.
"""
from __future__ import annotations

import re

#: Keys whose VALUES are always redacted (OpenBot's list, adapted).
_SENSITIVE_KEYS = {
    "access_token", "accesstoken", "api_key", "apikey", "authorization",
    "client_secret", "clientsecret", "content", "credential", "credentials",
    "document_content", "documentcontent", "encrypted_value", "encryptedvalue",
    "id_token", "idtoken", "password", "prompt", "refresh_token",
    "refreshtoken", "result", "secret", "secrets", "token", "tokens",
    "tool_arguments", "tool_result", "api-key", "api key",
}

#: High-entropy value patterns that get redacted wherever they appear.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),            # OpenAI-style keys
    re.compile(r"sk-sp-[A-Za-z0-9._-]{8,}"),         # Token Plan style
    re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._-]{8,}"),  # keep "Bearer " label
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),         # GitHub PAT
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),             # AWS access key id
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWT
)


def redact_value(key: str, value: object) -> object:
    """Redact a single key/value pair for receipt logging."""
    if key.lower() in _SENSITIVE_KEYS:
        if isinstance(value, str):
            return f"<redacted:{len(value)}>"
        return "<redacted>"
    return value


def redact_text(text: str) -> str:
    """Redact high-entropy secrets anywhere in a text blob."""
    out = text
    for pattern in _SECRET_PATTERNS:
        if pattern.groups:
            out = pattern.sub(lambda m: m.group(1) + "<redacted>", out)
        else:
            out = pattern.sub("<redacted>", out)
    return out


def redact_mapping(data: dict[str, object]) -> dict[str, object]:
    """Deep-ish redaction of a mapping (values, and lists of scalars)."""
    redacted: dict[str, object] = {}
    for key, value in data.items():
        if key.lower() in _SENSITIVE_KEYS:
            if isinstance(value, str):
                redacted[key] = f"<redacted:{len(value)}>"
            else:
                redacted[key] = "<redacted>"
            continue
        if isinstance(value, dict):
            redacted[key] = redact_mapping(value)
        elif isinstance(value, list):
            redacted[key] = [
                redact_mapping(v) if isinstance(v, dict)
                else redact_text(v) if isinstance(v, str) else v
                for v in value
            ]
        elif isinstance(value, str):
            redacted[key] = redact_text(value)
        else:
            redacted[key] = value
    return redacted


def redact_json(text: str) -> str:
    """Redact secrets in a serialized JSON string without breaking structure."""
    try:
        import json

        data = json.loads(text)
    except (ValueError, TypeError):
        return redact_text(text)
    if isinstance(data, dict):
        return __import__("json").dumps(
            redact_mapping(data), ensure_ascii=False, default=str
        )
    if isinstance(data, list):
        return __import__("json").dumps(
            [
                redact_mapping(v) if isinstance(v, dict)
                else redact_text(v) if isinstance(v, str) else v
                for v in data
            ],
            ensure_ascii=False,
            default=str,
        )
    return redact_text(str(data))
