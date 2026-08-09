@echo off
REM Download the game's own reference data, for when a new round changes races or units.
cd /d "%~dp0"
call _compose.bat
if not defined COMPOSE goto end

%COMPOSE% run --rm --entrypoint python app refdata_update.py update

echo Restarting ODInfo so it picks up the new data...
%COMPOSE% up -d

:end
pause