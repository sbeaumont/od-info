@echo off
REM Start ODInfo, and keep it running until you stop it.
cd /d "%~dp0"
call _compose.bat
if not defined COMPOSE goto end

REM A container has no idea what timezone you are in, so tell it once. The rest of the
REM settings go in the same file, commented out, so they are there when you want them.
if exist .env goto haveenv
echo A container does not know your timezone, so please enter it.
echo Use the Area/City form, for example: Europe/Amsterdam
set /p TIMEZONE="Timezone: "
>.env echo TZ=%TIMEZONE%
>>.env echo.
>>.env echo # Where your configuration and database live. Uncomment and give a full path
>>.env echo # to keep them somewhere else, for instance where your backups already look.
>>.env echo #ODINFO_INSTANCE=D:\odinfo\instance
>>.env echo.
>>.env echo # How to reach ODInfo. It listens on every interface, so other machines on your
>>.env echo # network can reach it too; set the address to 127.0.0.1 for this machine only.
>>.env echo #ODINFO_BIND=0.0.0.0
>>.env echo #ODINFO_PORT=5042
>>.env echo.
>>.env echo # Docker or Podman, for when you have both and want a particular one.
>>.env echo #ODINFO_ENGINE=docker
:haveenv

set INSTANCE=instance
if exist .env for /f "tokens=1,* delims==" %%i in ('findstr /b "ODINFO_INSTANCE=" .env') do set INSTANCE=%%j

set ODPORT=5042
if exist .env for /f "tokens=1,* delims==" %%i in ('findstr /b "ODINFO_PORT=" .env') do set ODPORT=%%j

set ODBIND=0.0.0.0
if exist .env for /f "tokens=1,* delims==" %%i in ('findstr /b "ODINFO_BIND=" .env') do set ODBIND=%%j

%COMPOSE% pull

REM Make the folder ourselves so it belongs to you, not to the container runtime.
if not exist "%INSTANCE%" mkdir "%INSTANCE%"

if not exist "%INSTANCE%\secret.txt" echo Creating configuration files in %INSTANCE% ...
REM Exits non-zero on purpose: the files it writes still need your details, which the
REM message further down puts better than the container runtime would. So its output is
REM held back until it turns out something genuinely went wrong.
if not exist "%INSTANCE%\secret.txt" %COMPOSE% run --rm --entrypoint python app -c "import odinfo.config" >bootstrap.log 2>&1

if not exist "%INSTANCE%\secret.txt" goto nostart
if exist bootstrap.log del bootstrap.log

findstr /C:"EDIT_THIS" "%INSTANCE%\secret.txt" >nul 2>&1
if %errorlevel%==0 goto needsedit

%COMPOSE% up -d
if not %errorlevel%==0 goto portbusy
echo.
echo ODInfo is running: http://localhost:%ODPORT%
if "%ODBIND%"=="127.0.0.1" echo Only from this machine, since ODINFO_BIND says so.
if not "%ODBIND%"=="127.0.0.1" echo From another machine, use this machine's own name or address instead of localhost.
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
echo   %INSTANCE%\secret.txt   your OpenDominion login and the round number
echo   %INSTANCE%\users.json   the login for the web interface

:end
pause