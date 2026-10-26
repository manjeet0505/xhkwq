from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CUTOFF_HOUR_UTC = 9  # D-1 09:00 UTC. Jan = GMT, so UTC == UK local time.
MAPE_MIN_ACTUAL = 1000  # MW, MAPE sirf iske upar ke actuals pe


def load_data():
    actuals = pd.read_csv(DATA_DIR / "actuals.csv", parse_dates=["startTime"])
    forecasts = pd.read_csv(DATA_DIR / "forecasts.csv", parse_dates=["startTime", "publishTime"])
    return actuals, forecasts


def day_ahead_forecast(actuals, forecasts, cutoff_hour=CUTOFF_HOUR_UTC):
    """Har target startTime ke liye wo forecast jo D-1 cutoff tak ka latest tha."""
    f = forecasts.copy()
    day = f["startTime"].dt.floor("D")
    f["cutoff"] = day - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff_hour)
    f = f[f["publishTime"] <= f["cutoff"]]
    if f.empty:
        return pd.DataFrame()
    best = f.loc[f.groupby("startTime")["publishTime"].idxmax()]
    best = best.rename(columns={"generation": "forecast"})
    a = actuals.rename(columns={"generation": "actual"})
    df = a.merge(best[["startTime", "publishTime", "cutoff", "forecast"]], on="startTime", how="inner")
    df["horizon_h"] = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600
    df = df[(df["cutoff"] >= pd.Timestamp("2026-01-01", tz="UTC")) &
            (df["cutoff"] < pd.Timestamp("2026-02-01", tz="UTC"))]
    df["error"] = df["forecast"] - df["actual"]
    df["abs_error"] = df["error"].abs()
    return df.sort_values("startTime").reset_index(drop=True)


def overall_metrics(df):
    if df.empty:
        return {}
    big = df[df["actual"] >= MAPE_MIN_ACTUAL]
    return {
        "n": int(len(df)),
        "mae": float(df["abs_error"].mean()),
        "rmse": float(np.sqrt((df["error"] ** 2).mean())),
        "bias": float(df["error"].mean()),
        "mape": float((big["abs_error"] / big["actual"]).mean() * 100) if len(big) else None,
        "p10": float(df["error"].quantile(0.10)),
        "p50": float(df["error"].quantile(0.50)),
        "p90": float(df["error"].quantile(0.90)),
    }


def metrics_by_hour(df):
    g = df.groupby(df["startTime"].dt.hour)
    out = g.agg(mae=("abs_error", "mean"), bias=("error", "mean"), n=("error", "size")).reset_index()
    return out.rename(columns={"startTime": "hour"})


def metrics_by_horizon(actuals, forecasts, bin_h=6):
    """Saare forecasts (sirf cutoff wale nahi) vs actual, horizon bins mein."""
    a = actuals.rename(columns={"generation": "actual"})
    df = forecasts.rename(columns={"generation": "forecast"}).merge(a, on="startTime", how="inner")
    df["horizon_h"] = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600
    df = df[df["horizon_h"] >= 0]
    df["error"] = df["forecast"] - df["actual"]
    df["abs_error"] = df["error"].abs()
    df["bin"] = (df["horizon_h"] // bin_h * bin_h).astype(int)
    out = df.groupby("bin").agg(mae=("abs_error", "mean"), bias=("error", "mean"), n=("error", "size")).reset_index()
    out["label"] = out["bin"].astype(str) + "-" + (out["bin"] + bin_h).astype(str) + "h"
    return out