@echo off
REM Start Automated Trading Session
REM Change settings in automated_session.py before running

cls
echo.
echo ================================================================================
echo  AUTOMATED TRADING SESSION LAUNCHER
echo ================================================================================
echo.
echo This will start your trading scanner for a few hours unattended.
echo.
echo BEFORE RUNNING:
echo  1. Open automated_session.py in your editor
echo  2. Set DURATION_HOURS, SCAN_INTERVAL_MINUTES, and AUTO_TRADE
echo  3. Run this script
echo.
echo ================================================================================
echo.
pause

cd /d "%~dp0"
python automated_session.py
pause
