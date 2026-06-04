from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import (
    AuditEvent,
    CallLog,
    Company,
    CompanyTemplate,
    Customer,
    Invoice,
    Job,
    Message,
    OcrExtraction,
    Payment,
    ReceiptUpload,
    StockItem,
    Template,
    User,
    VoiceSession,
)
from app.schemas import (
    AuthResponse,
    CallOut,
    CompanyOut,
    CompanyPatch,
    CustomerCreate,
    CustomerOut,
    InvoiceCreate,
    InvoiceOut,
    JobCreate,
    JobOut,
    LoginRequest,
    MessageOut,
    ReceiptOut,
    ReceiptRequest,
    RegisterRequest,
    SendMessageRequest,
    StockItemCreate,
    StockItemOut,
    TemplateOut,
    TemplatePatch,
    TokenResponse,
    UserOut,
    VoiceSessionOut,
)
from app.security import create_access_token, get_current_user, hash_password, verify_password
from app.services.messages import create_outbound_message
from app.services.phone import normalize_phone
from app.services.provisioning import assign_twilio_number
from app.services.seed import seed_default_templates
from app.services.stripe import verify_stripe_signature
from app.services.sumup import create_hosted_checkout
from app.services.templates import (
    TEMPLATE_VARIABLES,
    render_template,
    validate_template_body,
    validate_trade,
)
from app.services.twilio import verify_twilio_signature

router = APIRouter(prefix="/api")


def current_company(user: User) -> Company:
    if user.company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return user.company


def upsert_customer_by_phone(db: Session, company_id: str, phone: str) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.company_id == company_id, Customer.phone == phone))
    if customer is None:
        customer = Customer(company_id=company_id, phone=phone)
        db.add(customer)
        db.flush()
    return customer


def company_template_out(company: Company) -> TemplateOut:
    template = company.company_template
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not assigned")
    return TemplateOut(id=template.id, trade=company.trade, body=template.body, variables=template.variables)


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    seed_default_templates(db)
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    try:
        trade = validate_trade(payload.trade)
        business_phone = normalize_phone(payload.business_phone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    template = db.scalar(select(Template).where(Template.trade == trade))
    if template is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Default template missing")

    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()

    company = Company(
        user_id=user.id,
        business_name=payload.business_name.strip(),
        trade=trade,
        callback_window_minutes=payload.callback_window_minutes,
        appointment_window=payload.appointment_window,
        business_phone=business_phone,
        stripe_customer_id=f"cus_demo_{user.id[:8]}",
        stripe_subscription_id=f"sub_demo_{user.id[:8]}",
        subscription_status="trialing",
    )
    db.add(company)
    db.flush()
    assign_twilio_number(db, company)

    db.add(
        CompanyTemplate(
            company_id=company.id,
            template_id=template.id,
            body=template.body,
            variables=TEMPLATE_VARIABLES,
        )
    )
    db.add(AuditEvent(company_id=company.id, actor_user_id=user.id, event_type="company.registered", payload={}))
    db.commit()
    db.refresh(user)

    return AuthResponse(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/company", response_model=CompanyOut)
def get_company(user: User = Depends(get_current_user)) -> CompanyOut:
    return CompanyOut.model_validate(current_company(user))


@router.patch("/company", response_model=CompanyOut)
def update_company(
    payload: CompanyPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CompanyOut:
    company = current_company(user)
    if payload.business_name is not None:
        company.business_name = payload.business_name.strip()
    if payload.callback_window_minutes is not None:
        company.callback_window_minutes = payload.callback_window_minutes
    if payload.appointment_window is not None:
        company.appointment_window = payload.appointment_window
    if payload.business_phone is not None:
        try:
            company.business_phone = normalize_phone(payload.business_phone)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if payload.trade is not None:
        try:
            trade = validate_trade(payload.trade)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        company.trade = trade
        default_template = db.scalar(select(Template).where(Template.trade == trade))
        if default_template and company.company_template:
            company.company_template.template_id = default_template.id
            company.company_template.body = default_template.body
            company.company_template.variables = TEMPLATE_VARIABLES
    db.commit()
    db.refresh(company)
    return CompanyOut.model_validate(company)


@router.get("/company/template", response_model=TemplateOut)
def get_company_template(user: User = Depends(get_current_user)) -> TemplateOut:
    return company_template_out(current_company(user))


@router.patch("/company/template", response_model=TemplateOut)
def update_company_template(
    payload: TemplatePatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TemplateOut:
    company = current_company(user)
    try:
        validate_template_body(payload.body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    company.company_template.body = payload.body
    db.commit()
    db.refresh(company.company_template)
    return company_template_out(company)


@router.get("/calls", response_model=list[CallOut])
def list_calls(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CallLog]:
    company = current_company(user)
    return list(
        db.scalars(select(CallLog).where(CallLog.company_id == company.id).order_by(CallLog.created_at.desc()))
    )


@router.get("/messages", response_model=list[MessageOut])
def list_messages(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Message]:
    company = current_company(user)
    return list(
        db.scalars(select(Message).where(Message.company_id == company.id).order_by(Message.created_at.desc()))
    )


@router.post("/messages/send", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    payload: SendMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Message:
    company = current_company(user)
    try:
        to_number = normalize_phone(payload.to_number)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    customer = upsert_customer_by_phone(db, company.id, to_number)
    message = create_outbound_message(db, company=company, customer=customer, to_number=to_number, body=payload.body)
    db.commit()
    db.refresh(message)
    return message


@router.post("/webhooks/twilio/voice")
async def twilio_voice_webhook(request: Request, db: Session = Depends(get_db)) -> Response:
    settings = get_settings()
    form = {key: str(value) for key, value in (await request.form()).items()}
    if not verify_twilio_signature(
        url=str(request.url),
        params=form,
        signature=request.headers.get("X-Twilio-Signature"),
        auth_token=settings.twilio_auth_token,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")

    try:
        caller = normalize_phone(form.get("From", ""))
        called = normalize_phone(form.get("To", ""))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    company = db.scalar(select(Company).where(Company.twilio_number == called))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Twilio number is not assigned")

    call_sid = form.get("CallSid") or f"manual-{caller}-{called}"
    call = db.scalar(select(CallLog).where(CallLog.call_sid == call_sid))
    if call is None:
        call = CallLog(
            company_id=company.id,
            call_sid=call_sid,
            caller_number=caller,
            called_number=called,
            status=form.get("CallStatus", "missed"),
            missed=True,
            raw_payload=form,
        )
        db.add(call)
        db.flush()

    customer = upsert_customer_by_phone(db, company.id, caller)
    existing_sms = db.scalar(
        select(Message).where(
            Message.company_id == company.id,
            Message.call_log_id == call.id,
            Message.direction == "outbound",
        )
    )
    if existing_sms is None:
        body = render_template(
            company.company_template.body,
            business_name=company.business_name,
            callback_window_minutes=company.callback_window_minutes,
            appointment_window=company.appointment_window,
        )
        create_outbound_message(db, company=company, customer=customer, call_log=call, to_number=caller, body=body)

    db.commit()
    return Response('<?xml version="1.0" encoding="UTF-8"?><Response><Hangup /></Response>', media_type="application/xml")


@router.post("/webhooks/twilio/sms")
async def twilio_sms_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    settings = get_settings()
    form = {key: str(value) for key, value in (await request.form()).items()}
    if not verify_twilio_signature(
        url=str(request.url),
        params=form,
        signature=request.headers.get("X-Twilio-Signature"),
        auth_token=settings.twilio_auth_token,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Twilio signature")
    try:
        from_number = normalize_phone(form.get("From", ""))
        to_number = normalize_phone(form.get("To", ""))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    company = db.scalar(select(Company).where(Company.twilio_number == to_number))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Twilio number is not assigned")
    customer = upsert_customer_by_phone(db, company.id, from_number)
    db.add(
        Message(
            company_id=company.id,
            customer_id=customer.id,
            direction="inbound",
            from_number=from_number,
            to_number=to_number,
            body=form.get("Body", ""),
            provider_sid=form.get("MessageSid"),
            status="received",
            raw_payload=form,
        )
    )
    db.commit()
    return {"status": "received"}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    settings = get_settings()
    payload = await request.body()
    if not verify_stripe_signature(payload, request.headers.get("Stripe-Signature"), settings.stripe_webhook_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Stripe signature")
    event = await request.json()
    data = event.get("data", {}).get("object", {})
    subscription_id = data.get("id") if event.get("type", "").startswith("customer.subscription") else data.get("subscription")
    customer_id = data.get("customer")
    company = None
    if subscription_id:
        company = db.scalar(select(Company).where(Company.stripe_subscription_id == subscription_id))
    if company is None and customer_id:
        company = db.scalar(select(Company).where(Company.stripe_customer_id == customer_id))
    if company is not None:
        company.subscription_status = data.get("status", company.subscription_status)
        db.add(AuditEvent(company_id=company.id, event_type=f"stripe.{event.get('type')}", payload=event))
        db.commit()
    return {"status": "ok"}


@router.post("/webhooks/sumup")
async def sumup_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    event = await request.json()
    checkout_id = event.get("checkout_id") or event.get("id") or event.get("checkout_reference")
    status_value = str(event.get("status", "unknown")).lower()
    invoice = None
    if checkout_id:
        invoice = db.scalar(select(Invoice).where(Invoice.sumup_checkout_id == checkout_id))
    if invoice is not None:
        invoice.status = "paid" if status_value in {"paid", "successful", "success"} else status_value
        db.add(
            Payment(
                company_id=invoice.company_id,
                invoice_id=invoice.id,
                provider="sumup",
                provider_payment_id=str(event.get("transaction_id") or checkout_id),
                amount_minor=invoice.amount_minor,
                currency=invoice.currency,
                status=invoice.status,
                raw_payload=event,
            )
        )
        db.commit()
    return {"status": "ok"}


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Customer]:
    company = current_company(user)
    return list(db.scalars(select(Customer).where(Customer.company_id == company.id).order_by(Customer.created_at.desc())))


@router.post("/customers", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Customer:
    company = current_company(user)
    try:
        phone = normalize_phone(payload.phone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    customer = upsert_customer_by_phone(db, company.id, phone)
    customer.name = payload.name
    customer.email = str(payload.email) if payload.email else None
    customer.address = payload.address
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Job]:
    company = current_company(user)
    return list(db.scalars(select(Job).where(Job.company_id == company.id).order_by(Job.created_at.desc())))


@router.post("/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Job:
    company = current_company(user)
    job = Job(
        company_id=company.id,
        customer_id=payload.customer_id,
        source_call_log_id=payload.source_call_log_id,
        title=payload.title,
        description=payload.description,
        scheduled_window=payload.scheduled_window,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Invoice]:
    company = current_company(user)
    return list(db.scalars(select(Invoice).where(Invoice.company_id == company.id).order_by(Invoice.created_at.desc())))


@router.post("/invoices", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Invoice:
    settings = get_settings()
    company = current_company(user)
    count = db.query(Invoice).filter(Invoice.company_id == company.id).count() + 1
    invoice = Invoice(
        company_id=company.id,
        customer_id=payload.customer_id,
        job_id=payload.job_id,
        number=f"TA-{count:05d}",
        amount_minor=payload.amount_minor,
        currency=payload.currency.upper(),
        status="payment_pending",
    )
    db.add(invoice)
    db.flush()
    checkout = await create_hosted_checkout(invoice, settings)
    invoice.sumup_checkout_id = checkout.checkout_id
    invoice.sumup_checkout_url = checkout.checkout_url
    if payload.customer_id:
        customer = db.get(Customer, payload.customer_id)
        if customer and customer.phone:
            create_outbound_message(
                db,
                company=company,
                customer=customer,
                to_number=customer.phone,
                body=f"Invoice {invoice.number} from {company.business_name}: {checkout.checkout_url}",
            )
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/stock", response_model=list[StockItemOut])
def list_stock(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[StockItem]:
    company = current_company(user)
    return list(db.scalars(select(StockItem).where(StockItem.company_id == company.id).order_by(StockItem.name)))


@router.post("/stock", response_model=StockItemOut, status_code=status.HTTP_201_CREATED)
def create_stock_item(
    payload: StockItemCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StockItem:
    company = current_company(user)
    item = StockItem(
        company_id=company.id,
        name=payload.name,
        sku=payload.sku,
        quantity=payload.quantity,
        reorder_level=payload.reorder_level,
        unit_cost_minor=payload.unit_cost_minor,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/ocr/receipts", response_model=ReceiptOut, status_code=status.HTTP_201_CREATED)
def create_receipt_extraction(
    payload: ReceiptRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReceiptOut:
    company = current_company(user)
    receipt = ReceiptUpload(company_id=company.id, job_id=payload.job_id, filename=payload.filename)
    db.add(receipt)
    db.flush()
    extraction = OcrExtraction(
        receipt_upload_id=receipt.id,
        raw_text=payload.raw_text,
        amount_minor=payload.amount_minor,
        merchant_name=payload.merchant_name,
        extracted_items=payload.extracted_items,
    )
    db.add(extraction)
    db.add(
        AuditEvent(
            company_id=company.id,
            actor_user_id=user.id,
            event_type="ocr.receipt_processed",
            payload={"receipt_upload_id": receipt.id, "amount_minor": payload.amount_minor},
        )
    )
    db.commit()
    return ReceiptOut(receipt_upload_id=receipt.id, ocr_extraction_id=extraction.id, status=receipt.status)


def extract_sip_phone(headers: list[dict[str, Any]], name: str) -> str | None:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            value = str(header.get("value", ""))
            if "sip:" in value:
                value = value.split("sip:", 1)[1].split("@", 1)[0]
            try:
                return normalize_phone(value)
            except ValueError:
                return value or None
    return None


@router.post("/webhooks/openai/realtime")
async def openai_realtime_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    event = await request.json()
    data = event.get("data", {})
    call_id = data.get("call_id") or event.get("id")
    if not call_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="call_id is required")
    headers = data.get("sip_headers", [])
    caller = extract_sip_phone(headers, "From")
    called = extract_sip_phone(headers, "To")
    company = db.scalar(select(Company).where(Company.twilio_number == called)) if called else None
    session = db.scalar(select(VoiceSession).where(VoiceSession.call_id == call_id))
    if session is None:
        session = VoiceSession(
            company_id=company.id if company else None,
            call_id=call_id,
            caller_number=caller,
            called_number=called,
            status="accepted_stub",
        )
        db.add(session)
        db.flush()
    db.add(
        AuditEvent(
            company_id=company.id if company else None,
            event_type="openai.realtime_call_incoming",
            payload=event,
        )
    )
    db.commit()
    return {"accepted": True, "mode": "stubbed", "voice_session_id": session.id}


@router.get("/voice-sessions", response_model=list[VoiceSessionOut])
def list_voice_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[VoiceSession]:
    company = current_company(user)
    return list(
        db.scalars(select(VoiceSession).where(VoiceSession.company_id == company.id).order_by(VoiceSession.created_at.desc()))
    )

