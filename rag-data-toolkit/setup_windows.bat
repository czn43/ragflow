@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo RAG Data Toolkit - Windows Setup
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11 or 3.12 and add it to PATH.
    pause
    exit /b 1
)

echo [1/5] Checking Python version...
python --version
if errorlevel 1 goto :fail

if not exist ".venv\Scripts\python.exe" (
    echo [2/5] Creating virtual environment .venv ...
    python -m venv .venv
    if errorlevel 1 goto :fail
) else (
    echo [2/5] Existing .venv found. Skipping creation.
)

echo [3/5] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [4/5] Installing project dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [5/5] Running automated tests...
".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 goto :test_fail

echo.
echo ========================================
echo Setup completed. All tests passed.
echo ========================================
echo.
echo Next step:
echo   run_100.bat config\sites\demo.yaml
echo.
pause
exit /b 0

:test_fail
echo.
echo ========================================
echo [ERROR] Dependencies installed, but tests failed.
echo ========================================
echo Please review the error output above.
pause
exit /b 1

:fail
echo.
echo ========================================
echo [ERROR] Setup failed.
echo ========================================
echo Please review the error output above.
pause
exit /b 1
