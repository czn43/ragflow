@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo RAG Data Toolkit v1.8 - Windows Setup
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.11 or 3.12 and add it to PATH.
    pause
    exit /b 1
)

echo [1/6] Checking Python version...
python --version
if errorlevel 1 goto :fail

if not exist ".venv\Scripts\python.exe" (
    echo [2/6] Creating virtual environment .venv ...
    python -m venv .venv
    if errorlevel 1 goto :fail
) else (
    echo [2/6] Existing .venv found. Skipping creation.
)

echo [3/6] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [4/6] Installing project dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [5/6] Checking browser...
".venv\Scripts\python.exe" browser_check.py
if not errorlevel 1 goto :browser_ok

echo.
echo Google Chrome was not found in common Windows locations.
choice /C YN /N /M "Install Playwright Chromium now? [Y/N]: "
if errorlevel 2 goto :browser_skipped

echo Installing Playwright Chromium...
".venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 goto :browser_fail
goto :browser_ok

:browser_skipped
echo Chromium installation skipped.
echo JS pagination will require Chrome or Playwright Chromium before use.

:browser_ok
echo [6/6] Running automated tests...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto :test_fail

echo.
echo ========================================
echo Setup completed. All tests passed.
echo ========================================
echo.
echo Browser policy:
echo   1. Prefer installed system Chrome
echo   2. Fall back to Playwright Chromium only when needed
echo.
echo Quick starts:
echo   run_sztv_100.bat
echo   run_multi.bat config\tasks\sztv_training.yaml
echo.
pause
exit /b 0

:browser_fail
echo.
echo [ERROR] Chromium installation failed.
echo You can retry later with:
echo   .venv\Scripts\python.exe -m playwright install chromium
pause
exit /b 1

:test_fail
echo.
echo [ERROR] Dependencies installed, but tests failed.
pause
exit /b 1

:fail
echo.
echo [ERROR] Setup failed.
pause
exit /b 1
