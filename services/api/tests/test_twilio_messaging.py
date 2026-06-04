from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Company, Message
from app.services.twilio_messaging import can_send_real_sms, deliver_sms


def test_real_sms_requires_sender_configuration() -> None:
    settings = Settings(
        twilio_account_sid="AC123",
        twilio_auth_token="secret",
        twilio_from_number="",
        twilio_messaging_service_sid="",
    )
    assert not can_send_real_sms(settings)


def test_deliver_sms_without_sender_marks_ready(db_session: Session) -> None:
    company = Company(
        user_id="user-id",
        business_name="Test Plumbing",
        trade="plumber",
        business_phone="+447432870739",
        twilio_number="+447700900001",
    )
    db_session.add(company)
    db_session.flush()
    message = Message(
        company_id=company.id,
        direction="outbound",
        from_number="+447700900001",
        to_number="+447432870739",
        body="Hello",
        status="queued",
    )
    db_session.add(message)
    db_session.flush()

    deliver_sms(db_session, message, Settings(twilio_account_sid="AC123", twilio_auth_token="secret"))

    assert message.status == "ready_to_send"

