@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo RAG Data Toolkit v1.4 - 100 Document Run
echo ========================================

set "CFG=%~1"
if "%CFG%"=="" set "CFG=config\sites\demo.yaml"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: virtual environment not found.
    echo Run setup_windows.bat first.
    pause
    exit /b 1
)

if not exist "%CFG%" (
    echo ERROR: config file not found: %CFG%
    pause
    exit /b 1
)

echo Config: %CFG%
echo Clean run: YES
echo.

".venv\Scripts\python.exe" main.py all --site "%CFG%" --max-pages 20 --max-docs 100 --clean-run
if errorlevel 1 (
    echo.
    echo ERROR: run failed. Check logs\app.log
    pause
    exit /b 1
)

echo.
echo ========================================
echo Run completed.
echo Outputs:
echo   data\06_final\final.jsonl
echo   reports\quality_report.json
echo   reports\discovery_diagnostics.json
echo ========================================
pause
