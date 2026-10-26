import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATA_DIR.mkdir(exist_ok=True)


def get_json(url, params):
    r = requests.get(url, params=params, timeout=120)
    r.raise_for_status()
    return r.json()


def fetch_actuals():
    """FUELHH, WIND only, 1-31 Jan 2026, 7-day chunks."""
    rows = []
    cur = datetime(2026, 1, 1)
    end = datetime(2026, 1, 31)
    end = datetime(2026, 2, 1)
    while cur <= end:
        nxt = min(cur + timedelta(days=6), end)
        params = {
            "settlementDateFrom": cur.strftime("%Y-%m-%d"),
            "settlementDateTo": nxt.strftime("%Y-%m-%d"),
            "fuelType": "WIND",
        }
        data = get_json(f"{BASE}/FUELHH/stream", params)
        rows.extend(data)
        print(f"actuals {params['settlementDateFrom']} -> {params['settlementDateTo']}: {len(data)} rows")
        cur = nxt + timedelta(days=1)
    df = pd.DataFrame(rows)
    df = df[df["fuelType"] == "WIND"]
    df = df[["startTime", "generation"]].drop_duplicates("startTime")
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    return df.sort_values("startTime").reset_index(drop=True)


def fetch_forecasts():
    """WINDFOR, publishTime 25 Dec 2025 -> 31 Jan 2026, 2-day chunks."""
    rows = []
    cur = datetime(2025, 12, 25, tzinfo=timezone.utc)
    end = datetime(2026, 2, 1, tzinfo=timezone.utc)
    while cur < end:
        nxt = min(cur + timedelta(days=2), end)
        params = {
            "publishDateTimeFrom": cur.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": nxt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        data = get_json(f"{BASE}/WINDFOR/stream", params)
        rows.extend(data)
        print(f"forecasts {params['publishDateTimeFrom']}: {len(data)} rows")
        cur = nxt
    df = pd.DataFrame(rows)
    df = df[["startTime", "publishTime", "generation"]]
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = df.drop_duplicates(["startTime", "publishTime"])
    return df.sort_values(["startTime", "publishTime"]).reset_index(drop=True)


if __name__ == "__main__":
    actuals = fetch_actuals()
    actuals.to_csv(DATA_DIR / "actuals.csv", index=False)
    print("ACTUALS", actuals.shape)
    print(actuals.head(), actuals.tail(), sep="\n")

    forecasts = fetch_forecasts()
    forecasts.to_csv(DATA_DIR / "forecasts.csv", index=False)
    print("FORECASTS", forecasts.shape)
    print(forecasts.head(), forecasts.tail(), sep="\n")