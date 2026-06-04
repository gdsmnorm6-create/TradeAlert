import json
import logging

from redis import Redis

from app.config import get_settings

logger = logging.getLogger(__name__)


def enqueue_sms_delivery(message_id: str) -> None:
    settings = get_settings()
    try:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        redis.lpush("tradealert:sms", json.dumps({"message_id": message_id}))
    except Exception as exc:  # pragma: no cover - local dev can run without Redis
        logger.info("SMS queued in database only; Redis unavailable: %s", exc)

