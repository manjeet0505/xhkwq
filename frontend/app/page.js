"use client";
import { useEffect, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  ComposedChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

const MIN = "2026-01-02"; // first delivery date (decision made on 1 Jan)
const MAX = "2026-02-01"; // last delivery date (decision made on 31 Jan)

const fmt = (n, d = 0) =>
  n == null ? "-" : Number(n).toLocaleString("en-GB", { maximumFractionDigits: d });

const tipFmt = (v) =>
  Array.isArray(v) ? v.map((x) => fmt(x)).join(" to ") : fmt(v);

const label = (iso) => iso.slice(5, 10) + " " + iso.slice(11, 16);

async function getJson(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error("API " + r.status);
  return r.json();
}

function Kpi({ label, value, unit, hint }) {
  return (
    <div className="kpi">
      <div className="v">
        {value} <small>{unit}</small>
      </div>
      <div className="l">{label}</div>
      <div className="h">{hint}</div>
    </div>
  );
}

export default function Page() {
  const [start, setStart] = useState(MIN);
  const [end, setEnd] = useState(MAX);
  const [metrics, setMetrics] = useState(null);
  const [series, setSeries] = useState([]);
  const [byHour, setByHour] = useState([]);
  const [byHorizon, setByHorizon] = useState([]);
  const [dDate, setDDate] = useState("2026-01-15");
  const [decision, setDecision] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const q = `?start=${start}&end=${end}`;
    Promise.all([
      getJson(`/api/metrics${q}`),
      getJson(`/api/series${q}`),
      getJson(`/api/metrics/by-hour${q}`),
    ])
      .then(([m, s, h]) => {
        setMetrics(m);
        setSeries(s.map((r) => ({ ...r, t: label(r.startTime) })));
        setByHour(h);
        setError("");
      })
      .catch((e) => setError(e.message));
  }, [start, end]);

  useEffect(() => {
    getJson("/api/metrics/by-horizon")
      .then(setByHorizon)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    getJson(`/api/decision?date=${dDate}`)
      .then((d) =>
        setDecision({
          ...d,
          hours: d.hours.map((h) => ({
            ...h,
            t: h.startTime.slice(11, 16),
            band: [h.low, h.high],
          })),
        })
      )
      .catch((e) => setError(e.message));
  }, [dDate]);

  const avg = (k) =>
    decision && decision.hours.length
      ? decision.hours.reduce((a, h) => a + h[k], 0) / decision.hours.length
      : null;

  return (
    <div className="wrap">
      <h1>UK Wind Forecast Reliability</h1>
      <div className="sub">
        Day-ahead purchase decisions, January 2026. Forecast = latest WINDFOR
        published before 09:00 UTC on D-1. Actuals = FUELHH (WIND). Source: Elexon.
      </div>

      {error && <div className="err">Error: {error}</div>}

      <div className="card">
        <div className="controls">
          <b>Delivery date range:</b>
          <label>
            From{" "}
            <input
              type="date"
              min={MIN}
              max={MAX}
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </label>
          <label>
            To{" "}
            <input
              type="date"
              min={MIN}
              max={MAX}
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </label>
        </div>
      </div>

      {metrics && (
        <div className="kpis">
          <Kpi label="MAE" value={fmt(metrics.mae)} unit="MW" hint="avg absolute error" />
          <Kpi label="RMSE" value={fmt(metrics.rmse)} unit="MW" hint="penalises big misses" />
          <Kpi label="Bias" value={fmt(metrics.bias)} unit="MW" hint="forecast - actual" />
          <Kpi label="MAPE" value={fmt(metrics.mape, 1)} unit="%" hint="actual >= 1000 MW" />
        </div>
      )}

      <div className="card">
        <h2>Actual vs day-ahead forecast</h2>
        <ResponsiveContainer width="100%" height={340}>
          <LineChart data={series}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="t" minTickGap={60} fontSize={11} />
            <YAxis fontSize={11} unit=" MW" width={80} />
            <Tooltip formatter={tipFmt} />
            <Legend />
            <Line dataKey="actual" name="Actual" stroke="#1f77b4" dot={false} strokeWidth={2} />
            <Line dataKey="forecast" name="Forecast (D-1 09:00)" stroke="#ff7f0e" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="grid2">
        <div className="card">
          <h2>Error by hour of day (UTC)</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={byHour}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" fontSize={11} />
              <YAxis fontSize={11} width={60} />
              <Tooltip formatter={tipFmt} />
              <Legend />
              <Bar dataKey="mae" name="MAE (MW)" fill="#2ca02c" />
              <Bar dataKey="bias" name="Bias (MW)" fill="#d62728" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2>Error by forecast horizon</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={byHorizon}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" fontSize={11} />
              <YAxis fontSize={11} width={60} />
              <Tooltip formatter={tipFmt} />
              <Legend />
              <Bar dataKey="mae" name="MAE (MW)" fill="#9467bd" />
              <Bar dataKey="bias" name="Bias (MW)" fill="#8c564b" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <h2>Decision view: wind for a delivery day</h2>
        <div className="controls" style={{ marginBottom: 12 }}>
          <label>
            Delivery date{" "}
            <input
              type="date"
              min={MIN}
              max={MAX}
              value={dDate}
              onChange={(e) => setDDate(e.target.value)}
            />
          </label>
        </div>

        {decision && decision.hours.length > 0 && (
          <>
            <div className="big">
              Avg forecast: <b>{fmt(avg("forecast"))} MW</b> | Bias-adjusted:{" "}
              <b>{fmt(avg("bias_adjusted"))} MW</b> | 80% range:{" "}
              <b>{fmt(avg("low"))}</b> to <b>{fmt(avg("high"))} MW</b>
            </div>
            <div className="plan">
              Conservative plan: assume wind at {fmt(avg("low"))} MW and cover the
              rest of demand from thermal plants or the market. Trusting the raw
              forecast would, on average, overstate wind by ~
              {fmt(decision.error_stats.bias)} MW.
            </div>
            <ResponsiveContainer width="100%" height={320}>
              <ComposedChart data={decision.hours}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="t" fontSize={11} />
                <YAxis fontSize={11} unit=" MW" width={80} />
                <Tooltip formatter={tipFmt} />
                <Legend />
                <Area dataKey="band" name="80% range" fill="#cfe3f7" stroke="none" />
                <Line dataKey="forecast" name="Forecast" stroke="#ff7f0e" dot={false} strokeWidth={2} />
                <Line dataKey="bias_adjusted" name="Bias-adjusted" stroke="#2ca02c" dot={false} strokeWidth={2} />
                <Line dataKey="actual" name="Actual (hindsight)" stroke="#1f77b4" dot={false} strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          </>
        )}
      </div>
    </div>
  );
}