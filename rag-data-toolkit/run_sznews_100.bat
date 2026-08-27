@echo off
setlocal
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Virtual environment not found. Run setup_windows.bat first.
  pause
  exit /b 1
)

echo ========================================
echo SZNEWS - 100 Document Training Run
echo ========================================
"%PY%" main.py all --site config\sites\sznews.yaml --max-pages 10 --max-docs 100 --clean-run
if errorlevel 1 (
  echo.
  echo SZNEWS run failed. Check logs\app.log and reports\discovery_diagnostics.json
  pause
  exit /b 1
)

echo.
echo Finished.
echo Final: data\06_final\final.jsonl
echo Report: reports\quality_report.json
pause
