@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo Guangdong Education and Talent - P0 Run
echo ========================================

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: virtual environment not found.
    echo Run setup_windows.bat first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py multi --task "config\tasks\guangdong_education_talent_p0.yaml" --clean-run
if errorlevel 1 (
    echo.
    echo ERROR: task failed. Check logs\app.log
    pause
    exit /b 1
)

echo.
echo Completed.
echo Final: data\final\guangdong_education_talent_p0\combined_final.jsonl
echo Per source: data\runs\guangdong_education_talent_p0\
echo Benchmark: benchmarks\Guangdong_Education_Talent_100Q.xlsx
pause
