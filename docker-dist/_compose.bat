@echo off
REM Called by the other scripts: work out whether to drive Docker or Podman. Nothing is
REM configured here beyond the choice between the two, so whichever one you pick uses
REM your own settings. Put ODINFO_ENGINE=podman or ODINFO_ENGINE=docker in .env to force.
set COMPOSE=
if exist .env for /f "tokens=2 delims==" %%e in ('findstr /b "ODINFO_ENGINE=" .env') do set COMPOSE=%%e compose

REM Whichever one is actually running. Having both installed is common, having both
REM running is not.
if not defined COMPOSE docker info >nul 2>&1 && set COMPOSE=docker compose
if not defined COMPOSE podman info >nul 2>&1 && set COMPOSE=podman compose

REM Nothing responded, so fall back to whichever is installed and let it explain itself.
if not defined COMPOSE where docker >nul 2>&1 && set COMPOSE=docker compose
if not defined COMPOSE where podman >nul 2>&1 && set COMPOSE=podman compose

if not defined COMPOSE echo Neither Docker nor Podman is installed. Install one of them and try again.