@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run setup_windows.bat first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pytest -v
set CODE=%ERRORLEVEL%

echo.
if "%CODE%"=="0" (
    echo [OK] All tests passed.
) else (
    echo [ERROR] Tests failed. Exit code: %CODE%
)
pause
exit /b %CODE%
