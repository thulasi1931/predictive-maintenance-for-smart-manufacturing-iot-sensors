import React from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function SensorGraph({ title, data, dataKey, color, unit }) {
  return (
    <article className="panel analysis-chart">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <XAxis dataKey="created_at" hide />
          <YAxis unit={unit} />
          <Tooltip />
          <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={3} dot />
        </LineChart>
      </ResponsiveContainer>
    </article>
  );
}

export default function Analysis({ predictions, machineId, onBack }) {
  const chartData = [...predictions].reverse();
  return (
    <main>
      <header><div><p className="eyebrow">MACHINE TELEMETRY</p><h1>Sensor Analysis</h1></div><button onClick={onBack}>Back to dashboard</button></header>
      <section className="intro"><h2>{machineId ? `Analysis for ${machineId}` : "All machine readings"}</h2><p>Each sensor has its own graph so maintenance patterns are easy to compare.</p></section>
      {chartData.length ? <section className="analysis-grid">
        <SensorGraph title="Air temperature" data={chartData} dataKey="air_temperature" color="#0ea5e9" unit=" K" />
        <SensorGraph title="Process temperature" data={chartData} dataKey="process_temperature" color="#f97316" unit=" K" />
        <SensorGraph title="Rotational speed" data={chartData} dataKey="rotational_speed" color="#4f46e5" unit=" rpm" />
        <SensorGraph title="Torque" data={chartData} dataKey="torque" color="#dc2626" unit=" Nm" />
        <SensorGraph title="Tool wear" data={chartData} dataKey="tool_wear" color="#16a34a" unit=" min" />
        <SensorGraph title="Failure probability" data={chartData.map((item) => ({ ...item, risk: item.failure_probability * 100 }))} dataKey="risk" color="#9333ea" unit="%" />
      </section> : <article className="panel"><p>No readings found. Predict or simulate readings first, then select a machine on the dashboard.</p></article>}
    </main>
  );
}
