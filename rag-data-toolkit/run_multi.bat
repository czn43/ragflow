@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo RAG Data Toolkit v1.8 - Multi Source Run
echo ========================================

set "TASK=%~1"
if "%TASK%"=="" set "TASK=config\tasks\sztv_training.yaml"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: virtual environment not found.
    echo Run setup_windows.bat first.
    pause
    exit /b 1
)

if not exist "%TASK%" (
    echo ERROR: task config not found: %TASK%
    pause
    exit /b 1
)

echo Task: %TASK%
echo Clean run: YES
echo.

".venv\Scripts\python.exe" main.py multi --task "%TASK%" --clean-run
if errorlevel 1 (
    echo.
    echo ERROR: multi-source run failed. Check logs\app.log
    pause
    exit /b 1
)

echo.
echo Multi-source run completed.
echo Check:
echo   data\runs\TASK_ID\SITE_ID\
echo   data\final\TASK_ID\combined_final.jsonl
echo   reports\tasks\TASK_ID\multi_summary.json
echo.
pause
