from fastapi.testclient import TestClient


def test_register_assigns_template_and_twilio_number(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "email": "roofer@example.com",
            "password": "password123",
            "business_name": "Top Roofs",
            "trade": "roofer",
            "callback_window_minutes": 30,
            "appointment_window": "same day",
            "business_phone": "07700 900101",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["user"]["company"]["trade"] == "roofer"
    assert data["user"]["company"]["twilio_number"].startswith("+44")

    headers = {"Authorization": f"Bearer {data['access_token']}"}
    template = client.get("/api/company/template", headers=headers).json()
    assert "Top Roofs" not in template["body"]
    assert "{business_name}" in template["body"]


def test_twilio_missed_call_is_idempotent(client: TestClient, auth_headers: dict[str, str]) -> None:
    company = client.get("/api/company", headers=auth_headers).json()
    payload = {
        "CallSid": "CA_missed_1",
        "From": "+447700900222",
        "To": company["twilio_number"],
        "CallStatus": "no-answer",
    }
    first = client.post("/api/webhooks/twilio/voice", data=payload)
    second = client.post("/api/webhooks/twilio/voice", data=payload)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    calls = client.get("/api/calls", headers=auth_headers).json()
    messages = client.get("/api/messages", headers=auth_headers).json()
    assert len(calls) == 1
    outbound = [message for message in messages if message["direction"] == "outbound"]
    assert len(outbound) == 1
    assert "Ian's Plumbing" in outbound[0]["body"]
    assert outbound[0]["status"] in {"queued", "ready_to_send"}


def test_jobs_invoices_sumup_and_ocr_flow(client: TestClient, auth_headers: dict[str, str]) -> None:
    customer = client.post(
        "/api/customers",
        headers=auth_headers,
        json={"name": "Sarah", "phone": "07700 900333", "address": "10 High Street"},
    ).json()
    job = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={"customer_id": customer["id"], "title": "Replace kitchen tap"},
    ).json()
    invoice = client.post(
        "/api/invoices",
        headers=auth_headers,
        json={"customer_id": customer["id"], "job_id": job["id"], "amount_minor": 12500, "currency": "GBP"},
    )
    assert invoice.status_code == 201, invoice.text
    invoice_data = invoice.json()
    assert invoice_data["sumup_checkout_url"].startswith("https://checkout.sumup.com/pay/")

    receipt = client.post(
        "/api/ocr/receipts",
        headers=auth_headers,
        json={
            "filename": "receipt.jpg",
            "job_id": job["id"],
            "raw_text": "Pipe fittings 25.00",
            "amount_minor": 2500,
            "merchant_name": "Builders Merchant",
        },
    )
    assert receipt.status_code == 201, receipt.text
    assert receipt.json()["status"] == "processed"


def test_openai_realtime_incoming_call_creates_voice_session(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    company = client.get("/api/company", headers=auth_headers).json()
    response = client.post(
        "/api/webhooks/openai/realtime",
        json={
            "id": "evt_1",
            "type": "realtime.call.incoming",
            "data": {
                "call_id": "call_1",
                "sip_headers": [
                    {"name": "From", "value": "sip:+447700900444@sip.example.com"},
                    {"name": "To", "value": f"sip:{company['twilio_number']}@sip.example.com"},
                ],
            },
        },
    )
    assert response.status_code == 200, response.text
    sessions = client.get("/api/voice-sessions", headers=auth_headers).json()
    assert len(sessions) == 1
    assert sessions[0]["call_id"] == "call_1"
