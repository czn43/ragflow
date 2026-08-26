@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if "%~1"=="" (
    echo Usage:
    echo   run_100.bat config\sites\your_site.yaml
    echo.
    echo Example:
    echo   run_100.bat config\sites\demo.yaml
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv not found. Run setup_windows.bat first.
    pause
    exit /b 1
)

if not exist "%~1" (
    echo [ERROR] Site config does not exist: %~1
    pause
    exit /b 1
)

echo ========================================
echo RAG Data Toolkit - 100 Document Run
echo Config: %~1
echo ========================================
echo.

".venv\Scripts\python.exe" main.py all --site "%~1" --max-pages 20 --max-docs 100
if errorlevel 1 (
    echo.
    echo [ERROR] Run failed. Check logs\app.log
    pause
    exit /b 1
)

echo.
echo ========================================
echo Run completed.
echo Outputs:
echo   data\06_final\final.jsonl
echo   reports\quality_report.json
echo ========================================
pause
exit /b 0
