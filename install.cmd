@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

echo.
echo   ██████╗ ██████╗  █████╗ ██████╗ ██╗  ██╗██╗  ██╗██████╗ ██╗      ██████╗ ██╗████████╗
echo  ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██║  ██║╚██╗██╔╝██╔══██╗██║     ██╔═══██╗██║╚══██╔══╝
echo  ██║  ███╗██████╔╝███████║██████╔╝███████║ ╚███╔╝ ██████╔╝██║     ██║   ██║██║   ██║
echo  ██║   ██║██╔══██╗██╔══██║██╔═══╝ ██╔══██║ ██╔██╗ ██╔═══╝ ██║     ██║   ██║██║   ██║
echo  ╚██████╔╝██║  ██║██║  ██║██║     ██║  ██║██╔╝ ██╗██║     ███████╗╚██████╔╝██║   ██║
echo   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝ ╚═╝   ╚═╝
echo.
echo   GraphXploit Installer
echo.

:: ── Check Python ──────────────────────────────────────────────
set PYTHON=
for %%P in (python python3 py) do (
    %%P --version >nul 2>&1 && (
        for /f "tokens=2 delims= " %%V in ('%%P --version 2^>^&1') do (
            for /f "tokens=1,2 delims=." %%A in ("%%V") do (
                if %%A GEQ 3 if %%B GEQ 11 (
                    set PYTHON=%%P
                    echo   [OK] Found Python %%V
                    goto :found_python
                )
            )
        )
    )
)

echo   [ERROR] Python 3.11+ is required.
echo   Download from https://python.org
pause
exit /b 1

:found_python

:: ── Check pip ─────────────────────────────────────────────────
%PYTHON% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] pip not found. Run: %PYTHON% -m ensurepip --upgrade
    pause
    exit /b 1
)
echo   [OK] pip available

:: ── Check Docker ──────────────────────────────────────────────
docker --version >nul 2>&1
if errorlevel 1 (
    echo   [INFO] Docker not found. Install Docker Desktop for full features.
    echo   https://docs.docker.com/desktop/install/windows-install/
) else (
    echo   [OK] Docker found
)

:: ── Install ───────────────────────────────────────────────────
echo.
echo   Installing GraphXploit...
%PYTHON% -m pip install git+https://github.com/Ujjansh05/GraphXpolit.git >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Installation failed. Check your internet connection.
    pause
    exit /b 1
)
echo   [OK] Installed successfully

:: ── Verify ────────────────────────────────────────────────────
echo.
graphxploit --version >nul 2>&1
if errorlevel 1 (
    echo   [INFO] Installed. Restart your terminal, then run: graphxploit --help
) else (
    echo   [OK] graphxploit is ready!
    echo.
    echo   Get started:
    echo     graphxploit start          # boot infrastructure
    echo     graphxploit model mount    # connect your LLM
    echo     graphxploit analyze .\src  # analyze a codebase
)

echo.
endlocal
