@echo off
REM Watch what ODInfo is doing. Press Ctrl-C to stop watching; ODInfo keeps running.
cd /d "%~dp0"
call _compose.bat
if not defined COMPOSE goto end

%COMPOSE% logs -f

:end