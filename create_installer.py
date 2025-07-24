#!/usr/bin/env python3
"""
Simple installer creator for YouTube Downloader
Creates a ZIP package that users can easily install
"""

import zipfile
import shutil
from pathlib import Path
import os

def create_installer_zip():
    """Create installer ZIP package"""
    print("Creating YouTube Downloader Installer...")
    print("=" * 40)
    
    # Create temp directory for installer files
    installer_dir = Path("installer_temp")
    if installer_dir.exists():
        shutil.rmtree(installer_dir)
    installer_dir.mkdir()
    
    print("Step 1: Copying core files...")
    
    # Core application files
    core_files = [
        "youtube_downloader_safe.py",
        "youtube_downloader_gui.py", 
        "youtube_downloader_web.py",
        "yt_dlp_enhanced.py",
        "requirements.txt"
    ]
    
    for file in core_files:
        if Path(file).exists():
            shutil.copy2(file, installer_dir / file)
            print(f"  [OK] {file}")
        else:
            print(f"  [MISSING] {file}")
    
    # Documentation files
    docs = ["README_GUI.md", "TROUBLESHOOTING.md", "LICENSE"]
    for doc in docs:
        if Path(doc).exists():
            shutil.copy2(doc, installer_dir / doc)
            print(f"  [OK] {doc}")
    
    print("\nStep 2: Creating launcher script...")
    
    # Create Windows launcher
    launcher_content = '''@echo off
title YouTube Downloader Pro
cd /d "%~dp0"

echo YouTube Downloader Pro
echo =======================
echo.

REM Check Python
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not installed!
    echo.
    echo Please install Python from: https://python.org
    echo Make sure to check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

REM Install requirements on first run
if not exist ".installed" (
    echo Installing requirements...
    python -m pip install -r requirements.txt --quiet
    if %ERRORLEVEL% EQU 0 (
        echo Installation complete!
        echo. > .installed
    ) else (
        echo Installation failed!
        pause
        exit /b 1
    )
    echo.
)

REM Launch application
echo Starting YouTube Downloader...
python youtube_downloader_safe.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with error.
    pause
)
'''
    
    with open(installer_dir / "YouTube-Downloader.bat", "w") as f:
        f.write(launcher_content)
    print("  [OK] YouTube-Downloader.bat")
    
    print("\nStep 3: Creating installation instructions...")
    
    # Create README
    readme_content = '''YouTube Downloader Pro - Installation
===================================

REQUIREMENTS:
- Windows 10 or later
- Python 3.8+ (https://python.org)
- Internet connection

INSTALLATION:
1. Extract this ZIP to a folder
2. Double-click "YouTube-Downloader.bat"
3. First run will install dependencies automatically
4. Application will launch with best available interface

INTERFACES:
- Desktop GUI (if tkinter available)
- Web Browser (if GUI unavailable)
- Command Line (fallback)

The application automatically detects and uses the best available interface.

FEATURES:
- Download YouTube videos in various qualities
- Batch download support
- Resume interrupted downloads
- Real-time progress tracking
- 5-10x faster than basic downloaders

TROUBLESHOOTING:
- If Python not found: Install from python.org with "Add to PATH"
- If GUI doesn't work: Web interface will launch automatically
- For detailed help: See TROUBLESHOOTING.md

SUPPORT:
Check TROUBLESHOOTING.md for common issues and solutions.
'''
    
    with open(installer_dir / "README.txt", "w") as f:
        f.write(readme_content)
    print("  [OK] README.txt")
    
    print("\nStep 4: Creating ZIP package...")
    
    # Create ZIP file
    zip_path = Path("YouTubeDownloader-Installer.zip")
    if zip_path.exists():
        zip_path.unlink()
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in installer_dir.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(installer_dir)
                zipf.write(file_path, arcname)
    
    # Get ZIP size
    size_kb = zip_path.stat().st_size / 1024
    print(f"  [OK] {zip_path} ({size_kb:.1f} KB)")
    
    # Cleanup
    shutil.rmtree(installer_dir)
    
    print(f"\nSUCCESS: Installer created!")
    print("=" * 40)
    print(f"File: {zip_path}")
    print(f"Size: {size_kb:.1f} KB")
    print()
    print("DISTRIBUTION:")
    print("1. Share the ZIP file with users")
    print("2. Users extract and run 'YouTube-Downloader.bat'")
    print("3. First run installs dependencies automatically")
    print("4. Application launches with automatic interface detection")
    print()
    print("This installer avoids PyInstaller tkinter issues by:")
    print("- Using source code instead of bundled executable")
    print("- Automatically installing dependencies") 
    print("- Providing graceful fallback to web interface")
    print("- Including comprehensive troubleshooting")

if __name__ == "__main__":
    try:
        create_installer_zip()
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()