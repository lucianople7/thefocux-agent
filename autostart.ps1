# THE FOCUX Agent — 24/7 autostart (Windows)
# Installs scheduled tasks so the web console + OmniRoute gateway start at login.
# Run:  powershell -ExecutionPolicy Bypass -File autostart.ps1
$ErrorActionPreference = "Stop"

$Repo = "C:\Users\lucia\OneDrive\Documentos\thefocux-agent"
$NodeDir = "$env:LOCALAPPDATA\Programs\nodejs24"

# --- THE FOCUX web console (port 47822) ---
$webTask = "THEFOCUX-Web"
$webCmd = "python"
$webArgs = "`"$Repo\webui.py`" --port 47822"

# --- OmniRoute gateway (port 20128) ---
$omniTask = "THEFOCUX-OmniRoute"
$omniCmd = "$NodeDir\node.exe"
$omniArgs = "`"$env:APPDATA\npm\node_modules\omniroute\bin\omniroute.mjs`""

function Install-Task($name, $cmd, $args) {
    Write-Host "Installing scheduled task: $name"
    schtasks /Create /F /TN $name /TR "`"$cmd`" $args" /SC ONLOGON /RL LIMITED /IT | Out-Null
    Write-Host "  installed (runs at logon)."
}

Install-Task $webTask $webCmd $webArgs
Install-Task $omniTask $omniCmd $omniArgs

Write-Host ""
Write-Host "=== Autostart configured ==="
Write-Host "  $webTask  -> http://127.0.0.1:47822  (THE FOCUX console)"
Write-Host "  $omniTask -> http://localhost:20128 (OmniRoute gateway)"
Write-Host "Stop a task:  schtasks /End /TN $webTask"
Write-Host "Remove:       schtasks /Delete /TN $webTask /F"
