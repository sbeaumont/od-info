@echo off
where uv >nul 2>nul
if %errorlevel% equ 0 (
    echo uv is already installed.
) else (
    echo Installing uv...
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
)

echo.
echo Installing dependencies...
uv sync

echo.
uv run python setup.py

echo.
echo Run odinfo.bat to start the application.
pause