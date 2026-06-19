"""Tests for Feishu webhook signature verification."""
import hashlib
import hmac
import base64
import time
from backend.auth.feishu_signature import verify_feishu_signature


def test_verify_valid_signature():
    timestamp = str(int(time.time()))
    encrypt_key = "test_key_123"
    body = '{"event":"test"}'

    string_to_sign = f"{timestamp}\n{encrypt_key}\n{body}"
    digest = hmac.new(
        encrypt_key.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")

    assert verify_feishu_signature(
        timestamp=timestamp,
        nonce="any",
        body=body,
        signature=expected,
        encrypt_key=encrypt_key,
    ) is True


def test_verify_invalid_signature_rejected():
    assert verify_feishu_signature(
        timestamp="1234",
        nonce="any",
        body='{"event":"x"}',
        signature="invalid_sig_xxx",
        encrypt_key="key",
    ) is False


def test_verify_old_timestamp_rejected():
    old_ts = str(int(time.time()) - 600)
    body = '{"x":1}'
    string_to_sign = f"{old_ts}\nkey\n{body}"
    digest = hmac.new(b"key", string_to_sign.encode(), hashlib.sha256).digest()
    sig = base64.b64encode(digest).decode("utf-8")

    assert verify_feishu_signature(
        timestamp=old_ts, nonce="n", body=body,
        signature=sig, encrypt_key="key",
    ) is False