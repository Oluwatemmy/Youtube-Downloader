@echo off
REM ============================================================
REM  YouT Manager - one-click installer
REM ============================================================
REM  Runs the PowerShell install script with the execution policy
REM  bypass Windows requires for downloaded scripts.
REM  No admin rights needed - installs per-user.

cd /d "%~dp0"

if not exist "install.ps1" (
    if exist "scripts\install.ps1" (
        set "SCRIPT=scripts\install.ps1"
    ) else (
        echo.
        echo   install.ps1 not found next to this file.
        echo   Extract the whole zip and try again.
        echo.
        pause
        exit /b 1
    )
) else (
    set "SCRIPT=install.ps1"
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%"
