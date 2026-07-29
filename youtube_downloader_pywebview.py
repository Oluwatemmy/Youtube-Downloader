"""YouTube Downloader Pro — pywebview UI entry point.

Startup order matters:
  1. UTF-8 stdout so nothing crashes with emoji or non-ASCII prints
  2. `truststore.inject_into_ssl` so the OS trust store handles antivirus
     MITM certs (otherwise every yt-dlp request fails)
  3. FFmpeg check (auto-download on Windows if missing)
  4. Create the pywebview window pointing at ui/index.html with a
     `PyBridge` instance as the JS-side api
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------
# 1. UTF-8 stdout / stderr
# ---------------------------------------------------------------
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# ---------------------------------------------------------------
# 2. OS trust store for SSL
# ---------------------------------------------------------------
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass


# ---------------------------------------------------------------
# 3. FFmpeg discovery + auto-install
# ---------------------------------------------------------------

_FFMPEG_WIN64_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/latest/download/"
    "ffmpeg-master-latest-win64-gpl.zip"
)


def _find_ffmpeg() -> str | None:
    """Return the path to ffmpeg, checking PATH and a few bundled locations."""
    hit = shutil.which("ffmpeg")
    if hit:
        return hit
    for candidate in (
        Path(sys.executable).parent / "ffmpeg" / "bin" / "ffmpeg.exe",
        Path(__file__).parent / "ffmpeg" / "bin" / "ffmpeg.exe",
    ):
        if candidate.exists():
            os.environ["PATH"] = f"{candidate.parent}{os.pathsep}{os.environ.get('PATH', '')}"
            return str(candidate)
    return None


def _download_ffmpeg_headless() -> bool:
    """Download + extract ffmpeg to <app>/ffmpeg/bin/ without any UI.

    Used before the pywebview window exists so we don't have a place to
    show a progress dialog yet. Prints to stderr for visibility.
    """
    import io
    import urllib.request
    import zipfile

    install_dir = Path(__file__).parent / "ffmpeg"
    install_dir.mkdir(exist_ok=True)
    bin_dst = install_dir / "bin"
    bin_dst.mkdir(exist_ok=True)

    print(f"[ffmpeg] downloading {_FFMPEG_WIN64_URL}", file=sys.stderr, flush=True)
    try:
        req = urllib.request.Request(_FFMPEG_WIN64_URL, headers={"User-Agent": "YouTubeDownloaderPro/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0)) or None
            buf = io.BytesIO()
            downloaded = 0
            next_report = 5_000_000
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                buf.write(chunk)
                downloaded += len(chunk)
                if downloaded >= next_report:
                    if total:
                        print(f"[ffmpeg] {downloaded/1_048_576:.0f} / {total/1_048_576:.0f} MB",
                              file=sys.stderr, flush=True)
                    next_report += 10_000_000

        print("[ffmpeg] extracting…", file=sys.stderr, flush=True)
        with zipfile.ZipFile(buf) as zf:
            for name in zf.namelist():
                lower = name.lower()
                if lower.endswith("/bin/ffmpeg.exe") or lower.endswith("/bin/ffprobe.exe"):
                    target = bin_dst / Path(name).name
                    with zf.open(name) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)

        if not (bin_dst / "ffmpeg.exe").exists():
            print("[ffmpeg] ERROR: ffmpeg.exe not found in archive", file=sys.stderr)
            return False

        os.environ["PATH"] = f"{bin_dst}{os.pathsep}{os.environ.get('PATH', '')}"
        print("[ffmpeg] installed", file=sys.stderr, flush=True)
        return True

    except Exception as exc:
        print(f"[ffmpeg] install failed: {exc}", file=sys.stderr)
        return False


def _ensure_ffmpeg() -> None:
    """Ensure ffmpeg is available. Auto-installs on Windows if missing.

    Runs before window creation so downloads work from the first URL the
    user pastes. On non-Windows, we just warn — users normally have a
    package manager.
    """
    if _find_ffmpeg():
        return
    if sys.platform != "win32":
        print("[warn] ffmpeg not found. Install via your package manager.", file=sys.stderr)
        return
    _download_ffmpeg_headless()


# ---------------------------------------------------------------
# 4. window bootstrap
# ---------------------------------------------------------------

def main() -> None:
    _ensure_ffmpeg()

    import webview
    from pywebview_bridge import PyBridge

    api = PyBridge()

    # The UI folder ships alongside this script in dev and inside the
    # PyInstaller bundle in production. sys._MEIPASS points at the
    # extracted resources when frozen.
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    ui_index = base / "ui" / "index.html"
    if not ui_index.exists():
        print(f"[fatal] ui/index.html not found at {ui_index}", file=sys.stderr)
        sys.exit(1)

    window = webview.create_window(
        title="YouT Manager",
        url=str(ui_index),
        js_api=api,
        width=1280, height=820,
        min_size=(900, 600),
        background_color="#1B1B1B",
        resizable=True,
        # Use the native OS window chrome for the title bar / min-max-close
        # controls. Frameless mode on WebView2 doesn't reliably support
        # CSS-based dragging or resize handles, and users lose the ability
        # to move / resize / snap the window — which is worse than losing
        # a bespoke title bar.
        frameless=False,
    )
    api.attach(window)

    webview.start(debug=False)


if __name__ == "__main__":
    main()
