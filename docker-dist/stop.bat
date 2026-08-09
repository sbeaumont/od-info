@echo off
REM Stop ODInfo. Your instance folder is left alone.
cd /d "%~dp0"
call _compose.bat
if not defined COMPOSE goto end

%COMPOSE% down

echo ODInfo stopped. Your configuration and database in instance are untouched.

:end
pause