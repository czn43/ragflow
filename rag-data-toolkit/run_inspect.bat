@echo off
setlocal
cd /d "%~dp0"

set "CFG=%~1"
if "%CFG%"=="" set "CFG=config\sites\demo.yaml"
set "URL=%~2"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: virtual environment not found. Run setup_windows.bat first.
    pause
    exit /b 1
)

if not exist "%CFG%" (
    echo ERROR: config file not found: %CFG%
    pause
    exit /b 1
)

if "%URL%"=="" (
    ".venv\Scripts\python.exe" main.py inspect --site "%CFG%" --validate-top 5
) else (
    ".venv\Scripts\python.exe" main.py inspect --site "%CFG%" --url "%URL%" --validate-top 5
)

if errorlevel 1 (
    echo ERROR: inspect failed. Check logs\app.log
    pause
    exit /b 1
)

pause
