"""Feishu webhook signature verification.

Algorithm: HMAC-SHA256 over "{timestamp}\n{encrypt_key}\n{body}", base64 encoded.
"""
import base64
import hashlib
import hmac
import time
from typing import Final

MAX_TIMESTAMP_AGE_SEC: Final = 300


def verify_feishu_signature(
    timestamp: str,
    nonce: str,
    body: str,
    signature: str,
    encrypt_key: str,
    max_age_sec: int = MAX_TIMESTAMP_AGE_SEC,
) -> bool:
    if not timestamp or not signature or not encrypt_key:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    now = int(time.time())
    if abs(now - ts) > max_age_sec:
        return False
    string_to_sign = f"{timestamp}\n{encrypt_key}\n{body}"
    digest = hmac.new(
        encrypt_key.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)