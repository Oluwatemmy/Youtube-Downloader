@echo off
title YouTube Downloader Pro - Enhanced Edition
cd /d "%~dp0"

echo.
echo ================================================================
echo                YouTube Downloader Pro - Enhanced Edition
echo ================================================================
echo.

REM Prefer the local venv if it exists; otherwise fall back to system Python
set PYTHON_EXE=
if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
    echo [INFO] Using local virtual environment
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python is not installed or not in PATH
        echo.
        echo Please install Python 3.8+ from https://python.org
        echo Make sure to check "Add Python to PATH" during installation.
        echo.
        pause
        exit /b 1
    )
    set PYTHON_EXE=python
    echo [INFO] Using system Python
)

"%PYTHON_EXE%" --version
echo.

if not exist "launcher.py" (
    echo [ERROR] launcher.py not found in current directory
    pause
    exit /b 1
)

echo [INFO] Starting YouTube Downloader Pro...
echo.
"%PYTHON_EXE%" launcher.py

if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error
    pause
)
