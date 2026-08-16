"""Flask API for the predictive-maintenance dashboard.

Run from the project folder with: python backend/app.py
"""

import sys
import json
import os
import smtplib
import secrets
import urllib.error
import urllib.request
import threading
from datetime import datetime, timezone
from pathlib import Path
from email.message import EmailMessage

import joblib
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.security import check_password_hash


PROJECT_DIRECTORY = Path(__file__).resolve().parents[1]

# Automatically load .env file if present
env_file_path = PROJECT_DIRECTORY / ".env"
if env_file_path.exists():
    for env_line in env_file_path.read_text(encoding="utf-8").splitlines():
        env_line = env_line.strip()
        if env_line and not env_line.startswith("#") and "=" in env_line:
            k, v = env_line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(PROJECT_DIRECTORY / "ml"))
sys.path.insert(0, str(PROJECT_DIRECTORY / "database"))
from feature_engineering import add_engineered_features  # noqa: E402
from database import (  # noqa: E402
    add_custom_asset, create_user, get_custom_assets, get_dashboard_summary, get_password_reset,
    get_recent_alerts, get_recent_predictions, get_user_by_email, initialise_database, get_notification_settings,
    get_recent_notifications, resolve_alert, save_alert, save_notification,
    save_notification_settings, save_password_reset, save_prediction, update_user_password,
    record_risk_streak,
)


MODEL_PATH = PROJECT_DIRECTORY / "artifacts" / "random_forest_failure_model.joblib"
FAILURE_TYPE_MODEL_PATH = PROJECT_DIRECTORY / "artifacts" / "failure_type_models.joblib"
ASSET_CATALOG_PATH = PROJECT_DIRECTORY / "artifacts" / "asset_catalog.json"
FAILURE_TYPE_NAMES = {
    "TWF": "Tool Wear Failure",
    "HDF": "Heat Dissipation Failure",
    "PWF": "Power Failure",
    "OSF": "Overstrain Failure",
    "RNF": "Random Failure",
}
REQUIRED_FIELDS = {
    "machine_id": str,
    "type": str,
    "air_temperature": float,
    "process_temperature": float,
    "rotational_speed": float,
    "torque": float,
    "tool_wear": float,
}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "hackathon-demo-change-me")

_model = None
_failure_type_models = None

def get_model():
    global _model
    if _model is None and MODEL_PATH.exists():
        loaded = joblib.load(MODEL_PATH)
        if hasattr(loaded, "named_steps") and "model" in loaded.named_steps:
            loaded.named_steps["model"].n_jobs = 1
        elif hasattr(loaded, "n_jobs"):
            loaded.n_jobs = 1
        _model = loaded
    return _model

def get_failure_type_models():
    global _failure_type_models
    if _failure_type_models is None and FAILURE_TYPE_MODEL_PATH.exists():
        loaded = joblib.load(FAILURE_TYPE_MODEL_PATH)
        for key, model_instance in loaded.items():
            if hasattr(model_instance, "named_steps") and "model" in model_instance.named_steps:
                model_instance.named_steps["model"].n_jobs = 1
            elif hasattr(model_instance, "n_jobs"):
                model_instance.n_jobs = 1
        _failure_type_models = loaded
    return _failure_type_models

initialise_database()

# Pre-warm ML models in background thread so predictions respond instantly
def _warmup_models():
    try:
        get_model()
        get_failure_type_models()
    except Exception as e:
        print(f"Model warmup warning: {e}")

threading.Thread(target=_warmup_models, daemon=True).start()


@app.after_request
def allow_frontend_requests(response):
    """Allow the local React dashboard to call this development API."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def validate_sensor_reading(payload: dict) -> dict:
    """Check and convert the incoming JSON reading into safe numeric values."""
    if not isinstance(payload, dict):
        raise ValueError("Request body must be JSON.")

    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    product_type = str(payload["type"]).upper()
    if product_type not in {"L", "M", "H"}:
        raise ValueError("type must be L, M, or H.")

    try:
        machine_id = str(payload["machine_id"]).strip().upper()
        if not machine_id:
            raise ValueError("machine_id cannot be empty.")
        return {
            "Machine ID": machine_id,
            "Type": product_type,
            "Air temperature [K]": float(payload["air_temperature"]),
            "Process temperature [K]": float(payload["process_temperature"]),
            "Rotational speed [rpm]": float(payload["rotational_speed"]),
            "Torque [Nm]": float(payload["torque"]),
            "Tool wear [min]": float(payload["tool_wear"]),
        }
    except (TypeError, ValueError) as error:
        raise ValueError("All sensor values must be valid numbers.") from error


@app.get("/health")
def health_check():
    """Confirm that the backend and trained model are ready."""
    return jsonify({"status": "ready", "model": "Random Forest"})


@app.get("/history")
def prediction_history():
    """Return recent saved predictions for the dashboard table or charts."""
    machine_id = request.args.get("machine_id", "").strip().upper() or None
    return jsonify(get_recent_predictions(machine_id=machine_id))


@app.get("/alerts")
def maintenance_alerts():
    """Return open maintenance alerts for the dashboard alert panel."""
    return jsonify(get_recent_alerts())


@app.get("/notifications")
def notification_history():
    """Return demo email and SMS records created for maintenance alerts."""
    return jsonify(get_recent_notifications())


@app.get("/assets")
def asset_search():
    """Search actual AI4I Product IDs for the dashboard asset picker."""
    query = request.args.get("q", "").strip().upper()
    if not ASSET_CATALOG_PATH.exists():
        return jsonify([])
    assets = json.loads(ASSET_CATALOG_PATH.read_text(encoding="utf-8"))
    matched_assets = [asset for asset in assets if asset["asset_id"].startswith(query)]
    return jsonify(matched_assets[:25] + get_custom_assets(query))


@app.get("/assets/<path:asset_id>")
def asset_details(asset_id: str):
    """Return static asset file if it exists in frontend/dist/assets, or return AI4I telemetry record."""
    frontend_assets_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist", "assets")
    asset_file_path = os.path.join(frontend_assets_dir, asset_id)
    if os.path.isfile(asset_file_path):
        return send_from_directory(frontend_assets_dir, asset_id)

    if ASSET_CATALOG_PATH.exists():
        assets = json.loads(ASSET_CATALOG_PATH.read_text(encoding="utf-8"))
        for asset in assets:
            if asset["asset_id"] == asset_id.upper():
                return jsonify(asset)
    custom_assets = get_custom_assets(asset_id)
    if custom_assets and custom_assets[0]["asset_id"] == asset_id.upper():
        return jsonify(custom_assets[0])
    return jsonify({"error": "Asset was not found."}), 404


@app.post("/assets")
def create_asset():
    """Add a future machine to the app without retraining the current model."""
    payload = request.get_json(silent=True) or {}
    asset_id = str(payload.get("asset_id", "")).strip().upper()
    asset_name = str(payload.get("asset_name", "")).strip()
    product_type = str(payload.get("product_type", "M")).upper()
    if not asset_id or not asset_name or product_type not in {"L", "M", "H"}:
        return jsonify({"error": "Provide asset ID, asset name, and product type L, M, or H."}), 400
    if not add_custom_asset(asset_id, asset_name, product_type):
        return jsonify({"error": "This asset ID already exists."}), 409
    return jsonify({"message": f"Future machine {asset_id} added."}), 201


@app.get("/model-metrics")
def model_metrics():
    """Expose saved training metrics so the dashboard can show model quality."""
    metrics_path = PROJECT_DIRECTORY / "artifacts" / "random_forest_metrics.json"
    if not metrics_path.exists():
        return jsonify({"error": "Model metrics file is unavailable."}), 404
    return jsonify(json.loads(metrics_path.read_text(encoding="utf-8")))


@app.post("/signup")
def signup():
    """Create a simple local account for the hackathon dashboard."""
    payload = request.get_json(silent=True) or {}
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip()
    password = str(payload.get("password", ""))
    if not name or "@" not in email or len(password) < 6:
        return jsonify({"error": "Enter name, valid email, and a password of at least 6 characters."}), 400
    if not create_user(name, email, password):
        return jsonify({"error": "An account already exists for this email."}), 409
    return jsonify({"message": "Account created. You can sign in now."}), 201


@app.post("/login")
def login():
    """Verify local demo account credentials."""
    payload = request.get_json(silent=True) or {}
    user = get_user_by_email(str(payload.get("email", "")))
    if not user or not check_password_hash(user["password_hash"], str(payload.get("password", ""))):
        return jsonify({"error": "Incorrect email or password."}), 401
    return jsonify({"name": user["name"], "email": user["email"], "message": "Signed in successfully."})


@app.post("/forgot-password")
def forgot_password():
    """Email a six-digit reset OTP when SMTP is configured."""
    email = str((request.get_json(silent=True) or {}).get("email", "")).strip()
    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "No account exists for this email."}), 404
    otp = f"{secrets.randbelow(1_000_000):06d}"
    save_password_reset(email, otp)
    status = send_email(email, "MaintAI password reset OTP", f"Your MaintAI OTP is {otp}. It expires in 10 minutes.")
    if status != "sent":
        return jsonify({"error": f"OTP was created but email failed: {status}"}), 503
    return jsonify({"message": "OTP sent to your email."})


@app.post("/reset-password")
def reset_password():
    """Verify a valid, unexpired OTP and update the local password hash."""
    payload = request.get_json(silent=True) or {}
    email = str(payload.get("email", "")).strip()
    otp = str(payload.get("otp", ""))
    password = str(payload.get("password", ""))
    reset_request = get_password_reset(email)
    if not reset_request or not check_password_hash(reset_request["otp_hash"], otp):
        return jsonify({"error": "Invalid OTP."}), 400
    if datetime.fromisoformat(reset_request["expires_at"]) < datetime.now(timezone.utc):
        return jsonify({"error": "OTP expired. Request a new one."}), 400
    if len(password) < 6:
        return jsonify({"error": "New password must have at least 6 characters."}), 400
    update_user_password(email, password)
    return jsonify({"message": "Password reset successfully. You can sign in now."})


@app.get("/notification-settings")
def read_notification_settings():
    """Return the selected email opt-in and SMTP configuration."""
    settings = get_notification_settings()
    # Mask password for security when sending to frontend
    safe_settings = dict(settings)
    if safe_settings.get("smtp_password"):
        safe_settings["smtp_password_set"] = True
        safe_settings["smtp_password"] = "••••••••••••••••"
    else:
        safe_settings["smtp_password_set"] = False
        safe_settings["smtp_password"] = ""
    return jsonify(safe_settings)


@app.get("/email-status")
def email_status():
    """Show whether the running Flask process received SMTP or Resend settings."""
    settings = get_notification_settings()
    username = os.getenv("SMTP_USERNAME") or os.getenv("EMAIL_USER") or settings.get("smtp_username", "")
    password = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_APP_PASSWORD") or settings.get("smtp_password", "")
    smtp_configured = bool(username and password)
    resend_configured = all(os.getenv(key) for key in ("RESEND_API_KEY", "EMAIL_FROM"))
    return jsonify({"smtp_configured": smtp_configured, "resend_configured": resend_configured, "sender_email": username})


@app.post("/notification-settings")
def update_notification_settings():
    """Save email opt-in, recipient, and optional SMTP credentials."""
    payload = request.get_json(silent=True) or {}
    recipient = str(payload.get("email_recipient", "")).strip()
    enabled = bool(payload.get("email_enabled", False))
    smtp_host = str(payload.get("smtp_host", "smtp.gmail.com")).strip() or "smtp.gmail.com"
    smtp_port = int(payload.get("smtp_port", 587) or 587)
    smtp_username = str(payload.get("smtp_username", "")).strip()
    smtp_password = str(payload.get("smtp_password", "")).strip()

    if enabled and ("@" not in recipient or "." not in recipient.rsplit("@", 1)[-1]):
        return jsonify({"error": "Enter a valid recipient email address before enabling notifications."}), 400

    # Don't overwrite existing password with mask
    if smtp_password.startswith("•"):
        smtp_password = ""

    save_notification_settings(enabled, recipient, smtp_host, smtp_port, smtp_username, smtp_password)
    return jsonify({"message": "Email & notification settings saved successfully."})


@app.post("/email-test")
def test_email_notification():
    """Send a user-requested test email to the opted-in recipient."""
    settings = get_notification_settings()
    recipient = settings.get("email_recipient", "").strip()
    if not recipient or "@" not in recipient:
        return jsonify({"error": "Please enter a valid recipient email address and save settings first."}), 400
    
    status = send_email(
        recipient,
        "MaintAI Test Alert: Predictive Maintenance Connected",
        "Hello!\n\nThis is a verified test notification from your MaintAI Smart IoT Predictive Maintenance System.\n\nEmail alerts are functioning properly. When any machine encounters a high-risk anomaly (Risk >= 60%) more than 2 consecutive times, you will automatically receive an incident alert with complete sensor telemetry snapshot.\n\nTimestamp: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    save_notification("Email", recipient, "MaintAI email notification test.", "Info", status)
    if "sent" in status.lower():
        return jsonify({"message": f"Success: Test email sent to {recipient}"})
    return jsonify({"error": status}), 400


@app.post("/alerts/<int:alert_id>/resolve")
def resolve_maintenance_alert(alert_id: int):
    """Mark an alert resolved after the maintenance team has inspected it."""
    if not resolve_alert(alert_id):
        return jsonify({"error": "Open alert not found."}), 404
    return jsonify({"message": "Alert marked as resolved."})


@app.get("/summary")
def dashboard_summary():
    """Return the counters shown at the top of the dashboard."""
    return jsonify(get_dashboard_summary())


def explain_risk(reading: dict) -> list[str]:
    """Give clear rule-based explanations alongside the ML probability."""
    factors = []
    temperature_gap = reading["Process temperature [K]"] - reading["Air temperature [K]"]
    if reading["Tool wear [min]"] >= 200:
        factors.append("Tool wear is high (200+ minutes).")
    if reading["Torque [Nm]"] >= 55:
        factors.append("Torque is high, indicating heavy machine load.")
    if reading["Rotational speed [rpm]"] <= 1300:
        factors.append("Rotational speed is low under load.")
    if temperature_gap >= 11:
        factors.append("Process-to-air temperature difference is high.")
    return factors or ["No single sensor exceeded the explanation thresholds."]


def build_alert_email_content(machine_id: str, risk_streak: int, risk_probability: float, cause: str, reading: dict, recommended_action: str) -> tuple[str, str]:
    """Create a rich, structured incident notification email."""
    subject = f"URGENT: Machine {machine_id} High Failure Risk Alert ({risk_probability * 100:.1f}%)"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    temp_diff = round(reading["Process temperature [K]"] - reading["Air temperature [K]"], 2)
    power = round((2 * 3.14159265 * reading["Rotational speed [rpm]"] * reading["Torque [Nm]"]) / 60, 2)

    body = f"""=======================================================
SMART MANUFACTURING PREDICTIVE MAINTENANCE ALERT
=======================================================

ALERT STATUS: CRITICAL - REPEATED HIGH RISK DETECTED
Machine / Asset ID:          {machine_id}
Current Failure Probability: {risk_probability * 100:.2f}%
Consecutive High-Risk Count: {risk_streak} (Threshold crossed: >2 times @ >=60% risk)
Trigger Timestamp:           {timestamp}
Most Likely Failure Mode:    {cause}

-------------------------------------------------------
SENSOR TELEMETRY SNAPSHOT
-------------------------------------------------------
- Air Temperature:           {reading['Air temperature [K]']} K
- Process Temperature:       {reading['Process temperature [K]']} K
- Temperature Differential:  {temp_diff} K
- Rotational Speed:          {reading['Rotational speed [rpm]']} rpm
- Torque:                    {reading['Torque [Nm]']} Nm
- Calculated Spindle Power:  {power} W
- Tool Wear Duration:        {reading['Tool wear [min]']} min
- Product Quality Type:      {reading['Type']}

-------------------------------------------------------
RECOMMENDED MAINTENANCE ACTION
-------------------------------------------------------
{recommended_action}
Please schedule an immediate physical diagnostic inspection of {machine_id} to prevent unscheduled breakdown.

=======================================================
Notification dispatched by MaintAI IoT Edge System
"""
    return subject, body


def send_email(recipient: str, subject: str, message: str) -> str:
    """Send real email via Resend API or SMTP (including Gmail App Password)."""
    # 1. Resend API if configured
    # Resend integration removed; using SMTP only

    # 2. SMTP / Gmail App Password
    settings = get_notification_settings()
    username = os.getenv("SMTP_USERNAME") or os.getenv("EMAIL_USER") or settings.get("smtp_username", "")
    password = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_APP_PASSWORD") or settings.get("smtp_password", "")
    host = os.getenv("SMTP_HOST") or settings.get("smtp_host", "smtp.gmail.com") or "smtp.gmail.com"
    port_val = os.getenv("SMTP_PORT") or settings.get("smtp_port", 587) or 587
    port = int(port_val)

    if not username or not password:
        return "SMTP not configured: Please enter your Gmail address and 16-character App Password in Settings tab or .env file."

    email = EmailMessage()
    email["From"] = username
    email["To"] = recipient
    email["Subject"] = subject
    email.set_content(message)
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=5) as server:
                server.login(username, password)
                server.send_message(email)
        else:
            with smtplib.SMTP(host, port, timeout=5) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(email)
        return "sent successfully via SMTP"
    except (OSError, smtplib.SMTPException) as error:
        return f"SMTP error ({error}). Verify your Gmail address and 16-char App Password."


@app.post("/predict")
def predict_failure():
    """Predict machine-failure risk from a single IoT sensor reading."""
    try:
        reading = validate_sensor_reading(request.get_json(silent=True))
        features = add_engineered_features(pd.DataFrame([reading]))
        loaded_model = get_model()
        if not loaded_model:
            return jsonify({"error": "ML model is loading or unavailable."}), 503
        risk_probability = float(loaded_model.predict_proba(features)[0, 1])
        will_fail = risk_probability >= 0.50

        # Email alert streak triggers when machine has risk >= 60% (0.60)
        is_high_risk_for_email = risk_probability >= 0.60
        settings = get_notification_settings()
        risk_streak, should_send_email, streak_updated_at = record_risk_streak(reading["Machine ID"], is_high_risk_for_email)
        
        priority = "Critical" if risk_probability >= 0.80 else "High" if risk_probability >= 0.60 else "Warning" if will_fail else "Low"
        downtime_cost_at_risk = round(risk_probability * 15000, 2)
        
        failure_type_probabilities = {}
        most_likely_failure_type = None
        likely_failure_types = []
        if will_fail:
            loaded_ft_models = get_failure_type_models()
            if loaded_ft_models:
                failure_type_probabilities = {
                    FAILURE_TYPE_NAMES[code]: round(float(type_model.predict_proba(features)[0, 1]), 4)
                    for code, type_model in loaded_ft_models.items()
                }
            likely_failure_types = [
                name for name, prob in failure_type_probabilities.items() if prob >= 0.50
            ]
            most_likely_failure_type = (
                max(failure_type_probabilities, key=failure_type_probabilities.get)
                if failure_type_probabilities else None
            )
        
        save_prediction(reading, int(will_fail), risk_probability)
        
        email_status_msg = None
        if will_fail:
            severity = "Critical" if risk_probability >= 0.80 else "Warning"
            cause = most_likely_failure_type or "Unknown failure type"
            save_alert(
                severity,
                f"{cause} risk detected. Schedule machine inspection.",
                risk_probability,
                most_likely_failure_type,
            )
            
        if should_send_email and settings.get("email_enabled") and settings.get("email_recipient"):
            cause = most_likely_failure_type or "Equipment Thermal/Load Anomaly"
            recommended_action = "Inspect the machine immediately and reduce spindle load/tool wear." if will_fail else "Perform preventive inspection."
            email_subject, email_body = build_alert_email_content(
                reading["Machine ID"],
                risk_streak,
                risk_probability,
                cause,
                reading,
                recommended_action,
            )
            email_status_msg = "dispatched in background"
            def _async_email_worker():
                status = send_email(settings["email_recipient"], email_subject, email_body)
                save_notification("Email", settings["email_recipient"], email_body, "Critical", status)
            threading.Thread(target=_async_email_worker, daemon=True).start()

        # Get recent 6 predictions for machine-level risk history
        recent_machine_preds = get_recent_predictions(limit=6, machine_id=reading["Machine ID"])
        machine_risk_history = [
            {
                "id": p["id"],
                "created_at": p["created_at"],
                "failure_probability": p["failure_probability"],
                "failure_probability_percent": round(p["failure_probability"] * 100, 1),
                "is_failure": bool(p["machine_failure"]),
            }
            for p in recent_machine_preds
        ]

        return jsonify({
            "prediction": "Failure Risk" if will_fail else "Normal",
            "machine_failure": int(will_fail),
            "failure_probability": round(risk_probability, 4),
            "failure_probability_percent": round(risk_probability * 100, 2),
            "machine_id": reading["Machine ID"],
            "maintenance_priority": priority,
            "consecutive_high_risk_readings": risk_streak,
            "streak_timestamp": streak_updated_at,
            "email_alert_triggered": should_send_email and bool(settings.get("email_enabled")),
            "email_delivery_status": email_status_msg,
            "estimated_downtime_cost_at_risk_usd": downtime_cost_at_risk,
            "risk_factors": explain_risk(reading),
            "recommended_action": "Inspect the machine immediately." if will_fail else "Continue monitoring the machine.",
            "most_likely_failure_type": most_likely_failure_type if will_fail else None,
            "likely_failure_types": likely_failure_types if will_fail else [],
            "failure_type_probabilities": failure_type_probabilities,
            "machine_risk_history": machine_risk_history,
        })
    except Exception as error:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(error)}), 400



# Serve the built frontend (frontend/dist) for any remaining route (SPA fallback)
@app.route('/', defaults={"path": ""})
@app.route('/<path:path>')
def serve_frontend(path):
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
    full_path = os.path.join(frontend_dir, path)
    if path != "" and os.path.isfile(full_path):
        return send_from_directory(frontend_dir, path)
    return send_from_directory(frontend_dir, "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
