@echo off
:: Stop the od-info scheduled task

set TASK_NAME=ODInfo_Update

schtasks /query /tn "%TASK_NAME%" >nul 2>nul
if %errorlevel% neq 0 (
    echo Task is not scheduled.
    exit /b 0
)

schtasks /delete /tn "%TASK_NAME%" /f
echo Task stopped.
pause