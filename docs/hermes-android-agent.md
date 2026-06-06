# Hermes Android Agent Build Brief

Build a private Android companion app that runs on the tradesman's Android phone and sends missed-call SMS replies from the phone's own SIM. This avoids Twilio, USB dongles, and any home-PC dependency for the MVP.

The v1 source now lives in `apps/android-agent`.

## Backend Contract

Base URL: the TradeAlert API on the VPS/VPN, for example `http://VPN_HOST:8000`.

The Android app can log in with `/api/auth/login`, then register itself:

```http
POST /api/device-agent/register
Authorization: Bearer <user_access_token>
Content-Type: application/json

{
  "name": "Hermes Pixel",
  "platform": "android",
  "phone_number": "07432870739"
}
```

Store the returned `token` on the Android device. It is shown once by the backend.

Report a missed call:

```http
POST /api/device-agent/missed-call
X-TradeAlert-Agent-Token: <agent_token>
Content-Type: application/json

{
  "caller_number": "07700900555",
  "device_call_id": "android-call-log-id",
  "missed_at": "2026-06-04T20:00:00Z",
  "sim_number": "07432870739",
  "raw_payload": {}
}
```

The response returns an SMS task:

```json
{
  "call_id": "...",
  "already_processed": false,
  "sms": {
    "message_id": "...",
    "to_number": "+447700900555",
    "body": "Hi, this is ..."
  }
}
```

After sending the SMS from the device SIM:

```http
POST /api/device-agent/messages/{message_id}/delivery
X-TradeAlert-Agent-Token: <agent_token>
Content-Type: application/json

{
  "status": "sent",
  "provider_sid": "android-sms-local-id"
}
```

If the app restarts, poll:

```http
GET /api/device-agent/pending-messages
X-TradeAlert-Agent-Token: <agent_token>
```

Heartbeat:

```http
POST /api/device-agent/heartbeat
X-TradeAlert-Agent-Token: <agent_token>
```

## Android MVP Requirements

- Kotlin app in `apps/android-agent`, private install first.
- Foreground service with persistent notification while monitoring.
- Runtime permissions:
  - `READ_CALL_LOG`
  - `READ_PHONE_STATE`
  - `SEND_SMS`
- Detect new missed calls from `CallLog.Calls` using a small polling worker or content observer.
- Deduplicate by Android call-log row ID and phone number.
- Send SMS using the phone SIM after backend returns the rendered body.
- Do not send more than one auto-SMS per caller within a configurable cooldown, default 30 minutes.
- Add a local kill switch: "Pause auto replies".
- Log every action locally: missed call detected, backend accepted/rejected, SMS sent/failed.

## Safety Rules

- Only respond to missed incoming calls.
- Never send SMS to premium-rate, emergency, withheld, or invalid numbers.
- Never send more than one message for the same device call ID.
- Respect backend `already_processed=true`.
- If backend is unreachable before SMS is sent, retry the missed-call event; do not spam-send.
- If SMS is sent but delivery reporting fails, reconcile status later without sending a duplicate.

## MVP Acceptance Test

1. Install Hermes Android Agent on the phone with SIM number `+447432870739`.
2. Enter the VPS/VPN API URL and register the agent against a TradeAlert company.
3. Call the phone from another number and let it miss.
4. Agent reports the missed call to TradeAlert.
5. TradeAlert returns the rendered template.
6. Agent sends SMS from the phone SIM.
7. TradeAlert dashboard shows the missed call and message status `sent`.
