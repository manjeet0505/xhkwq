# UK Wind Forecast Reliability Dashboard

A web app that helps a UK energy buyer decide how much power to procure from the
day-ahead market, by showing the latest wind forecast available at decision time
and quantifying how accurate those forecasts have been.

**Live app:** https://<FRONTEND-URL>
**Live API:** https://xhkwq.vercel.app/api/health

Scope: national-level wind only, January 2026 purchase decisions, data from Elexon
(FUELHH actuals and WINDFOR forecasts) only.

## AI tools used

I used Claude (Anthropic) as a coding assistant for scaffolding, debugging and
code review. I reviewed and tested all generated code, and I can explain every
part of it.

## Key assumptions

1. **Decision cutoff:** day-ahead decisions for delivery day D are made on D-1 at
   **09:00 UTC**. In January the UK is on GMT, so UTC equals UK local time.
2. **Forecast used:** for each target `startTime`, the forecast with the latest
   `publishTime <= cutoff`. Forecasts published after the cutoff are ignored.
3. **Scope of decisions:** decisions made 1-31 Jan 2026, so delivery days are
   2 Jan to 1 Feb 2026 (744 hourly points).
4. **Hourly comparison:** WINDFOR is hourly while FUELHH is half-hourly, so
   comparison is done on the hourly timestamps both datasets share.
5. **Error sign:** error = forecast - actual (positive means over-forecast).
6. **MAPE** is computed only where actual >= 1,000 MW to avoid blow-ups near zero.

## Headline results (Jan 2026 decisions)

| Metric | Value |
|---|---|
| MAE | ~2,022 MW |
| RMSE | ~2,497 MW |
| Bias (forecast - actual) | ~+1,746 MW |
| MAPE | ~21.9 % |

The day-ahead forecast systematically over-predicts wind. Error is largest in the
early morning hours (0-7 UTC) and grows with forecast horizon. The decision view
therefore shows a bias-adjusted forecast and an 80% error range alongside the raw
forecast.

## Repository structure

```
.
├── api/index.py            # Vercel serverless entry (imports the FastAPI app)
├── api/requirements.txt    # Vercel Python dependencies
├── requirements.txt        # Vercel Python dependencies (runtime only)
├── vercel.json             # Vercel routing + data bundling
├── docker-compose.yml      # Runs backend + frontend locally
├── backend/
│   ├── app/main.py         # FastAPI routes
│   ├── app/logic.py        # Cutoff logic and metrics
│   ├── scripts/fetch_data.py  # Downloads data from the Elexon API
│   ├── tests/test_logic.py # Unit tests for the core logic
│   ├── requirements.txt    # Pinned deps (dev + docker)
│   └── Dockerfile
├── frontend/               # Next.js 14 (React) dashboard
│   ├── app/page.js         # The dashboard page
│   ├── next.config.mjs     # Proxies /api/* to the backend
│   └── Dockerfile
└── data/
    ├── actuals.csv         # FUELHH wind actuals
    └── forecasts.csv       # WINDFOR forecasts
```

Data is fetched once and committed, so the deployed app does not depend on the
live Elexon API.

## API

| Endpoint | Description |
|---|---|
| `GET /api/health` | Health check and row count |
| `GET /api/series?start=&end=` | Actual vs day-ahead forecast per hour |
| `GET /api/metrics?start=&end=` | MAE, RMSE, bias, MAPE, error percentiles |
| `GET /api/metrics/by-hour?start=&end=` | Error by hour of day |
| `GET /api/metrics/by-horizon` | Error by forecast horizon (all forecasts) |
| `GET /api/decision?date=YYYY-MM-DD` | Forecast, bias-adjusted forecast and 80% range for a delivery day |

Interactive docs at `/docs` when the backend runs locally.

## How to run

### Option 1: Docker

```bash
docker compose up --build
```

Open http://localhost:3000 (API on http://localhost:8000).

### Option 2: Local (no Docker)

Backend:

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend (new terminal):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

### Tests

```bash
cd backend
python -m pytest -q
```

### Refresh data (optional)

```bash
cd backend
python scripts/fetch_data.py
```

## Deployment

Two Vercel projects from this repo:
1. **Backend:** repo root, preset "Other". `api/index.py` serves FastAPI.
2. **Frontend:** root directory `frontend`, env var `BACKEND_URL` set to the backend URL.

## Limitations and next steps

- The 80% error range uses all of January's errors, so it includes some
  look-ahead. In production it should use a rolling window of past errors only.
- Single cutoff time (09:00 UTC). The real gate closure may differ.
- Wind only, national level, one month of data.
- No authentication or caching on the API.