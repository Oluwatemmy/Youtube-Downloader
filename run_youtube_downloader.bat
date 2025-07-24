@echo off
title YouTube Downloader Pro - Enhanced Edition

echo.
echo ================================================================
echo                YouTube Downloader Pro - Enhanced Edition
echo ================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.7+ from: https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Display Python version
echo [INFO] Python version:
python --version
echo.

REM Check if the launcher script exists
if not exist "launcher.py" (
    echo [ERROR] launcher.py not found in current directory
    echo Please ensure all files are in the same folder
    echo.
    pause
    exit /b 1
)

REM Run the launcher script
echo [INFO] Starting YouTube Downloader Pro...
echo.
python launcher.py

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error
    pause
)

echo.
echo [INFO] Application closed normally
pause