from fastapi.testclient import TestClient


def test_device_agent_missed_call_returns_sms_task(client: TestClient, auth_headers: dict[str, str]) -> None:
    registered = client.post(
        "/api/device-agent/register",
        headers=auth_headers,
        json={"name": "Hermes Pixel", "phone_number": "07432870739"},
    )
    assert registered.status_code == 201, registered.text
    token = registered.json()["token"]

    missed = client.post(
        "/api/device-agent/missed-call",
        headers={"X-TradeAlert-Agent-Token": token},
        json={
            "caller_number": "07700 900555",
            "device_call_id": "call-1",
            "sim_number": "07432870739",
        },
    )
    assert missed.status_code == 201, missed.text
    data = missed.json()
    assert data["already_processed"] is False
    assert data["sms"]["to_number"] == "+447700900555"
    assert "Ian's Plumbing" in data["sms"]["body"]

    duplicate = client.post(
        "/api/device-agent/missed-call",
        headers={"X-TradeAlert-Agent-Token": token},
        json={
            "caller_number": "07700 900555",
            "device_call_id": "call-1",
            "sim_number": "07432870739",
        },
    )
    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()["already_processed"] is True
    assert duplicate.json()["sms"] is None


def test_device_agent_delivery_updates_message(client: TestClient, auth_headers: dict[str, str]) -> None:
    registered = client.post("/api/device-agent/register", headers=auth_headers, json={})
    token = registered.json()["token"]
    missed = client.post(
        "/api/device-agent/missed-call",
        headers={"X-TradeAlert-Agent-Token": token},
        json={"caller_number": "07700 900556", "device_call_id": "call-2"},
    ).json()
    message_id = missed["sms"]["message_id"]

    delivered = client.post(
        f"/api/device-agent/messages/{message_id}/delivery",
        headers={"X-TradeAlert-Agent-Token": token},
        json={"status": "sent", "provider_sid": "android-sms-1"},
    )
    assert delivered.status_code == 200, delivered.text
    assert delivered.json()["status"] == "sent"

