@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "TASK=%~1"
if "%TASK%"=="" set "TASK=config\tasks\sztv_training.yaml"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: virtual environment not found. Run setup_windows.bat first.
    pause
    exit /b 1
)

if not exist "%TASK%" (
    echo ERROR: task config not found: %TASK%
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py merge --task "%TASK%"
if errorlevel 1 (
    echo Merge failed.
    pause
    exit /b 1
)

echo Merge completed.
pause
