import React, { useState } from "react";

const API = "";

export default function Auth({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "", confirmPassword: "", otp: "" });
  const [message, setMessage] = useState("");
  const update = (key, value) => setForm({ ...form, [key]: value });
  async function submit(event) {
    event.preventDefault(); setMessage("");
    if (mode === "signup" && form.password !== form.confirmPassword) { setMessage("Passwords do not match."); return; }
    const endpoint = mode === "login" ? "/login" : mode === "signup" ? "/signup" : "/reset-password";
    const body = mode === "reset" ? { email: form.email, otp: form.otp, password: form.password } : form;
    const response = await fetch(`${API}${endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await response.json(); if (!response.ok) { setMessage(data.error); return; }
    if (mode === "signup") { setMessage("Account created. Please sign in."); setMode("login"); return; }
    if (mode === "reset") { setMessage("Password reset. Please sign in."); setMode("login"); return; }
    onAuthenticated({ name: data.name, email: data.email });
  }
  async function requestOtp() { const response = await fetch(`${API}/forgot-password`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: form.email }) }); const data = await response.json(); setMessage(data.message || data.error); if (response.ok) setMode("reset"); }
  const title = mode === "login" ? "Welcome back" : mode === "signup" ? "Create your account" : "Reset password";
  return <main className="auth-page"><form className="auth-card" onSubmit={submit}><p>MAINTAI PLATFORM</p><h1>{title}</h1><span>Smart manufacturing predictive maintenance</span>{mode === "signup" && <label>Name<input value={form.name} onChange={(e) => update("name", e.target.value)} required /></label>}<label>Email<input type="email" value={form.email} onChange={(e) => update("email", e.target.value)} required /></label>{mode === "reset" && <label>OTP from email<input value={form.otp} onChange={(e) => update("otp", e.target.value)} required /></label>}<label>{mode === "reset" ? "New password" : "Password"}<input type="password" value={form.password} onChange={(e) => update("password", e.target.value)} minLength="6" required /></label>{mode === "signup" && <label>Re-enter password<input type="password" value={form.confirmPassword} onChange={(e) => update("confirmPassword", e.target.value)} minLength="6" required /></label>}<button>{mode === "login" ? "Sign in" : mode === "signup" ? "Sign up" : "Reset password"}</button>{mode === "reset" && <button type="button" onClick={requestOtp}>Send new OTP</button>}{message && <b className="notice">{message}</b>}<button type="button" className="link-button" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setMessage(""); }}>{mode === "login" ? "New here? Sign up" : "Back to sign in"}</button>{mode === "login" && <button type="button" className="link-button" onClick={() => { setMode("reset"); setMessage(""); }}>Forgot password?</button>}</form></main>;
}
