@echo off
setlocal
cd /d "%~dp0"
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Virtual environment not found. Run setup_windows.bat first.
  pause
  exit /b 1
)

"%PY%" main.py inspect --site config\sites\sznews.yaml --url https://www.sznews.com/node_31100.htm
pause
