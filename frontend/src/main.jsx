import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Analysis from "./Analysis";
import Auth from "./Auth";
import Metrics from "./Metrics";
import "./styles.css";

const API = typeof window !== "undefined" && window.location.port === "5173" ? "http://127.0.0.1:5000" : "";
const initialReading = { machine_id: "M14860", type: "M", air_temperature: 300.1, process_temperature: 310.6, rotational_speed: 1500, torque: 40, tool_wear: 100 };
const sensors = [["air_temperature", "Air temperature (K)"], ["process_temperature", "Process temperature (K)"], ["rotational_speed", "Rotational speed (rpm)"], ["torque", "Torque (Nm)"], ["tool_wear", "Tool wear (min)"]];

function Sidebar({ page, setPage, onLogout, theme, toggleTheme }) {
  return <aside className="sidebar"><div className="brand">Maint<span>AI</span><small>Predictive maintenance</small></div><nav>{[["dashboard", "Dashboard"], ["analysis", "Sensor analysis"], ["alerts", "Maintenance alerts"], ["workorders", "Work orders"], ["assets", "Add future machine"], ["metrics", "Model performance"], ["settings", "Email settings"]].map(([key, label]) => <button className={page === key ? "active" : ""} onClick={() => setPage(key)} key={key}>{label}</button>)}</nav><button className="theme-toggle" onClick={toggleTheme}>{theme === "dark" ? "☀ Light mode" : "☾ Dark mode"}</button><button className="logout" onClick={onLogout}>Sign out</button><p className="sidebar-note">AI4I Product IDs are used as asset IDs because this dataset has no machine-ID column.</p></aside>;
}

function App({ onLogout, theme, toggleTheme }) {
  const [page, setPage] = useState("dashboard");
  const [reading, setReading] = useState(initialReading);
  const [result, setResult] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [history, setHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [workOrders, setWorkOrders] = useState([]);
  const [workOrder, setWorkOrder] = useState({ machine_id: "M14860", title: "Inspect machine after risk alert", priority: "High", assigned_to: "" });
  const [assets, setAssets] = useState([]);
  const [search, setSearch] = useState("M14860");
  const [compareA, setCompareA] = useState("torque");
  const [compareB, setCompareB] = useState("tool_wear");
  const [settings, setSettings] = useState({ email_enabled: false, email_recipient: "" });
  const [metrics, setMetrics] = useState(null);
  const [newAsset, setNewAsset] = useState({ asset_id: "CNC-001", asset_name: "New CNC Milling Machine", product_type: "M" });
  const [notice, setNotice] = useState("");
  const [simulating, setSimulating] = useState(false);
  const timer = useRef(null);

  async function loadHistory(assetId = search) { const r = await fetch(`${API}/history?machine_id=${encodeURIComponent(assetId)}`); if (r.ok) setHistory(await r.json()); }
  async function loadForecast(assetId = search) { setNotice(""); const r = await fetch(`${API}/forecast?machine_id=${encodeURIComponent(assetId)}`); const data = await r.json(); if (!r.ok) { setForecast(null); setNotice(data.error || "Unable to create a trend forecast."); return; } setForecast(data); }
  async function loadAlerts() { const r = await fetch(`${API}/alerts`); if (r.ok) setAlerts(await r.json()); }
  async function loadWorkOrders() { const r = await fetch(`${API}/work-orders`); if (r.ok) setWorkOrders(await r.json()); }
  async function loadSettings() { const r = await fetch(`${API}/notification-settings`); if (r.ok) setSettings(await r.json()); }
  async function loadMetrics() { const r = await fetch(`${API}/model-metrics`); if (r.ok) setMetrics(await r.json()); }
  async function searchAssets(value) { setSearch(value); const r = await fetch(`${API}/assets?q=${encodeURIComponent(value)}`); if (r.ok) setAssets(await r.json()); }
  async function loadSelectedAsset() {
    await loadHistory(search);
    const response = await fetch(`${API}/assets/${encodeURIComponent(search)}`);
    if (!response.ok) { setNotice("Asset not found. Choose an AI4I Product ID or add a future machine."); return; }
    const asset = await response.json();
    if (asset.air_temperature !== undefined) {
      setReading({ machine_id: asset.asset_id, type: asset.product_type, air_temperature: asset.air_temperature, process_temperature: asset.process_temperature, rotational_speed: asset.rotational_speed, torque: asset.torque, tool_wear: asset.tool_wear });
      setNotice(`Loaded original AI4I telemetry for ${asset.asset_id}.`);
    } else {
      setReading((old) => ({ ...old, machine_id: asset.asset_id, type: asset.product_type }));
      setNotice(`Loaded ${asset.asset_id}. Enter its first live sensor values.`);
    }
  }
  useEffect(() => { loadHistory(); loadAlerts(); loadWorkOrders(); loadSettings(); loadMetrics(); searchAssets("M14860"); return () => clearInterval(timer.current); }, []);

  function updateReading(event) { const { name, value } = event.target; setReading((old) => ({ ...old, [name]: value })); }
  async function predict(event) { event?.preventDefault(); setNotice(""); const payload = { ...reading, air_temperature: Number(reading.air_temperature), process_temperature: Number(reading.process_temperature), rotational_speed: Number(reading.rotational_speed), torque: Number(reading.torque), tool_wear: Number(reading.tool_wear) }; const r = await fetch(`${API}/predict`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); const data = await r.json(); if (!r.ok) { setNotice(data.error); return; } setResult(data); setSearch(payload.machine_id); loadHistory(payload.machine_id); loadAlerts(); }
  function simulateReading() { const air = +(298 + Math.random() * 4).toFixed(1); return { machine_id: reading.machine_id, type: reading.type, air_temperature: air, process_temperature: +(air + 8 + Math.random() * 4).toFixed(1), rotational_speed: Math.round(1200 + Math.random() * 700), torque: +(25 + Math.random() * 40).toFixed(1), tool_wear: Math.round(Math.random() * 250) }; }
  function toggleSimulation() { if (simulating) { clearInterval(timer.current); setSimulating(false); return; } const run = () => { const next = simulateReading(); setReading(next); predict({ preventDefault() { } }); }; run(); timer.current = setInterval(run, 5000); setSimulating(true); }
  async function resolveAlert(id) { await fetch(`${API}/alerts/${id}/resolve`, { method: "POST" }); loadAlerts(); }
  async function createWorkOrder(event) { event.preventDefault(); const r = await fetch(`${API}/work-orders`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(workOrder) }); const data = await r.json(); setNotice(data.message || data.error); if (r.ok) loadWorkOrders(); }
  async function setWorkOrderStatus(id, status) { const r = await fetch(`${API}/work-orders/${id}/status`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status }) }); const data = await r.json(); setNotice(data.message || data.error); loadWorkOrders(); }
  async function saveSettings(event) {
    event.preventDefault();
    const r = await fetch(`${API}/notification-settings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...settings,
        email_enabled: Boolean(settings.email_enabled),
      }),
    });
    const data = await r.json();
    setNotice(data.message || data.error);
    loadSettings();
  }
  async function sendTestEmail() {
    setNotice("Sending test email...");
    const r = await fetch(`${API}/email-test`, { method: "POST" });
    const data = await r.json();
    setNotice(data.message || data.error);
  }
  async function addFutureMachine(event) { event.preventDefault(); const r = await fetch(`${API}/assets`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(newAsset) }); const data = await r.json(); setNotice(data.message || data.error); if (r.ok) { setSearch(newAsset.asset_id); setReading((old) => ({ ...old, machine_id: newAsset.asset_id, type: newAsset.product_type })); searchAssets(newAsset.asset_id); } }
  const chartData = [...history].reverse();
  const sensorOptions = sensors.map(([key, label]) => <option value={key} key={key}>{label}</option>);

  let body;
  if (page === "analysis") body = <Analysis predictions={history} machineId={search} onBack={() => setPage("dashboard")} />;
  else if (page === "alerts") body = <section><section className="page-title"><div><p>MAINTENANCE WORKFLOW</p><h1>Open maintenance alerts</h1></div></section><div className="alert-list">{alerts.length ? alerts.map((alert) => <article className={`card alert ${alert.severity.toLowerCase()}`} key={alert.id}><b>{alert.severity}</b><h3>{alert.message}</h3><p>{(alert.failure_probability * 100).toFixed(2)}% risk · {alert.created_at}</p><button onClick={() => resolveAlert(alert.id)}>Mark resolved</button></article>) : <article className="card">No open alerts.</article>}</div></section>;
  else if (page === "workorders") body = <section className="settings"><section className="page-title"><div><p>MAINTENANCE WORKFLOW</p><h1>Work orders</h1><span>Assign model findings to technicians and track completion.</span></div></section><form className="card work-order-form" onSubmit={createWorkOrder}><label>Machine ID<input value={workOrder.machine_id} onChange={(e) => setWorkOrder({ ...workOrder, machine_id: e.target.value })} required /></label><label>Task title<input value={workOrder.title} onChange={(e) => setWorkOrder({ ...workOrder, title: e.target.value })} required /></label><label>Priority<select value={workOrder.priority} onChange={(e) => setWorkOrder({ ...workOrder, priority: e.target.value })}><option>Low</option><option>Warning</option><option>High</option><option>Critical</option></select></label><label>Assign to<input value={workOrder.assigned_to} onChange={(e) => setWorkOrder({ ...workOrder, assigned_to: e.target.value })} placeholder="Technician name" /></label><button>Create work order</button></form><div className="alert-list work-order-list">{workOrders.length ? workOrders.map((item) => <article className="card" key={item.id}><b>{item.priority} · {item.status}</b><h3>{item.machine_id}: {item.title}</h3><p>Assigned: {item.assigned_to || "Unassigned"}</p><div className="work-order-actions">{item.status === "Open" && <button onClick={() => setWorkOrderStatus(item.id, "In progress")}>Start work</button>}{item.status !== "Completed" && <button onClick={() => setWorkOrderStatus(item.id, "Completed")}>Mark completed</button>}</div></article>) : <article className="card">No work orders yet.</article>}</div></section>;
  else if (page === "assets") body = <section className="settings"><section className="page-title"><div><p>FUTURE EXPANSION</p><h1>Add a future machine</h1><span>Register a new machine now; its telemetry can be predicted using the existing model.</span></div></section><form className="card" onSubmit={addFutureMachine}><label>Future asset ID<input value={newAsset.asset_id} onChange={(e) => setNewAsset({ ...newAsset, asset_id: e.target.value })} required /></label><label>Machine name<input value={newAsset.asset_name} onChange={(e) => setNewAsset({ ...newAsset, asset_name: e.target.value })} required /></label><label>Expected product quality type<select value={newAsset.product_type} onChange={(e) => setNewAsset({ ...newAsset, product_type: e.target.value })}><option>L</option><option>M</option><option>H</option></select></label><button>Add machine</button></form></section>;
  else if (page === "metrics") body = <Metrics metrics={metrics} />;
  else if (page === "settings") body = <section className="settings"><section className="page-title"><div><p>NOTIFICATION CONTROL</p><h1>Email alert configuration</h1><span>Trigger alerts when machine risk reaches 60%+ more than 2 times.</span></div></section><form className="card" onSubmit={saveSettings}><label className="checkbox"><input type="checkbox" checked={Boolean(settings.email_enabled)} onChange={(e) => setSettings((old) => ({ ...old, email_enabled: e.target.checked }))} /> Enable automatic high-risk email alerts</label><label>Alert recipient email<input type="email" value={settings.email_recipient || ""} onChange={(e) => setSettings((old) => ({ ...old, email_recipient: e.target.value }))} placeholder="maintenance-lead@factory.com" required /></label><label>Sender Gmail address<input type="email" value={settings.smtp_username || ""} onChange={(e) => setSettings((old) => ({ ...old, smtp_username: e.target.value }))} placeholder="yourname@gmail.com" /></label><label>Gmail 16-character App Password<input type="password" value={settings.smtp_password || ""} onChange={(e) => setSettings((old) => ({ ...old, smtp_password: e.target.value }))} placeholder={settings.smtp_password_set ? "•••••••••••••••• (Saved)" : "Enter 16-character App Password"} /></label><div style={{ display: 'flex', gap: '10px', marginTop: '6px' }}><button type="submit">Save settings</button><button type="button" onClick={sendTestEmail} style={{ background: '#475467' }}>Send test email</button></div></form></section>;
  else body = (
    <>
      <section className="page-title">
        <div>
          <p>LIVE OPERATIONS</p>
          <h1>Machine health overview</h1>
          <span>Use a real AI4I Product ID, enter readings, and predict failure risk.</span>
        </div>
        <button className={simulating ? "danger-button" : ""} onClick={toggleSimulation}>
          {simulating ? "Stop simulation" : "Start live simulation"}
        </button>
      </section>

      <section className="search-panel">
        <label>
          Search dataset asset / Product ID
          <input list="asset-ids" value={search} onChange={(e) => searchAssets(e.target.value)} placeholder="Example: M14860" />
        </label>
        <datalist id="asset-ids">
          {assets.map((asset) => (
            <option value={asset.asset_id} key={asset.asset_id}>
              {asset.product_type} quality
            </option>
          ))}
        </datalist>
        <button onClick={loadSelectedAsset}>Load telemetry</button>
        <small>Examples: M14860, L47181</small>
      </section>

      <div className="layout">
        <form className="card telemetry" onSubmit={predict}>
          <h2>Current telemetry</h2>
          <label>
            Asset / Product ID
            <input name="machine_id" value={reading.machine_id} onChange={updateReading} required />
          </label>
          <label>
            Product quality type
            <select name="type" value={reading.type} onChange={updateReading}>
              <option>L</option>
              <option>M</option>
              <option>H</option>
            </select>
          </label>
          {sensors.map(([key, label]) => (
            <label key={key}>
              {label}
              <input name={key} type="number" step="0.1" value={reading[key]} onChange={updateReading} required />
            </label>
          ))}
          <button>Run ML prediction</button>
        </form>

        <section className="main-column">
          <article className={`card result ${result?.machine_failure ? "risk" : "healthy"}`}>
            <p>PREDICTION</p>
            <h2>{result?.prediction || "Awaiting reading"}</h2>
            <b>{result ? `${result.failure_probability_percent}%` : "—"}</b>
            <span>failure probability</span>

            {result && (
              <>
                <div className="risk-gauge-container">
                  <div className="risk-gauge-bar">
                    <div
                      className={`risk-gauge-fill ${
                        result.failure_probability >= 0.60
                          ? "gauge-critical"
                          : result.failure_probability >= 0.40
                          ? "gauge-warning"
                          : "gauge-healthy"
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, result.failure_probability_percent))}%` }}
                    />
                  </div>
                  <div className="risk-gauge-labels">
                    <span>0% Safe</span>
                    <span>40% Warning</span>
                    <span>60% Critical Trigger</span>
                    <span>100% Failure</span>
                  </div>
                </div>

                {result.consecutive_high_risk_readings > 0 && (
                  <div className="streak-badge">
                    ⚠ High Risk Streak: <b>{result.consecutive_high_risk_readings} consecutive reading(s)</b> (&ge; 60% risk)
                    {result.streak_timestamp && <span> · Last: {result.streak_timestamp}</span>}
                    {result.email_alert_triggered && (
                      <div className="email-sent-badge">✉ High-Risk Email Alert Dispatched to Maintenance Team!</div>
                    )}
                  </div>
                )}

                <div className="impact">
                  <strong>{result.machine_id} · {result.maintenance_priority} priority</strong>
                  <span>Cost at risk: ${result.estimated_downtime_cost_at_risk_usd.toLocaleString()}</span>
                </div>

                <h3>Why this result?</h3>
                <ul>
                  {result.risk_factors.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>

                {result.machine_failure === 1 && (
                  <p>
                    <strong>Likely failure:</strong> {result.most_likely_failure_type || "Under investigation"}
                  </p>
                )}
              </>
            )}
          </article>

          <article className="card comparison">
            <h2>Compare two sensors: {search || "selected asset"}</h2>
            <div className="select-row">
              <select value={compareA} onChange={(e) => setCompareA(e.target.value)}>
                {sensorOptions}
              </select>
              <select value={compareB} onChange={(e) => setCompareB(e.target.value)}>
                {sensorOptions}
              </select>
            </div>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={chartData}>
                <XAxis dataKey="created_at" hide />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey={compareA} stroke="#2563eb" strokeWidth={3} name={compareA} />
                <Line type="monotone" dataKey={compareB} stroke="#f97316" strokeWidth={3} name={compareB} />
              </LineChart>
            </ResponsiveContainer>
          </article>

          <article className="card forecast-card">
            <div className="card-heading"><div><h2>Next-reading trend forecast</h2><span>Uses the last 3–10 saved readings for this asset, then estimates its next failure risk.</span></div><button onClick={() => loadForecast(search)}>Forecast next reading</button></div>
            {forecast ? <div className={forecast.forecast_failure_probability >= 0.5 ? "forecast-risk" : "forecast-normal"}><h3>{forecast.forecast_prediction} · {forecast.forecast_failure_probability_percent}% estimated risk</h3><p>{forecast.method} ({forecast.readings_used} readings).</p><div className="forecast-values"><span>Air: <b>{forecast.forecast_reading.air_temperature} K</b></span><span>Process: <b>{forecast.forecast_reading.process_temperature} K</b></span><span>Speed: <b>{forecast.forecast_reading.rotational_speed} rpm</b></span><span>Torque: <b>{forecast.forecast_reading.torque} Nm</b></span><span>Tool wear: <b>{forecast.forecast_reading.tool_wear} min</b></span></div><small>{forecast.disclaimer}</small></div> : <p className="forecast-help">To create a forecast, submit three readings for the same machine or start the live simulation. The forecast then uses the most recent 3–10 readings.</p>}
          </article>

          {result?.machine_risk_history?.length > 0 && (
            <article className="card machine-risk-history">
              <h3>Machine {result.machine_id} Recent Risk Timeline</h3>
              <div className="risk-history-pills">
                {result.machine_risk_history.map((item, idx) => (
                  <span
                    key={item.id || idx}
                    className={`risk-pill ${
                      item.failure_probability >= 0.60
                        ? "pill-critical"
                        : item.failure_probability >= 0.40
                        ? "pill-warning"
                        : "pill-healthy"
                    }`}
                  >
                    <b>{item.failure_probability_percent}%</b>
                    <small>{item.created_at?.slice(11, 19) || `#${idx + 1}`}</small>
                  </span>
                ))}
              </div>
            </article>
          )}
        </section>
      </div>
    </>
  );
  return <div className="app" data-theme={theme}><Sidebar page={page} setPage={setPage} onLogout={onLogout} theme={theme} toggleTheme={toggleTheme} /><main className="content">{body}{notice && <p className="notice">{notice}</p>}</main></div>;
}

function Root() {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem("maintai_user") || "null"));
  const [theme, setTheme] = useState(() => localStorage.getItem("maintai_theme") || "light");
  function toggleTheme() {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    localStorage.setItem("maintai_theme", next);
  }
  function signIn(account) { localStorage.setItem("maintai_user", JSON.stringify(account)); setUser(account); }
  function signOut() { localStorage.removeItem("maintai_user"); setUser(null); }
  return user ? <App onLogout={signOut} theme={theme} toggleTheme={toggleTheme} /> : <Auth onAuthenticated={signIn} />;
}

createRoot(document.getElementById("root")).render(<Root />);
