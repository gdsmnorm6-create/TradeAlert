from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Company, TwilioNumber


def assign_twilio_number(db: Session, company: Company) -> str:
    settings = get_settings()
    for phone_number in settings.twilio_pool:
        existing = db.scalar(select(TwilioNumber).where(TwilioNumber.phone_number == phone_number))
        if existing is None:
            record = TwilioNumber(phone_number=phone_number, company_id=company.id)
            db.add(record)
            company.twilio_number = phone_number
            return phone_number
        if existing.company_id is None:
            existing.company_id = company.id
            company.twilio_number = phone_number
            return phone_number

    count = db.query(TwilioNumber).count() + 1
    phone_number = f"+4477009{count:05d}"
    db.add(TwilioNumber(phone_number=phone_number, company_id=company.id))
    company.twilio_number = phone_number
    return phone_number

