"""Small SQLite helper for storing dashboard prediction history."""

import sqlite3
import os
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash
from pathlib import Path


def _resolve_database_path() -> Path:
    """Detect persistent disk path on Render (/var/data) or local development."""
    if os.getenv("MAINTAI_DATABASE_PATH"):
        return Path(os.environ["MAINTAI_DATABASE_PATH"])
    if os.getenv("RENDER_DISK_PATH"):
        return Path(os.environ["RENDER_DISK_PATH"]) / "maintenance.db"
    # Auto-detect standard Render persistent disk mount
    if os.path.isdir("/var/data"):
        return Path("/var/data/maintenance.db")
    return Path(__file__).resolve().parent / "maintenance.db"


DATABASE_PATH = _resolve_database_path()


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection with readable dictionary-like rows."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def get_current_ist_time() -> str:
    """Return the current Indian Standard Time (IST, UTC+5:30) as YYYY-MM-DD HH:MM:SS."""
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist_tz).strftime("%Y-%m-%d %H:%M:%S")


def initialise_database() -> None:
    """Create the prediction table the first time the backend starts."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                product_type TEXT NOT NULL,
                air_temperature REAL NOT NULL,
                process_temperature REAL NOT NULL,
                rotational_speed REAL NOT NULL,
                torque REAL NOT NULL,
                tool_wear REAL NOT NULL,
                machine_failure INTEGER NOT NULL,
                failure_probability REAL NOT NULL
            )
        """)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(predictions)")}
        if "machine_id" not in columns:
            connection.execute("ALTER TABLE predictions ADD COLUMN machine_id TEXT DEFAULT 'M-001'")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                failure_probability REAL NOT NULL,
                failure_type TEXT,
                is_resolved INTEGER DEFAULT 0
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS work_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                machine_id TEXT NOT NULL,
                title TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                assigned_to TEXT DEFAULT '',
                due_date TEXT DEFAULT '',
                notes TEXT DEFAULT ''
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT,
                channel TEXT NOT NULL,
                recipient TEXT NOT NULL,
                message TEXT NOT NULL,
                alert_severity TEXT NOT NULL
            )
        """)
        notification_columns = {row[1] for row in connection.execute("PRAGMA table_info(notifications)")}
        if "delivery_status" not in notification_columns:
            connection.execute("ALTER TABLE notifications ADD COLUMN delivery_status TEXT DEFAULT 'simulated'")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS notification_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                email_enabled INTEGER DEFAULT 0,
                email_recipient TEXT DEFAULT '',
                smtp_host TEXT DEFAULT 'smtp.gmail.com',
                smtp_port INTEGER DEFAULT 587,
                smtp_username TEXT DEFAULT '',
                smtp_password TEXT DEFAULT ''
            )
        """)
        connection.execute("INSERT OR IGNORE INTO notification_settings (id) VALUES (1)")
        # Migrate existing notification_settings table if needed
        existing_cols = {row[1] for row in connection.execute("PRAGMA table_info(notification_settings)")}
        for col, col_type in [("smtp_host", "TEXT DEFAULT 'smtp.gmail.com'"), ("smtp_port", "INTEGER DEFAULT 587"), ("smtp_username", "TEXT DEFAULT ''"), ("smtp_password", "TEXT DEFAULT ''")]:
            if col not in existing_cols:
                connection.execute(f"ALTER TABLE notification_settings ADD COLUMN {col} {col_type}")

        # Seed/update notification settings from environment variables into DB
        env_user = (os.getenv("SMTP_USERNAME") or os.getenv("EMAIL_USER") or "").strip()
        env_pwd = (os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_APP_PASSWORD") or "").strip()
        env_recipient = (os.getenv("ALERT_EMAIL") or os.getenv("EMAIL_RECIPIENT") or "").strip()
        if env_user or env_pwd or env_recipient:
            row = connection.execute("SELECT smtp_username, smtp_password, email_recipient FROM notification_settings WHERE id = 1").fetchone()
            db_user = (row[0] if row else "") or ""
            db_pwd = (row[1] if row else "") or ""
            db_recipient = (row[2] if row else "") or ""
            new_user = env_user or db_user
            new_pwd = env_pwd or db_pwd
            new_recipient = env_recipient or db_recipient
            connection.execute(
                "UPDATE notification_settings SET smtp_username = ?, smtp_password = ?, email_recipient = ? WHERE id = 1",
                (new_user, new_pwd, new_recipient),
            )
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS custom_assets (
                asset_id TEXT PRIMARY KEY,
                asset_name TEXT NOT NULL,
                product_type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS password_resets (
                email TEXT PRIMARY KEY,
                otp_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS risk_streaks (
                asset_id TEXT PRIMARY KEY,
                consecutive_high_risk INTEGER DEFAULT 0,
                email_sent_for_streak INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_prediction(reading: dict, machine_failure: int, probability: float) -> None:
    """Store one sensor reading and its model prediction with IST timestamp."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO predictions (
                created_at, machine_id, product_type, air_temperature, process_temperature,
                rotational_speed, torque, tool_wear,
                machine_failure, failure_probability
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            get_current_ist_time(),
            reading["Machine ID"], reading["Type"], reading["Air temperature [K]"],
            reading["Process temperature [K]"], reading["Rotational speed [rpm]"],
            reading["Torque [Nm]"], reading["Tool wear [min]"],
            machine_failure, probability,
        ))


def get_recent_predictions(limit: int = 20, machine_id: str | None = None) -> list[dict]:
    """Return the newest dashboard prediction records first."""
    with get_connection() as connection:
        if machine_id:
            rows = connection.execute("""
                SELECT * FROM predictions WHERE machine_id = ? ORDER BY id DESC LIMIT ?
            """, (machine_id, limit)).fetchall()
        else:
            rows = connection.execute("""
                SELECT * FROM predictions ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
    return [dict(row) for row in rows]


def save_alert(severity: str, message: str, probability: float, failure_type: str | None) -> None:
    """Record a maintenance alert with IST timestamp when the model finds material failure risk."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO alerts (created_at, severity, message, failure_probability, failure_type)
            VALUES (?, ?, ?, ?, ?)
        """, (get_current_ist_time(), severity, message, probability, failure_type))


def get_recent_alerts(limit: int = 10) -> list[dict]:
    """Return newest unresolved maintenance alerts first."""
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM alerts WHERE is_resolved = 0 ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(row) for row in rows]


def create_work_order(machine_id: str, title: str, priority: str, assigned_to: str = "", due_date: str = "", notes: str = "") -> int:
    """Create a maintenance task from a detected risk or technician review."""
    with get_connection() as connection:
        result = connection.execute("""
            INSERT INTO work_orders (created_at, machine_id, title, priority, assigned_to, due_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (get_current_ist_time(), machine_id.upper(), title, priority, assigned_to, due_date, notes))
    return int(result.lastrowid)


def get_work_orders(limit: int = 50) -> list[dict]:
    """Return active and completed maintenance tasks, newest first."""
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM work_orders ORDER BY CASE status WHEN 'Open' THEN 0 WHEN 'In progress' THEN 1 ELSE 2 END, id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def update_work_order_status(work_order_id: int, status: str) -> bool:
    """Move a task through the maintenance workflow."""
    with get_connection() as connection:
        result = connection.execute("UPDATE work_orders SET status = ? WHERE id = ?", (status, work_order_id))
    return result.rowcount == 1


def save_notification(channel: str, recipient: str, message: str, severity: str, status: str) -> None:
    """Save an email delivery attempt with IST timestamp for the dashboard history."""
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO notifications (created_at, channel, recipient, message, alert_severity, delivery_status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (get_current_ist_time(), channel, recipient, message, severity, status))


def get_recent_notifications(limit: int = 10) -> list[dict]:
    """Return notifications displayed in the dashboard activity area."""
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT * FROM notifications ORDER BY id DESC LIMIT ?
        """, (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_notification_settings() -> dict:
    """Return the email opt-in and SMTP settings."""
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM notification_settings WHERE id = 1").fetchone()
    return dict(row) if row else {}


def save_notification_settings(email_enabled: bool, email_recipient: str, smtp_host: str = "smtp.gmail.com", smtp_port: int = 587, smtp_username: str = "", smtp_password: str = "") -> None:
    """Save email preference and SMTP configuration permanently."""
    with get_connection() as connection:
        existing = connection.execute("SELECT smtp_username, smtp_password FROM notification_settings WHERE id = 1").fetchone()
        if existing:
            if not smtp_username and existing[0]:
                smtp_username = existing[0]
            if not smtp_password and existing[1]:
                smtp_password = existing[1]

        connection.execute("""
            UPDATE notification_settings
            SET email_enabled = ?, email_recipient = ?, smtp_host = ?, smtp_port = ?, smtp_username = ?, smtp_password = ?
            WHERE id = 1
        """, (int(email_enabled), email_recipient.strip(), smtp_host.strip(), int(smtp_port), smtp_username.strip(), smtp_password.strip()))


def create_user(name: str, email: str, password: str) -> bool:
    """Create a local demo account with a password hash, never plain text."""
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO users (created_at, name, email, password_hash) VALUES (?, ?, ?, ?)",
                (get_current_ist_time(), name, email.lower(), generate_password_hash(password)),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_user_by_email(email: str) -> dict | None:
    """Get a local user record for sign-in verification."""
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email.lower(),)).fetchone()
    return dict(row) if row else None


def save_password_reset(email: str, otp: str) -> None:
    """Store a short-lived hashed OTP for the password-recovery flow."""
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO password_resets (email, otp_hash, expires_at) VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET otp_hash = excluded.otp_hash, expires_at = excluded.expires_at
        """, (email.lower(), generate_password_hash(otp), expires_at))


def get_password_reset(email: str) -> dict | None:
    """Read the pending reset request, if one exists."""
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM password_resets WHERE email = ?", (email.lower(),)).fetchone()
    return dict(row) if row else None


def update_user_password(email: str, password: str) -> None:
    """Replace a user password with its secure hash and invalidate the OTP."""
    with get_connection() as connection:
        connection.execute("UPDATE users SET password_hash = ? WHERE email = ?", (generate_password_hash(password), email.lower()))
        connection.execute("DELETE FROM password_resets WHERE email = ?", (email.lower(),))


def record_risk_streak(asset_id: str, is_high_risk: bool) -> tuple[int, bool, str]:
    """Track consecutive high-risk readings and signal when email should be sent in IST."""
    now_str = get_current_ist_time()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT consecutive_high_risk, email_sent_for_streak, updated_at FROM risk_streaks WHERE asset_id = ?",
            (asset_id,),
        ).fetchone()
        previous_count = row[0] if row else 0
        already_sent = bool(row[1]) if row else False
        count = previous_count + 1 if is_high_risk else 0
        should_send_email = is_high_risk and count >= 3 and not already_sent
        email_sent = int(already_sent or should_send_email) if is_high_risk else 0
        connection.execute("""
            INSERT INTO risk_streaks (asset_id, consecutive_high_risk, email_sent_for_streak, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(asset_id) DO UPDATE SET
                consecutive_high_risk = excluded.consecutive_high_risk,
                email_sent_for_streak = excluded.email_sent_for_streak,
                updated_at = excluded.updated_at
        """, (asset_id, count, email_sent, now_str))
    return count, should_send_email, now_str


def add_custom_asset(asset_id: str, asset_name: str, product_type: str) -> bool:
    """Register a future machine/asset for telemetry and prediction tracking."""
    try:
        with get_connection() as connection:
            connection.execute(
                "INSERT INTO custom_assets (asset_id, asset_name, product_type) VALUES (?, ?, ?)",
                (asset_id.upper(), asset_name, product_type),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_custom_assets(query: str = "") -> list[dict]:
    """Return user-created future-machine records."""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM custom_assets WHERE asset_id LIKE ? ORDER BY asset_id LIMIT 25",
            (f"{query.upper()}%",),
        ).fetchall()
    return [dict(row) for row in rows]


def resolve_alert(alert_id: int) -> bool:
    """Mark one alert as inspected and resolved by a maintenance worker."""
    with get_connection() as connection:
        result = connection.execute(
            "UPDATE alerts SET is_resolved = 1 WHERE id = ? AND is_resolved = 0", (alert_id,)
        )
    return result.rowcount == 1


def get_dashboard_summary() -> dict:
    """Return small dashboard counters calculated from saved application data."""
    with get_connection() as connection:
        total_predictions = connection.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
        high_risk_predictions = connection.execute(
            "SELECT COUNT(*) FROM predictions WHERE machine_failure = 1"
        ).fetchone()[0]
        open_alerts = connection.execute(
            "SELECT COUNT(*) FROM alerts WHERE is_resolved = 0"
        ).fetchone()[0]
    return {
        "total_predictions": total_predictions,
        "high_risk_predictions": high_risk_predictions,
        "open_alerts": open_alerts,
    }
