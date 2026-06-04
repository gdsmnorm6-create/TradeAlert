import json
import logging
import time

from redis import Redis
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tradealert.worker")


def process_message(message_id: str) -> None:
    with SessionLocal() as db:
        message = db.scalar(select(Message).where(Message.id == message_id))
        if message is None:
            return
        # Real Twilio sending is intentionally behind provider credentials.
        message.status = "ready_to_send"
        db.commit()
        logger.info("Prepared outbound SMS %s to %s", message.id, message.to_number)


def main() -> None:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("TradeAlert worker listening on tradealert:sms")
    while True:
        item = redis.brpop("tradealert:sms", timeout=5)
        if item is None:
            time.sleep(0.1)
            continue
        _, payload = item
        process_message(json.loads(payload)["message_id"])


if __name__ == "__main__":
    main()

