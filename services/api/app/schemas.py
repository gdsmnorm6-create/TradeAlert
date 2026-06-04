from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_name: str
    trade: str
    callback_window_minutes: int
    appointment_window: str
    business_phone: str
    twilio_number: str | None
    subscription_status: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    company: CompanyOut


class AuthResponse(TokenResponse):
    user: UserOut


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    business_name: str = Field(min_length=2, max_length=255)
    trade: str
    callback_window_minutes: int = Field(default=10, ge=5, le=60)
    appointment_window: str = "4-hour"
    business_phone: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CompanyPatch(BaseModel):
    business_name: str | None = None
    trade: str | None = None
    callback_window_minutes: int | None = Field(default=None, ge=5, le=60)
    appointment_window: str | None = None
    business_phone: str | None = None


class TemplateOut(BaseModel):
    id: str
    trade: str
    body: str
    variables: list[str]


class TemplatePatch(BaseModel):
    body: str


class CallOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    call_sid: str
    caller_number: str
    called_number: str
    status: str
    missed: bool
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    direction: str
    from_number: str
    to_number: str
    body: str
    status: str
    created_at: datetime


class SendMessageRequest(BaseModel):
    to_number: str
    body: str = Field(min_length=1, max_length=1600)


class CustomerCreate(BaseModel):
    name: str | None = None
    phone: str
    email: EmailStr | None = None
    address: str | None = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str | None
    phone: str
    email: str | None
    address: str | None


class JobCreate(BaseModel):
    customer_id: str | None = None
    source_call_log_id: str | None = None
    title: str
    description: str | None = None
    scheduled_window: str | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str | None
    source_call_log_id: str | None
    title: str
    description: str | None
    status: str
    scheduled_window: str | None
    created_at: datetime


class InvoiceCreate(BaseModel):
    customer_id: str | None = None
    job_id: str | None = None
    amount_minor: int = Field(gt=0)
    currency: str = Field(default="GBP", min_length=3, max_length=3)


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    number: str
    amount_minor: int
    currency: str
    status: str
    sumup_checkout_id: str | None
    sumup_checkout_url: str | None
    created_at: datetime


class StockItemCreate(BaseModel):
    name: str
    sku: str
    quantity: int = 0
    reorder_level: int = 0
    unit_cost_minor: int = 0


class StockItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    sku: str
    quantity: int
    reorder_level: int
    unit_cost_minor: int


class ReceiptRequest(BaseModel):
    filename: str
    job_id: str | None = None
    raw_text: str
    amount_minor: int | None = None
    merchant_name: str | None = None
    extracted_items: list[dict[str, Any]] = Field(default_factory=list)


class ReceiptOut(BaseModel):
    receipt_upload_id: str
    ocr_extraction_id: str
    status: str


class VoiceSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    call_id: str
    caller_number: str | None
    called_number: str | None
    status: str
    transcript_summary: str | None
    created_at: datetime

