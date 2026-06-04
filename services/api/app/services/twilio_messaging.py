import logging

import httpx
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import Message

logger = logging.getLogger(__name__)


def can_send_real_sms(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    has_sender = bool(settings.twilio_messaging_service_sid or settings.twilio_from_number)
    return bool(settings.twilio_account_sid and settings.twilio_auth_token and has_sender)


def deliver_sms(db: Session, message: Message, settings: Settings | None = None) -> Message:
    settings = settings or get_settings()
    if not can_send_real_sms(settings):
        message.status = "ready_to_send"
        db.flush()
        logger.info("Twilio sender not configured; SMS %s remains ready_to_send", message.id)
        return message

    data = {
        "To": message.to_number,
        "Body": message.body,
    }
    if settings.twilio_messaging_service_sid:
        data["MessagingServiceSid"] = settings.twilio_messaging_service_sid
    else:
        data["From"] = settings.twilio_from_number

    try:
        response = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json",
            data=data,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            timeout=15,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        message.status = "failed"
        message.raw_payload = {**(message.raw_payload or {}), "twilio_error": str(exc)}
        db.flush()
        logger.exception("Failed to send Twilio SMS %s", message.id)
        return message

    payload = response.json()
    message.provider_sid = payload.get("sid")
    message.status = payload.get("status", "sent")
    message.raw_payload = {**(message.raw_payload or {}), "twilio_response": payload}
    db.flush()
    return message

