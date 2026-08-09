@echo off
REM Fetch game data right now, instead of waiting for the hourly update.
cd /d "%~dp0"
call _compose.bat
if not defined COMPOSE goto end

%COMPOSE% run --rm --entrypoint python app cron.py

:end
pause