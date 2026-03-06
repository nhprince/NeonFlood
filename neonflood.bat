@echo off
REM ═══════════════════════════════════════════════════════════════════
REM  NeonFlood v2.0.0 — Windows Quick-Start Script
REM  Developer : NH Prince | https://nhprince.dpdns.org
REM  Usage     : Double-click, or run from CMD: neonflood.bat [flags]
REM  Examples  : neonflood.bat
REM              neonflood.bat -u http://target.com -m get
REM ═══════════════════════════════════════════════════════════════════

echo.
echo   NeonFlood v2.0.0  //  NH Prince  //  nhprince.dpdns.org
echo   FOR AUTHORIZED AND EDUCATIONAL USE ONLY
echo.

REM ── Check Python is installed ────────────────────────────────────────────
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python not found.
    echo         Download from https://python.org and ensure it is on PATH.
    pause
    exit /b 1
)

REM ── Verify Python 3.10+ ─────────────────────────────────────────────────
python -c "import sys; exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERROR] Python 3.10 or newer is required.
    python --version
    pause
    exit /b 1
)

REM ── Upgrade pip silently ─────────────────────────────────────────────────
python -m pip install --upgrade pip --quiet >nul 2>&1

REM ── Install optional PySocks for proxy/Tor support ──────────────────────
echo [*] Checking optional dependencies...
python -m pip install PySocks --quiet >nul 2>&1
IF ERRORLEVEL 1 (
    echo [!] PySocks not installed -- proxy/Tor features will be disabled.
) ELSE (
    echo [OK] PySocks ready.
)

echo.
echo [*] Launching NeonFlood...
echo.

REM ── Launch (pass all arguments through) ─────────────────────────────────
python -m neonflood %*

IF ERRORLEVEL 1 (
    echo.
    echo [!] NeonFlood exited with an error.
    pause
)
