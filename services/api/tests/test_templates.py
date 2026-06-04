import pytest

from app.services.phone import normalize_phone
from app.services.templates import render_template, validate_template_body
from app.services.twilio import compute_twilio_signature, verify_twilio_signature


def test_template_rendering_uses_company_values() -> None:
    body = "Hi from {business_name}. We'll call in {callback_window} for a {appointment_window}."
    rendered = render_template(
        body,
        business_name="TradeAlert Plumbing",
        callback_window_minutes=10,
        appointment_window="4-hour",
    )
    assert rendered == "Hi from TradeAlert Plumbing. We'll call in 10 minutes for a 4-hour window."


def test_template_rejects_unknown_variables() -> None:
    with pytest.raises(ValueError):
        validate_template_body("Hi {business_name}, your {unknown} is ready")


def test_phone_normalization_defaults_to_gb() -> None:
    assert normalize_phone("07700 900123") == "+447700900123"


def test_twilio_signature_verification() -> None:
    url = "https://api.example.com/api/webhooks/twilio/voice"
    params = {"CallSid": "CA123", "From": "+447700900123", "To": "+447700900001"}
    signature = compute_twilio_signature(url, params, "secret")
    assert verify_twilio_signature(url=url, params=params, signature=signature, auth_token="secret")
    assert not verify_twilio_signature(url=url, params=params, signature="bad", auth_token="secret")

