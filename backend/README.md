# Backend API

Start from the project root with the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
python backend/app.py
```

Check `http://127.0.0.1:5000/health`.

## Model performance

Open the dashboard's **Model performance** page, or open `artifacts/random_forest_metrics.json`.

The backend also provides `GET /model-metrics`.

## Real email alerts

The dashboard stores only the recipient email and opt-in choice. It never stores a mail password.

Before starting Flask, set these variables in the same PowerShell window. Example for Gmail:

```powershell
$env:SMTP_HOST = "smtp.gmail.com"
$env:SMTP_PORT = "587"
$env:SMTP_USERNAME = "youraddress@gmail.com"
$env:SMTP_PASSWORD = "your-provider-app-password"
python backend/app.py
```

Use an app password from your mail provider rather than your normal mail password. After starting the backend, open **Email settings**, enable email notifications, enter the recipient address, save it, and click **Send test email**.

An easier secure option is:

```powershell
.\start_backend_with_email.ps1
```

The script prompts for the sender email and app password at runtime. It does not save the password in the project or database.

### Resend API alternative

If SMTP is blocked by your provider, use the Resend email API instead:

```powershell
.\start_backend_with_resend.ps1
```

It asks for a Resend API key and a verified sender email at runtime. Set up the API key and verified sender in your Resend account first. The application automatically uses Resend when those variables are present.

## Main endpoints

- `POST /predict` — failure prediction from telemetry
- `GET /assets?q=M148` — search AI4I Product IDs and future assets
- `POST /assets` — add a future machine
- `POST /signup`, `POST /login` — local demo account flow
- `GET /model-metrics` — Random Forest evaluation metrics
- `POST /notification-settings`, `POST /email-test` — email opt-in and delivery test
