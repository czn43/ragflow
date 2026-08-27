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
echo SZTV + SZNEWS Multi-source Training Run
echo ========================================
"%PY%" main.py multi --task config\tasks\shenzhen_news_training.yaml --clean-run
if errorlevel 1 (
  echo.
  echo Multi-source run failed. Check logs\app.log and reports\tasks\shenzhen_news_training\execution.json
  pause
  exit /b 1
)

echo.
echo Finished.
echo Combined final: data\final\shenzhen_news_training\combined_final.jsonl
echo Task report: reports\tasks\shenzhen_news_training\summary.json
pause
