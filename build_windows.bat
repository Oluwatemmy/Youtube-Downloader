@echo off
echo YouTube Downloader Pro - Windows Build Script
echo ==============================================

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%

REM Check if Python 3.13
echo %PYTHON_VERSION% | findstr "3.13" >nul
if %ERRORLEVEL% EQU 0 (
    echo.
    echo WARNING: Python 3.13 detected!
    echo Python 3.13 has compatibility issues with some packages.
    echo.
    echo RECOMMENDED SOLUTIONS:
    echo 1. Use Python 3.12 instead
    echo 2. Use the source distribution method below
    echo.
    echo Attempting build anyway...
    echo.
)

REM Create source distribution instead of exe
echo Creating source distribution...
python create_source_installer.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Source installer created!
    echo File: YouTubeDownloader-Installer.zip
    echo.
    echo This works on ALL Python versions and is more reliable.
    echo Users just run the .bat file included in the zip.
    echo.
    pause
    exit /b 0
)

REM Fallback to PyInstaller if source method fails
echo.
echo Attempting PyInstaller build...

REM Try installing with no-deps to avoid ctypes issues
python -m pip install --no-deps pyinstaller
python -m pip install altgraph

REM Simple build without complex dependencies
pyinstaller ^
    --onefile ^
    --console ^
    --name YouTubeDownloader ^
    --hidden-import=yt_dlp ^
    --collect-all=yt_dlp ^
    youtube_downloader_safe.py

if exist "dist\YouTubeDownloader.exe" (
    echo.
    echo SUCCESS: Executable created!
    echo File: dist\YouTubeDownloader.exe
) else (
    echo.
    echo BUILD FAILED: Creating fallback batch launcher...
    echo.
    echo @echo off > YouTubeDownloader.bat
    echo python youtube_downloader_safe.py %%* >> YouTubeDownloader.bat
    echo.
    echo Created: YouTubeDownloader.bat
    echo This batch file will work as a launcher.
)

pause