from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Template
from app.services.templates import DEFAULT_TEMPLATES, TEMPLATE_VARIABLES


def seed_default_templates(db: Session) -> None:
    for trade, body in DEFAULT_TEMPLATES.items():
        existing = db.scalar(select(Template).where(Template.trade == trade))
        if existing is None:
            db.add(Template(trade=trade, body=body, variables=TEMPLATE_VARIABLES))

