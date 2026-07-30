#!/usr/bin/env python3
"""
YouTube Downloader Pro - Launcher Script

This script checks dependencies and launches the main application.
It also handles the pkg_resources deprecation warning.
"""

import os
import sys
import subprocess
import importlib.util
import warnings
from pathlib import Path

# Windows console defaults to cp1252, which can't encode the emoji banners
# below and crashes with UnicodeEncodeError. Force UTF-8 on both streams
# before any print() runs. Ignored on platforms where reconfigure is a no-op.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Make Python's ssl module use the operating system's trust store instead of
# the bundled Mozilla store. This is required on machines where an antivirus
# (Avast, Kaspersky, corporate MITM proxy, etc.) intercepts HTTPS and installs
# its own root CA into the OS trust store — the Mozilla store won't have that
# root, so every yt-dlp request fails with CERTIFICATE_VERIFY_FAILED.
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# Suppress warnings early
warnings.filterwarnings("ignore", category=UserWarning, message=".*pkg_resources.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*pkg_resources.*")


def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 7):
        print("❌ Error: Python 3.7 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    return True


def check_dependency(package_name, import_name=None):
    """Check if a package is installed"""
    if import_name is None:
        import_name = package_name

    try:
        spec = importlib.util.find_spec(import_name)
        return spec is not None
    except ImportError:
        return False


def install_package(package_name):
    """Install a package using pip"""
    try:
        print(f"📦 Installing {package_name}...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", package_name, "--user"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False


def check_and_install_dependencies():
    """Check and install required dependencies"""
    dependencies = [
        ("yt-dlp", "yt_dlp"),
        ("aiohttp", "aiohttp"),
        ("aiofiles", "aiofiles"),
        ("tqdm", "tqdm"),
        ("truststore", "truststore"),
        ("pywebview", "webview"),
    ]

    missing_deps = []

    print("🔍 Checking dependencies...")

    for package_name, import_name in dependencies:
        if not check_dependency(package_name, import_name):
            missing_deps.append(package_name)
            print(f"❌ Missing: {package_name}")
        else:
            print(f"✅ Found: {package_name}")

    if missing_deps:
        print(f"\n📦 Installing {len(missing_deps)} missing package(s)...")

        for package in missing_deps:
            if install_package(package):
                print(f"✅ Installed: {package}")
            else:
                print(f"❌ Failed to install: {package}")
                print(f"Please install manually: pip install {package}")
                return False

        print("✅ All dependencies installed!")
    else:
        print("✅ All dependencies are already installed!")

    return True


def check_required_files():
    """Check if required files exist"""
    current_dir = Path(__file__).parent
    required_files = [
        "app/main.py",
        "app/bridge.py",
    ]

    missing_files = []

    for file_name in required_files:
        file_path = current_dir / file_name
        if not file_path.exists():
            missing_files.append(file_name)

    if missing_files:
        print("❌ Missing required files:")
        for file_name in missing_files:
            print(f"   - {file_name}")
        print("\nPlease ensure all files are in the same directory.")
        return False

    return True


def launch_application():
    """Launch the main application.

    Prefers the new pywebview UI. If pywebview isn't importable (missing
    dep, WebView2 runtime unavailable), falls back to the Tkinter GUI so
    the app still starts.
    """
    try:
        print("\n🚀 Launching YouTube Downloader Pro...")

        current_dir = Path(__file__).parent
        sys.path.insert(0, str(current_dir))

        try:
            import webview  # noqa: F401 — probe the pywebview install
            from app.main import main
            print("[info] using pywebview UI")
        except ImportError as exc:
            print(f"[warn] pywebview unavailable ({exc}); falling back to Tkinter UI")
            from app.legacy_gui import main

        main()

    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure all files are in the same directory.")
        return False
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        return False

    return True


def main():
    """Main launcher function"""
    print("=" * 60)
    print("🎬 YouTube Downloader Pro - Enhanced Edition")
    print("=" * 60)

    # Check Python version
    if not check_python_version():
        input("Press Enter to exit...")
        return

    # Check required files
    if not check_required_files():
        input("Press Enter to exit...")
        return

    # Check and install dependencies
    if not check_and_install_dependencies():
        print("\n❌ Failed to install required dependencies.")
        print("Please install manually using:")
        print("pip install yt-dlp aiohttp aiofiles tqdm")
        input("Press Enter to exit...")
        return

    # Launch the application
    try:
        launch_application()
    except KeyboardInterrupt:
        print("\n👋 Application closed by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()