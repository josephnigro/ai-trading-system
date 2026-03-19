@echo off
cd /d %~dp0
if not exist .venv\Scripts\python.exe (
  echo ERROR: .venv not found. Create it first.
  pause
  exit /b 1
)
call .venv\Scripts\python.exe -m streamlit run phase8_dashboard.py
