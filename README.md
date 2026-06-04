# TradeAlert

TradeAlert is a phased mobile app for UK tradespeople. The first wedge captures missed calls and sends a trade-specific SMS reply; later phases add jobs, invoices, SumUp payments, receipt/material OCR, stock, and a Twilio plus OpenAI voice receptionist.

## Repo Layout

- `apps/mobile` - Expo React Native app, TypeScript, Expo Router.
- `services/api` - FastAPI backend with SQLAlchemy 2, Alembic, Postgres support, Redis queue hooks, and pytest coverage.
- `docker-compose.yml` - local Postgres, Redis, API, and worker.

## Local Backend

```powershell
cd services/api
python -m venv ..\..\.venv
..\..\.venv\Scripts\python -m pip install -r requirements-dev.txt
..\..\.venv\Scripts\pytest
..\..\.venv\Scripts\uvicorn app.main:app --reload
```

The backend defaults to a local SQLite database for quick development. Docker uses Postgres via `TRADEALERT_DATABASE_URL`.

## Local Mobile

```powershell
cd apps/mobile
npm install
npm run web
```

Set `EXPO_PUBLIC_API_BASE_URL` if the API is not at `http://localhost:8000`.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

API docs are available at `http://localhost:8000/docs`.

