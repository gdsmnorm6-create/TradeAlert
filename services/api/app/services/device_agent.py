import hashlib
import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import DeviceAgent, now_utc


def make_agent_token() -> str:
    return f"ta_agent_{secrets.token_urlsafe(32)}"


def hash_agent_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authenticate_agent(
    db: Session = Depends(get_db),
    token: str | None = Header(default=None, alias="X-TradeAlert-Agent-Token"),
) -> DeviceAgent:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agent token missing")
    token_hash = hash_agent_token(token)
    agent = db.scalar(select(DeviceAgent).where(DeviceAgent.token_hash == token_hash))
    if agent is None or agent.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Agent token invalid")
    agent.last_seen_at = now_utc()
    db.flush()
    return agent
