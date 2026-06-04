import hashlib
import hmac
import time


def verify_stripe_signature(payload: bytes, signature_header: str | None, secret: str, tolerance: int = 300) -> bool:
    if not secret:
        return True
    if not signature_header:
        return False

    parts = {}
    for item in signature_header.split(","):
        key, _, value = item.partition("=")
        parts.setdefault(key, []).append(value)

    timestamps = parts.get("t", [])
    signatures = parts.get("v1", [])
    if not timestamps or not signatures:
        return False
    try:
        timestamp = int(timestamps[0])
    except ValueError:
        return False
    if abs(time.time() - timestamp) > tolerance:
        return False

    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in signatures)

