from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from .logic import (load_data, day_ahead_forecast, overall_metrics,
                    metrics_by_hour, metrics_by_horizon)

app = FastAPI(title="Wind Forecast API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
router = APIRouter(prefix="/api")

ACT, FC = load_data()
DF = day_ahead_forecast(ACT, FC)
FMT = "%Y-%m-%dT%H:%M:%SZ"


def sl(start, end):
    df = DF
    if start:
        df = df[df["startTime"] >= pd.Timestamp(start, tz="UTC")]
    if end:
        df = df[df["startTime"] < pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)]
    return df


@router.get("/health")
def health():
    return {"ok": True, "rows": len(DF)}


@router.get("/series")
def series(start: str | None = None, end: str | None = None):
    df = sl(start, end).copy()
    for c in ["startTime", "publishTime", "cutoff"]:
        df[c] = df[c].dt.strftime(FMT)
    return df[["startTime", "publishTime", "actual", "forecast", "error", "horizon_h"]].to_dict("records")


@router.get("/metrics")
def metrics(start: str | None = None, end: str | None = None):
    return overall_metrics(sl(start, end))


@router.get("/metrics/by-hour")
def by_hour(start: str | None = None, end: str | None = None):
    return metrics_by_hour(sl(start, end)).to_dict("records")


@router.get("/metrics/by-horizon")
def by_horizon():
    return metrics_by_horizon(ACT, FC).to_dict("records")


@router.get("/decision")
def decision(date: str):
    """date = delivery date (YYYY-MM-DD). Band historical error ke P10/P90 se."""
    m = overall_metrics(DF)
    day = DF[DF["startTime"].dt.strftime("%Y-%m-%d") == date].copy()
    day["startTime"] = day["startTime"].dt.strftime(FMT)
    rows = []
    for r in day.to_dict("records"):
        f = r["forecast"]
        rows.append({
            "startTime": r["startTime"], "forecast": f, "actual": r["actual"],
            "bias_adjusted": f - m["p50"],
            "low": f - m["p90"], "high": f - m["p10"],  # actual = forecast - error
        })
    return {"date": date, "error_stats": m, "hours": rows}


app.include_router(router)