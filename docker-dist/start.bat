@echo off
REM Start ODInfo, and keep it running until you stop it.
cd /d "%~dp0"
call _compose.bat
if not defined COMPOSE goto end

REM A container has no idea what timezone you are in, so tell it once.
if exist .env goto haveenv
echo A container does not know your timezone, so please enter it.
echo Use the Area/City form, for example: Europe/Amsterdam
set /p TIMEZONE="Timezone: "
>.env echo TZ=%TIMEZONE%
:haveenv

set ODPORT=5042
if exist .env for /f "tokens=2 delims==" %%p in ('findstr /b "ODINFO_PORT=" .env') do set ODPORT=%%p

%COMPOSE% pull

REM Make the folder ourselves so it belongs to you, not to the container runtime.
if not exist instance mkdir instance

if not exist instance\secret.txt echo Creating configuration files...
REM Exits non-zero on purpose: the files it writes still need your details, which the
REM message further down puts better than the container runtime would. So its output is
REM held back until it turns out something genuinely went wrong.
if not exist instance\secret.txt %COMPOSE% run --rm --entrypoint python app -c "import odinfo.config" >bootstrap.log 2>&1

if not exist instance\secret.txt goto nostart
if exist bootstrap.log del bootstrap.log

findstr /C:"EDIT_THIS" instance\secret.txt >nul 2>&1
if %errorlevel%==0 goto needsedit

%COMPOSE% up -d
if not %errorlevel%==0 goto portbusy
echo.
echo ODInfo is running: http://localhost:%ODPORT%
echo The data updates itself at 45 minutes past every hour.
goto end

:portbusy
echo.
echo ODInfo could not start. If the message above says the address is already in
echo use, something else on this machine is sitting on port %ODPORT%: put a line
echo like ODINFO_PORT=5043 in the .env file and start again.
goto end

:nostart
echo.
echo Could not start ODInfo, most likely because it could not be downloaded.
echo Check your internet connection. What went wrong:
echo.
if exist bootstrap.log type bootstrap.log
goto end

:needsedit
echo.
echo Almost there. Edit these two files, then run start again:
echo   instance\secret.txt   your OpenDominion login and the round number
echo   instance\users.json   the login for the web interface

:end
pause