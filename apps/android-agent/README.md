# TradeAlert Android Agent

Private Android v1 agent for the no-Twilio/no-dongle MVP.

The VPS/VPN runs the TradeAlert API. This Android app runs on the tradesman's phone, watches missed calls, asks the API for the rendered reply, and sends the SMS from the phone SIM.

## Build

Open `apps/android-agent` in Android Studio and build the `app` module, or run:

```powershell
cd apps/android-agent
.\gradlew.bat assembleDebug
```

The debug APK is written to `app/build/outputs/apk/debug/app-debug.apk`.

## First Test

1. Start the TradeAlert API on the VPS/VPN.
2. Register or log in to the TradeAlert company account.
3. Install this app on the Android phone with the business SIM.
4. Enter:
   - API base URL, for example `http://100.x.x.x:8000`
   - TradeAlert email and password
   - Phone/SIM number, for example `07432870739`
5. Tap `Allow permissions`.
6. Tap `Login and register this phone`.
7. Tap `Heartbeat test`.
8. Tap `Start missed-call monitoring`.
9. Call the phone from another number and let it ring out.
10. Confirm the caller receives the TradeAlert SMS from this phone SIM.
11. Confirm `/api/calls` and `/api/messages` show the missed call and message status.

## Notes

- The app sets a call-log baseline on first start so it does not text old missed calls.
- It skips unsafe destinations such as withheld/private, emergency, short-code, and common UK premium-rate numbers.
- It uses a 30 minute local cooldown per caller.
- If the backend is unreachable before SMS is sent, the call-log item is retried.
- If SMS is sent but delivery reporting fails, the local message ID is remembered so the app can reconcile without sending a duplicate.
