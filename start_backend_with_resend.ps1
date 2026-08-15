# Starts MaintAI with the Resend email API instead of SMTP.
# Create a Resend API key and verify a sender domain/account first.

$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:RESEND_API_KEY = Read-Host "Resend API key"
$env:EMAIL_FROM = Read-Host "Verified sender address (for example alerts@yourdomain.com)"
try {
    & (Join-Path $projectPath '.venv\Scripts\python.exe') (Join-Path $projectPath 'backend\app.py')
}
finally {
    Remove-Item Env:RESEND_API_KEY -ErrorAction SilentlyContinue
}
