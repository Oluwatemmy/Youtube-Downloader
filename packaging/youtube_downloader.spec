# PyInstaller spec for YouT Manager
# ----------------------------------
# One-folder build (not one-file) — faster startup, less antivirus
# flakiness with WebView2. Produces dist/YouTManager/YouTManager.exe
# plus an _internal/ folder of DLLs and resources.
#
# Run from the repo root:
#     venv\Scripts\pyinstaller packaging\youtube_downloader.spec --clean

from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files

# Spec files run with __file__ set weirdly by PyInstaller; use SPEC.
REPO_ROOT = Path(SPECPATH).parent   # packaging/ → repo root

# Bundle everything yt_dlp needs. It has ~1000 extractors that get
# lazily imported by string, so PyInstaller can't see them without help.
ytdlp_datas, ytdlp_binaries, ytdlp_hidden = collect_all("yt_dlp")

# pywebview's backend gets picked at runtime — force include the Windows
# Edge Chromium backend so the frozen build knows about it.
pywebview_datas = collect_data_files("webview")

# Static assets shipped alongside the .exe. Layout inside the bundle:
#   YouTManager/
#     YouTManager.exe
#     _internal/            (Python DLLs, packages, etc.)
#     ui/index.html         (frontend)
#     ui/styles.css
#     ui/app.js
#     assets/icon.ico
datas = [
    (str(REPO_ROOT / "ui"),     "ui"),
    (str(REPO_ROOT / "assets"), "assets"),
] + ytdlp_datas + pywebview_datas

hiddenimports = list(ytdlp_hidden) + [
    # pywebview's backend selection uses importlib — name them here so
    # PyInstaller actually copies them into the bundle.
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
    # truststore hooks Python's ssl module at import time; make sure
    # it's present in the frozen build even though we import it lazily.
    "truststore",
]

a = Analysis(
    [str(REPO_ROOT / "app" / "main.py")],
    pathex=[str(REPO_ROOT)],
    binaries=list(ytdlp_binaries),
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Tkinter fallback is not needed in the frozen build — the app
        # ships pywebview, so exclude tkinter to shave ~15MB.
        "tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="YouTManager",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,        # UPX often triggers antivirus false positives
    console=False,    # no cmd window — this is a GUI app
    disable_windowed_traceback=False,
    icon=str(REPO_ROOT / "assets" / "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="YouTManager",
)
