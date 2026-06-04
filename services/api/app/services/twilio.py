import base64
import hashlib
import hmac
from collections.abc import Mapping


def compute_twilio_signature(url: str, params: Mapping[str, str], auth_token: str) -> str:
    payload = url + "".join(f"{key}{params[key]}" for key in sorted(params))
    digest = hmac.new(auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def verify_twilio_signature(
    *,
    url: str,
    params: Mapping[str, str],
    signature: str | None,
    auth_token: str,
) -> bool:
    if not auth_token:
        return True
    if not signature:
        return False
    expected = compute_twilio_signature(url, params, auth_token)
    return hmac.compare_digest(expected, signature)

