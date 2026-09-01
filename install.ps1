# THE FOCUX Agent — one-command installer (Windows)
# Run:  irm https://raw.githubusercontent.com/lucianople7/thefocux-agent/main/install.ps1 | iex
$ErrorActionPreference = "Stop"

$RepoUrl = "https://github.com/lucianople7/thefocux-agent.git"
$InstallDir = Join-Path $env:USERPROFILE "thefocux-agent"

Write-Host "=== THE FOCUX Agent installer ===" -ForegroundColor Yellow

# 1. Git?
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: git not found. Install Git for Windows first." -ForegroundColor Red
    exit 1
}

# 2. Python >= 3.11?
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "ERROR: python not found. Install Python 3.11+ first." -ForegroundColor Red
    exit 1
}
$pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ([version]$pyVer -lt [version]"3.11") {
    Write-Host "ERROR: Python 3.11+ required (found $pyVer)." -ForegroundColor Red
    exit 1
}

# 3. Clone or update
if (-not (Test-Path $InstallDir)) {
    Write-Host "Cloning THE FOCUX into $InstallDir ..."
    git clone --depth 1 $RepoUrl $InstallDir
} else {
    Write-Host "Updating THE FOCUX ..."
    Push-Location $InstallDir
    git pull --ff-only
    Pop-Location
}

# 4. Install (editable, entry points: focux / focux-web)
Push-Location $InstallDir
Write-Host "Installing package (pip install -e .) ..."
python -m pip install -e ".[dev]"
Pop-Location

# 5. Verify
Write-Host ""
Write-Host "=== Installation complete ===" -ForegroundColor Green
Write-Host "Commands:"
Write-Host "  focux skills                  # 57 skills"
Write-Host "  focux agents                  # 11 business roles"
Write-Host "  focux attach ./negocio --workspace mi-negocio   # brain for ANY agent"
Write-Host "  focux absorb --query 'ai agent'                 # real data -> memory"
Write-Host "  focux doctor                  # verify the brain"
Write-Host "  focux install --mcp           # global launchers + user-level MCP"
Write-Host "  focux repl                    # interactive session"
Write-Host "  focux-web --port 47822        # web console: http://127.0.0.1:47822"
Write-Host ""
Write-Host "Configure your provider: copy $InstallDir\.env.example to .env and add your API key."
