@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: virtual environment not found. Run setup_windows.bat first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pytest -q
if errorlevel 1 (
    echo Tests failed.
    pause
    exit /b 1
)

echo All tests passed.
pause
