@echo off
:: Start the od-info scheduled task via Windows Task Scheduler
:: Runs cron.py at minute 45 of every hour

set TASK_NAME=ODInfo_Update
set SCRIPT_DIR=%~dp0

:: Check if already scheduled
schtasks /query /tn "%TASK_NAME%" >nul 2>nul
if %errorlevel% equ 0 (
    echo Task is already scheduled. Use stop_cron.bat to stop it first.
    exit /b 1
)

:: Create the scheduled task: run every hour at minute 45
schtasks /create /tn "%TASK_NAME%" /tr "uv run python \"%SCRIPT_DIR%cron.py\"" /sc hourly /st 00:45 /f
if %errorlevel% neq 0 (
    echo Failed to create scheduled task.
    pause
    exit /b 1
)

echo Task scheduled. cron.py will run at minute 45 of every hour.
echo To stop it, run stop_cron.bat.
pause