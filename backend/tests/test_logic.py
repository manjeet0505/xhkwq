import pandas as pd
from app.logic import day_ahead_forecast, overall_metrics


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def make(actual_val=150):
    actuals = pd.DataFrame({"startTime": [ts("2026-01-10 12:00")], "generation": [actual_val]})
    forecasts = pd.DataFrame({
        "startTime": [ts("2026-01-10 12:00")] * 3,
        "publishTime": [ts("2026-01-09 02:30"), ts("2026-01-09 08:30"), ts("2026-01-09 11:30")],
        "generation": [100, 200, 300],
    })
    return actuals, forecasts


def test_picks_latest_before_cutoff():
    a, f = make()
    df = day_ahead_forecast(a, f)
    assert len(df) == 1
    assert df.loc[0, "forecast"] == 200  # 11:30 wala cutoff (09:00) ke baad tha


def test_ignores_forecast_after_cutoff_only():
    a, f = make()
    f = f[f["publishTime"] > ts("2026-01-09 09:00")]
    assert day_ahead_forecast(a, f).empty


def test_error_sign_forecast_minus_actual():
    a, f = make(actual_val=150)
    df = day_ahead_forecast(a, f)
    assert df.loc[0, "error"] == 50


def test_metrics():
    df = pd.DataFrame({"actual": [1000, 1000], "error": [10, -10], "abs_error": [10, 10]})
    m = overall_metrics(df)
    assert m["mae"] == 10 and m["bias"] == 0 and m["rmse"] == 10