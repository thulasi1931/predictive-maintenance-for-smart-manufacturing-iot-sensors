# Starts MaintAI with SMTP credentials only for this running session.
# The password is requested securely and is never written into any project file.

$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:SMTP_HOST = Read-Host "SMTP host (Gmail: smtp.gmail.com)"
$env:SMTP_PORT = Read-Host "SMTP port (Gmail: 587)"
$env:SMTP_USERNAME = Read-Host "Email address used to send alerts"
$securePassword = Read-Host "SMTP app password" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $env:SMTP_PASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    & (Join-Path $projectPath '.venv\Scripts\python.exe') (Join-Path $projectPath 'backend\app.py')
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    Remove-Item Env:SMTP_PASSWORD -ErrorAction SilentlyContinue
}
