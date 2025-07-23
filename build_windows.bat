@echo off
echo YouTube Downloader Pro - Windows Build Script
echo ==============================================

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found! Please install Python from https://python.org
    pause
    exit /b 1
)

echo Python found. Starting build process...
echo.

REM Kill any running instances
taskkill /f /im YouTubeDownloader.exe 2>nul

REM Clean previous builds
echo Cleaning previous builds...
if exist dist rmdir /s /q dist 2>nul
if exist build rmdir /s /q build 2>nul

REM Install dependencies
echo Installing build dependencies...
python -m pip install pyinstaller --quiet --disable-pip-version-check
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

REM Build executable (simple approach)
echo Building executable...
pyinstaller ^
    --onefile ^
    --console ^
    --name YouTubeDownloader ^
    --add-data "yt_dlp_enhanced.py;." ^
    --add-data "youtube_downloader_gui.py;." ^
    --add-data "youtube_downloader_web.py;." ^
    youtube_downloader_safe.py

REM Check if build succeeded
if exist "dist\YouTubeDownloader.exe" (
    echo.
    echo SUCCESS: Build completed!
    echo Executable: dist\YouTubeDownloader.exe
    
    REM Get file size
    for %%F in ("dist\YouTubeDownloader.exe") do (
        set /a size=%%~zF/1048576
        echo Size: !size! MB
    )
    
    echo.
    echo The executable automatically falls back to web interface if GUI is unavailable.
    echo This ensures it works on all systems.
    
) else (
    echo.
    echo ERROR: Build failed! No executable found.
    echo Check the output above for error messages.
)

echo.
pause