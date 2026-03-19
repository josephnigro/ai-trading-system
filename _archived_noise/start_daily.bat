@echo off
title AI Trading Scanner — Daily Runner
cd /d "%~dp0"

echo.
echo  ============================================================
echo   AI Trading Scanner — Daily Runner
echo  ============================================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in virtual environment
    pause
    exit /b 1
)

echo  Config:
echo    Scan time  : 4:30 PM local time
echo    Poll inbox : every 15 minutes
echo    Scan limit : 40 symbols
echo    Email      : enabled
echo.
echo  Drop a file in logs\notifications\inbox\ to approve trades.
echo  Press Ctrl+C at any time to stop.
echo.

REM Pass any extra CLI args through (e.g. --execute-approved, --run-now)
python daily_runner.py --schedule 16:30 --poll-interval 15 --scan-limit 40 %*

echo.
echo  Daily Runner stopped.
pause
