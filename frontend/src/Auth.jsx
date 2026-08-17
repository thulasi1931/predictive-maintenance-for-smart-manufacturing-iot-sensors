import React, { useState } from "react";

const API = typeof window !== "undefined" && window.location.port === "5173" ? "http://127.0.0.1:5000" : "";

export default function Auth({ onAuthenticated }) {
  const [mode, setMode] = useState("login"); // "login" | "signup" | "forgot" | "reset"
  const [form, setForm] = useState({ name: "", email: "", password: "", confirmPassword: "", otp: "" });
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const update = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  async function handleLoginOrSignup(event) {
    event.preventDefault();
    setMessage("");
    if (mode === "signup" && form.password !== form.confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      const endpoint = mode === "login" ? "/login" : "/signup";
      const body = mode === "login" ? { email: form.email, password: form.password } : { name: form.name, email: form.email, password: form.password };
      const response = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) {
        setMessage(data.error || "Authentication request failed.");
        return;
      }
      if (mode === "signup") {
        setMessage("Account created successfully. You can now sign in.");
        setMode("login");
        return;
      }
      onAuthenticated({ name: data.name, email: data.email });
    } catch (err) {
      setMessage("Unable to connect to the server.");
    } finally {
      setLoading(false);
    }
  }

  async function requestOtp(event) {
    if (event) event.preventDefault();
    if (!form.email || !form.email.includes("@")) {
      setMessage("Please enter your registered email address first.");
      return;
    }
    setMessage("Generating and sending 6-digit OTP...");
    setLoading(true);
    try {
      const response = await fetch(`${API}/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: form.email.trim() }),
      });
      const data = await response.json();
      setMessage(data.message || data.error);
      if (response.ok) {
        setMode("reset");
      }
    } catch (err) {
      setMessage("Failed to request OTP. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleResetPassword(event) {
    event.preventDefault();
    setMessage("");
    if (!form.otp || form.otp.trim().length < 4) {
      setMessage("Please enter the OTP received.");
      return;
    }
    if (form.password.length < 6) {
      setMessage("New password must be at least 6 characters.");
      return;
    }
    if (form.password !== form.confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${API}/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.email.trim(),
          otp: form.otp.trim(),
          password: form.password,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        setMessage(data.error || "Failed to reset password.");
        return;
      }
      setMessage("Password reset successfully! Please sign in with your new password.");
      setMode("login");
      update("password", "");
      update("confirmPassword", "");
      update("otp", "");
    } catch (err) {
      setMessage("Unable to connect to the server.");
    } finally {
      setLoading(false);
    }
  }

  const title =
    mode === "login"
      ? "Welcome back"
      : mode === "signup"
      ? "Create your account"
      : mode === "forgot"
      ? "Forgot Password"
      : "Reset password with OTP";

  return (
    <main className="auth-page">
      <div className="auth-card">
        <p>MAINTAI PLATFORM</p>
        <h1>{title}</h1>
        <span>Smart manufacturing predictive maintenance</span>

        {mode === "login" && (
          <form onSubmit={handleLoginOrSignup} style={{ display: "grid", gap: "16px", marginTop: "12px" }}>
            <label>
              Email address
              <input
                type="email"
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                placeholder="technician@factory.com"
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                placeholder="••••••••"
                required
              />
            </label>
            <button type="submit" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </button>
            {message && <b className="notice">{message}</b>}
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px" }}>
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  setMode("signup");
                  setMessage("");
                }}
              >
                New here? Sign up
              </button>
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  setMode("forgot");
                  setMessage("");
                }}
              >
                Forgot password?
              </button>
            </div>
          </form>
        )}

        {mode === "signup" && (
          <form onSubmit={handleLoginOrSignup} style={{ display: "grid", gap: "16px", marginTop: "12px" }}>
            <label>
              Full name
              <input
                value={form.name}
                onChange={(e) => update("name", e.target.value)}
                placeholder="Jane Doe"
                required
              />
            </label>
            <label>
              Email address
              <input
                type="email"
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                placeholder="technician@factory.com"
                required
              />
            </label>
            <label>
              Password (min 6 characters)
              <input
                type="password"
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                placeholder="••••••••"
                minLength="6"
                required
              />
            </label>
            <label>
              Confirm password
              <input
                type="password"
                value={form.confirmPassword}
                onChange={(e) => update("confirmPassword", e.target.value)}
                placeholder="••••••••"
                minLength="6"
                required
              />
            </label>
            <button type="submit" disabled={loading}>
              {loading ? "Creating account..." : "Sign up"}
            </button>
            {message && <b className="notice">{message}</b>}
            <button
              type="button"
              className="link-button"
              onClick={() => {
                setMode("login");
                setMessage("");
              }}
            >
              Already have an account? Sign in
            </button>
          </form>
        )}

        {mode === "forgot" && (
          <form onSubmit={requestOtp} style={{ display: "grid", gap: "16px", marginTop: "12px" }}>
            <p style={{ color: "#475467", fontSize: "0.88rem", margin: 0 }}>
              Enter your registered email address. We will generate and email a 6-digit OTP to reset your password.
            </p>
            <label>
              Registered Email
              <input
                type="email"
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                placeholder="technician@factory.com"
                required
              />
            </label>
            <button type="submit" disabled={loading}>
              {loading ? "Generating OTP..." : "Generate & Send OTP"}
            </button>
            {message && <b className="notice">{message}</b>}
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: "8px" }}>
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  setMode("login");
                  setMessage("");
                }}
              >
                Back to Sign in
              </button>
              <button
                type="button"
                className="link-button"
                onClick={() => {
                  setMode("reset");
                  setMessage("");
                }}
              >
                Already have OTP?
              </button>
            </div>
          </form>
        )}

        {mode === "reset" && (
          <form onSubmit={handleResetPassword} style={{ display: "grid", gap: "16px", marginTop: "12px" }}>
            <label>
              Email address
              <input
                type="email"
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                placeholder="technician@factory.com"
                required
              />
            </label>
            <label>
              6-Digit OTP
              <input
                value={form.otp}
                onChange={(e) => update("otp", e.target.value)}
                placeholder="e.g. 583920"
                required
              />
            </label>
            <label>
              New password (min 6 characters)
              <input
                type="password"
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                placeholder="••••••••"
                minLength="6"
                required
              />
            </label>
            <label>
              Confirm new password
              <input
                type="password"
                value={form.confirmPassword}
                onChange={(e) => update("confirmPassword", e.target.value)}
                placeholder="••••••••"
                minLength="6"
                required
              />
            </label>
            <button type="submit" disabled={loading}>
              {loading ? "Resetting password..." : "Reset password"}
            </button>
            <button
              type="button"
              onClick={requestOtp}
              disabled={loading}
              style={{ background: "#475467" }}
            >
              Resend OTP
            </button>
            {message && <b className="notice">{message}</b>}
            <button
              type="button"
              className="link-button"
              onClick={() => {
                setMode("login");
                setMessage("");
              }}
            >
              Back to Sign in
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
