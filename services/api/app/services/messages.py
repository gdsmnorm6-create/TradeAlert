from sqlalchemy.orm import Session

from app.models import CallLog, Company, Customer, Message
from app.services.queue import enqueue_sms_delivery


def create_outbound_message(
    db: Session,
    *,
    company: Company,
    to_number: str,
    body: str,
    call_log: CallLog | None = None,
    customer: Customer | None = None,
) -> Message:
    from_number = company.twilio_number or company.business_phone
    message = Message(
        company_id=company.id,
        customer_id=customer.id if customer else None,
        call_log_id=call_log.id if call_log else None,
        direction="outbound",
        from_number=from_number,
        to_number=to_number,
        body=body,
        status="queued",
    )
    db.add(message)
    db.flush()
    enqueue_sms_delivery(message.id)
    return message

