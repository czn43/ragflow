@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo RAG Data Toolkit v1.8 - SZTV 100 Run
echo ========================================

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: virtual environment not found.
    echo Run setup_windows.bat first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py all --site "config\sites\sztv.yaml" --max-pages 20 --max-docs 100 --clean-run
if errorlevel 1 (
    echo.
    echo ERROR: run failed. Check logs\app.log
    pause
    exit /b 1
)

echo.
echo Outputs:
echo   data\00_urls\urls.jsonl
echo   data\01_raw\raw.jsonl
echo   data\04_clean\cleaned.jsonl
echo   data\06_final\final.jsonl
echo   data\06_final\json\*.json
echo   reports\quality_report.json
echo   reports\discovery_diagnostics.json
pause
