# GraphXploit Installer for Windows
# Usage: irm https://raw.githubusercontent.com/Ujjansh05/GraphXpolit/main/install.ps1 | iex
$ErrorActionPreference = "Stop"

function Write-Info    { param($msg) Write-Host "  > " -ForegroundColor Cyan -NoNewline; Write-Host $msg }
function Write-Success { param($msg) Write-Host "  ✔ " -ForegroundColor Green -NoNewline; Write-Host $msg }
function Write-Fail    { param($msg) Write-Host "  ✘ " -ForegroundColor Red -NoNewline; Write-Host $msg; exit 1 }

Write-Host ""
Write-Host @"
   ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗██╗  ██╗██████╗ ██╗      ██████╗ ██╗████████╗
  ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║╚██╗██╔╝██╔══██╗██║     ██╔═══██╗██║╚══██╔══╝
  ██║  ███╗██████╔╝███████║██████╔╝███████║ ╚███╔╝ ██████╔╝██║     ██║   ██║██║   ██║
  ██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║ ██╔██╗ ██╔═══╝ ██║     ██║   ██║██║   ██║
  ╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║██╔╝ ██╗██║     ███████╗╚██████╔╝██║   ██║
   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝ ╚═╝   ╚═╝
"@ -ForegroundColor Red

Write-Host ""
Write-Host "  GraphXploit Installer" -ForegroundColor White
Write-Host ""

# ── Check Python ────────────────────────────────────────────────
$python = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "(\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -ge 3 -and $minor -ge 11) {
                $python = $cmd
                break
            }
        }
    } catch {}
}

if (-not $python) {
    Write-Fail "Python 3.11+ is required. Install from https://python.org"
}
Write-Success "Found $(& $python --version)"

# ── Check pip ───────────────────────────────────────────────────
try {
    & $python -m pip --version | Out-Null
    Write-Success "pip available"
} catch {
    Write-Fail "pip not found. Run: $python -m ensurepip --upgrade"
}

# ── Check Docker ────────────────────────────────────────────────
try {
    $dockerVer = docker --version 2>&1
    Write-Success "Docker found ($($dockerVer.Substring(0, [Math]::Min(30, $dockerVer.Length))))"
} catch {
    Write-Info "Docker not found. Install Docker Desktop to use 'graphxploit start'."
    Write-Info "https://docs.docker.com/desktop/install/windows-install/"
}

# ── Install ─────────────────────────────────────────────────────
Write-Host ""
Write-Info "Installing GraphXploit..."

try {
    & $python -m pip install git+https://github.com/Ujjansh05/GraphXpolit.git 2>&1 | Out-Null
    Write-Success "Installed via pip"
} catch {
    Write-Fail "Installation failed: $_"
}

# ── Verify ──────────────────────────────────────────────────────
Write-Host ""

# Refresh PATH for current session
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

try {
    & graphxploit --version 2>&1 | Out-Null
    Write-Success "graphxploit is ready!"
    Write-Host ""
    Write-Host "  Get started:" -ForegroundColor White
    Write-Host "    graphxploit start          " -NoNewline; Write-Host "# boot infrastructure" -ForegroundColor DarkGray
    Write-Host "    graphxploit model mount    " -NoNewline; Write-Host "# connect your LLM" -ForegroundColor DarkGray
    Write-Host "    graphxploit analyze .\src  " -NoNewline; Write-Host "# analyze a codebase" -ForegroundColor DarkGray
    Write-Host ""
} catch {
    Write-Info "Installed, but 'graphxploit' is not on your PATH."
    Write-Info "Close and reopen your terminal, then try: graphxploit --version"
}
