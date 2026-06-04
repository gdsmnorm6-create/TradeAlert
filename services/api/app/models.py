from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    company: Mapped["Company"] = relationship(back_populates="user", uselist=False)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    business_name: Mapped[str] = mapped_column(String(255))
    trade: Mapped[str] = mapped_column(String(64), index=True)
    callback_window_minutes: Mapped[int] = mapped_column(Integer, default=10)
    appointment_window: Mapped[str] = mapped_column(String(64), default="4-hour")
    business_phone: Mapped[str] = mapped_column(String(32))
    twilio_number: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subscription_status: Mapped[str] = mapped_column(String(64), default="trialing")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped[User] = relationship(back_populates="company")
    company_template: Mapped["CompanyTemplate"] = relationship(back_populates="company", uselist=False)
    calls: Mapped[list["CallLog"]] = relationship(back_populates="company")
    messages: Mapped[list["Message"]] = relationship(back_populates="company")


class TwilioNumber(Base):
    __tablename__ = "twilio_numbers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    phone_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="assigned")
    regulatory_bundle_status: Mapped[str] = mapped_column(String(64), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    trade: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    body: Mapped[str] = mapped_column(Text)
    variables: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class CompanyTemplate(Base):
    __tablename__ = "company_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), unique=True)
    template_id: Mapped[str] = mapped_column(ForeignKey("templates.id"))
    body: Mapped[str] = mapped_column(Text)
    variables: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    company: Mapped[Company] = relationship(back_populates="company_template")
    template: Mapped[Template] = relationship()


class CallLog(Base):
    __tablename__ = "call_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    call_sid: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    caller_number: Mapped[str] = mapped_column(String(32), index=True)
    called_number: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(64), default="missed")
    missed: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    company: Mapped[Company] = relationship(back_populates="calls")
    messages: Mapped[list["Message"]] = relationship(back_populates="call_log")


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("company_id", "phone", name="uq_customer_company_phone"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    call_log_id: Mapped[str | None] = mapped_column(ForeignKey("call_logs.id"), nullable=True)
    direction: Mapped[str] = mapped_column(String(32))
    from_number: Mapped[str] = mapped_column(String(32))
    to_number: Mapped[str] = mapped_column(String(32))
    body: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(64), default="twilio")
    provider_sid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="queued")
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    company: Mapped[Company] = relationship(back_populates="messages")
    call_log: Mapped[CallLog | None] = relationship(back_populates="messages")


class DeviceAgent(Base):
    __tablename__ = "device_agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), default="Android Agent")
    platform: Mapped[str] = mapped_column(String(64), default="android")
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    source_call_log_id: Mapped[str | None] = mapped_column(ForeignKey("call_logs.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="new")
    scheduled_window: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    customer_id: Mapped[str | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    number: Mapped[str] = mapped_column(String(64), unique=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="GBP")
    status: Mapped[str] = mapped_column(String(64), default="draft")
    sumup_checkout_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sumup_checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    invoice_id: Mapped[str | None] = mapped_column(ForeignKey("invoices.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(64), default="sumup")
    provider_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    amount_minor: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="GBP")
    status: Mapped[str] = mapped_column(String(64))
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class StockItem(Base):
    __tablename__ = "stock_items"
    __table_args__ = (UniqueConstraint("company_id", "sku", name="uq_stock_company_sku"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    sku: Mapped[str] = mapped_column(String(128))
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, default=0)
    unit_cost_minor: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    stock_item_id: Mapped[str] = mapped_column(ForeignKey("stock_items.id"))
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ReceiptUpload(Base):
    __tablename__ = "receipt_uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), index=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(64), default="processed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class OcrExtraction(Base):
    __tablename__ = "ocr_extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    receipt_upload_id: Mapped[str] = mapped_column(ForeignKey("receipt_uploads.id"), index=True)
    raw_text: Mapped[str] = mapped_column(Text)
    amount_minor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    merchant_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    extracted_items: Mapped[list[dict]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    call_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    caller_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    called_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="incoming")
    transcript_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class VoiceTurn(Base):
    __tablename__ = "voice_turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    voice_session_id: Mapped[str] = mapped_column(ForeignKey("voice_sessions.id"), index=True)
    speaker: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
