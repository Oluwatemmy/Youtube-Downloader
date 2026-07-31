"""JS <-> Python bridge for the pywebview UI.

Everything that the HTML/JS front-end can call goes through the `PyBridge`
class as `window.pywebview.api.<method>`. Downloads run on a thread pool
inside `DownloadManager`; progress events push into JS via
`window.evaluate_js('window.onEvent(...)')`.

The item schema shared with the JS side (must match ui/app.js):

    id       int
    url      str
    file     str                 (output filename)
    title    str                 (video title)
    uploader str
    dur      str                 (e.g. "42:18")
    quality  str                 (e.g. "1080p MP4")
    status   'Queued' | 'Downloading' | 'Paused' | 'Done' | 'Failed'
    pct      int    (0-100)
    size     str                 (e.g. "412 MB")
    mb       int                 (numeric bytes/1024/1024 for sort)
    speed    str
    eta      str
    added    str                 (HH:MM:SS)
    got      str                 (e.g. "164 MB / 780 MB")
    error    str | None
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yt_dlp


# Displayed in the sidebar and available to JS via `api.app_version()`.
# Bump per release. Keep in sync with the `-Version` arg to build.ps1.
APP_VERSION = "v2.0.0"


# ---------------------------------------------------------------
# paths
# ---------------------------------------------------------------

def _config_dir() -> Path:
    """AppData location for settings/analytics/history."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        base = Path.home() / ".config"
    d = base / "YouTubeDownloader"
    d.mkdir(parents=True, exist_ok=True)
    return d


SETTINGS_FILE   = _config_dir() / "settings.json"
ANALYTICS_FILE  = _config_dir() / "analytics.json"
HISTORY_FILE    = _config_dir() / "history.json"
QUEUE_FILE      = _config_dir() / "queue.json"


# ---------------------------------------------------------------
# formatting helpers
# ---------------------------------------------------------------

def _fmt_bytes(n: Optional[int]) -> str:
    if not n or n <= 0:
        return "—"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _fmt_duration(seconds: Optional[float]) -> str:
    if not seconds or seconds < 0:
        return "—"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _fmt_speed(bps: Optional[float]) -> str:
    if not bps or bps <= 0:
        return "—"
    return f"{_fmt_bytes(bps)}/s".replace(" ", " ")


_FOLDER_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

def _sanitize_folder_name(name: str) -> str:
    """Return a Windows-safe folder name. Replaces illegal characters,
    strips trailing dots/spaces (which Windows drops silently), and caps
    length so path-limit issues stay unlikely for the files inside."""
    cleaned = _FOLDER_INVALID.sub("-", name or "").strip(". ")[:150]
    return cleaned or "Playlist"


# ---- URL / video id normalization ---------------------------------

# All the URL shapes YouTube serves that resolve to the same video.
# The important part is capturing the video id so we can dedupe across
# different-looking URLs like:
#   youtube.com/watch?v=ABC  |  youtu.be/ABC  |  youtube.com/shorts/ABC
#   youtube.com/watch?v=ABC&list=X&t=30s      (same video, playlist/timestamp trimmed)
_VIDEO_ID_RE = re.compile(
    r"""(?:
        youtu\.be/                        |
        youtube\.com/watch\?[^\s]*[?&]v=  |
        youtube\.com/watch\?v=            |
        youtube\.com/(?:shorts|live|embed)/
    )([\w-]{6,})""",
    re.IGNORECASE | re.VERBOSE,
)

def _extract_video_id(url: str) -> str:
    """Return YouTube's 11-ish-char video id if `url` is a single-video
    link, otherwise empty string (playlists, channel pages, etc.).
    Used to detect duplicates across cosmetically-different URLs."""
    m = _VIDEO_ID_RE.search(url or "")
    return m.group(1) if m else ""


_RATE_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([kmgKMG]?)\s*$")


def _parse_ratelimit(s: Any) -> int:
    """Parse a human-friendly speed limit string ("500K", "1.5M", "2G",
    "1048576") into bytes/sec for yt-dlp's `ratelimit` option. Returns
    0 for unlimited (empty / invalid / zero). Matches how curl/wget parse
    these — K = 1024, M = 1024*1024, etc."""
    if not s:
        return 0
    m = _RATE_RE.match(str(s))
    if not m:
        return 0
    n = float(m.group(1))
    unit = (m.group(2) or "").lower()
    mult = {"": 1, "k": 1024, "m": 1024 ** 2, "g": 1024 ** 3}.get(unit, 1)
    return int(n * mult)


def _app_is_foreground() -> bool:
    """True if our own process owns the foreground Windows window.
    Used to suppress the batch-complete toast when the user is already
    looking at the app — they can see the row turn Done, a toast on top
    of that is just noise. Matches Discord / Slack / VS Code behaviour.
    Silent False on non-Windows or if ctypes calls fail."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return False
        pid = ctypes.c_ulong(0)
        ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value == os.getpid()
    except Exception:
        return False


def _toast_icon_path() -> str:
    """Absolute path to the app icon used by Windows toast notifications.
    Falls back to empty string when the file isn't reachable — winotify
    just shows the default app icon in that case."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent.parent
    for name in ("icon.ico", "icon.png"):
        p = base / "assets" / name
        if p.exists():
            return str(p.resolve())
    return ""


def _fire_batch_toast(done: int, failed: int) -> None:
    """Windows toast notification when a batch of downloads finishes.
    Silent no-op on non-Windows, if winotify isn't available, or when the
    app is already in focus (the user doesn't need a toast on top of the
    UI they're actively looking at)."""
    if sys.platform != "win32":
        return
    if _app_is_foreground():
        return
    try:
        from winotify import Notification
    except ImportError:
        return
    total = done + failed
    if total == 1:
        title = "Download complete" if done else "Download failed"
        msg = "1 file finished" if done else "1 file failed"
    else:
        title = "Downloads finished"
        parts = []
        if done:   parts.append(f"{done} complete")
        if failed: parts.append(f"{failed} failed")
        msg = " · ".join(parts) or f"{total} finished"
    try:
        icon = _toast_icon_path()
        kwargs = {"app_id": "YouT Manager", "title": title, "msg": msg}
        if icon:
            kwargs["icon"] = icon
        Notification(**kwargs).show()
    except Exception:
        traceback.print_exc()


_JS_RUNTIME_CACHE: Optional[Dict[str, Any]] = None


def _app_root_for_bin() -> Path:
    """Where to look for bundled helper binaries (bin/qjs.exe, etc.).
    When frozen this is the folder next to YouTManager.exe; in dev mode
    it's the repo root two levels up from this file (app/bridge.py)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _detect_js_runtime() -> Dict[str, Any]:
    """Return a `js_runtimes` dict yt-dlp can use to deobfuscate YouTube's
    `nsig` signature — without it many videos only expose tiny storyboard
    formats and fail with "Requested format is not available". Cached
    across calls so we don't shell out for every metadata fetch.

    Order: bundled `bin/qjs.exe` first (ships with the app so users don't
    need to install anything), then PATH-discovered deno/bun/node/qjs.
    Returns `{}` if none are found — yt-dlp then falls back to its
    deprecated no-runtime path.
    """
    global _JS_RUNTIME_CACHE
    if _JS_RUNTIME_CACHE is not None:
        return _JS_RUNTIME_CACHE
    import shutil
    found: Dict[str, Any] = {}
    bundled = _app_root_for_bin() / "bin" / ("qjs.exe" if sys.platform == "win32" else "qjs")
    if bundled.exists():
        found["quickjs"] = {"path": str(bundled)}
    else:
        for name in ("deno", "bun", "node", "qjs"):
            path = shutil.which(name)
            if path:
                key = "quickjs" if name == "qjs" else name
                found[key] = {"path": path}
                break
    _JS_RUNTIME_CACHE = found
    return found


def _fmt_eta(seconds: Optional[float]) -> str:
    if not seconds or seconds <= 0:
        return "—"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60:02d}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60:02d}m"


# ---------------------------------------------------------------
# defaults
# ---------------------------------------------------------------

DEFAULT_SETTINGS: Dict[str, Any] = {
    "folder": str(Path.home() / "Downloads" / "YouTube"),
    "quality": "1080p",
    "format": "MP4",
    "concurrent": 3,
    "autoload": True,
    "desc": False,
    "dupes": True,
    "tray": False,
    "startup": False,
    "retries": 3,
    "timeout": 30,
    "ytdlp": "",
    "cookies_browser": "none",
    "cookies_file": "",           # path to a cookies.txt exported from a browser
    "wizard_seen": False,         # first-run cookies wizard has been shown
    "mp3_bitrate": "192",         # default kbps for MP3 extraction (320/256/192/128/96)
    "ytdlp_last_check": "",       # ISO timestamp of last update check (auto-runs weekly)
    "speed_limit": "",            # e.g. "500K" or "1M"; blank = unlimited
}

DEFAULT_ANALYTICS: Dict[str, Any] = {
    "stats": {
        "total": 0, "successful": 0, "failed": 0, "dataGB": 0.0,
        "since": datetime.now().strftime("%d %b %Y"),
        "failedNote": "",
    },
    "perDay": [[0, 0] for _ in range(30)],
    "history": [],
}


def _load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(default))  # deep copy
    try:
        with open(path, "r", encoding="utf-8") as f:
            merged = json.loads(json.dumps(default))
            merged.update(json.load(f))
            return merged
    except (json.JSONDecodeError, OSError):
        return json.loads(json.dumps(default))


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


# ---------------------------------------------------------------
# download manager
# ---------------------------------------------------------------

class _ItemLogger:
    """yt-dlp expects a logger with debug/info/warning/error methods.
    We route each call into the DownloadManager's per-item log buffer,
    with a css tone matching the severity."""
    def __init__(self, mgr: "DownloadManager", id_: int):
        self.mgr = mgr
        self.id = id_

    def debug(self, msg: str) -> None:
        # yt-dlp prefixes real debug lines with "[debug]" — those are
        # noisy internals we don't want in the UI. Everything else at
        # debug level is actually an info-style message (like the
        # "[youtube] extracting ..." lines).
        s = str(msg)
        if s.startswith("[debug]"):
            return
        self.mgr._log(self.id, "tx2", s)

    def info(self, msg):    self.mgr._log(self.id, "tx",   str(msg))
    def warning(self, msg): self.mgr._log(self.id, "warn", str(msg))
    def error(self, msg):   self.mgr._log(self.id, "bad",  str(msg))


class DownloadManager:
    """Owns the download queue and worker threads.

    Every mutation acquires `_lock`. Progress events fire on the worker
    thread and are pushed to JS via the `on_event` callback the caller
    supplied at construction time.
    """

    def __init__(self, settings: Dict[str, Any], on_event: Callable[[Dict], None],
                 on_finished: Optional[Callable[[Dict], None]] = None):
        self._items: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._next_id = 1
        self._settings = settings
        self._on_event = on_event
        # Called with the item dict when a download reaches a terminal
        # state (Done or Failed) — the PyBridge uses this to append to
        # history so analytics stays live.
        self._on_finished = on_finished or (lambda item: None)
        self._pool = ThreadPoolExecutor(max_workers=max(1, int(settings.get("concurrent", 3))))
        self._futures: Dict[int, Future] = {}
        self._cancelled: set[int] = set()  # ids the user asked to stop
        self._last_emit: Dict[int, float] = {}  # id -> last emit ts, for throttling
        # Batch-complete toast tracking. Flipped True on first Downloading
        # status; when the queue fully settles (no Queued/Downloading/Paused
        # items left) we fire a Windows toast and flip it back False.
        self._batch_active: bool = False
        self._batch_done_count: int = 0
        self._batch_fail_count: int = 0
        # Per-item captured log lines from yt-dlp. Kept in memory only —
        # logs are ephemeral per session, not part of queue persistence.
        # Each entry is [text, tone] where tone is a css class name.
        self._logs: Dict[int, List[List[str]]] = {}

        # Restore any queue that was persisted from the previous session.
        # Anything that had been Downloading gets flipped to Paused since
        # we can't actually resume mid-stream after a restart.
        self._load()

    # ---- public API ----

    def all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(i) for i in self._items]

    def add(self, url: str, format_id: Optional[str] = None,
            audio: bool = False, bitrate: str = "192",
            playlist_folder: str = "", container: str = "",
            force: bool = False, subs: bool = False) -> int:
        url = url.strip()
        if not url:
            raise ValueError("empty url")
        with self._lock:
            # Dedupe by canonical video id so ?t=30s / youtu.be / &list=X
            # variants of the same video don't queue twice. `force=True`
            # bypasses the check (user explicitly picked "Download anyway"
            # in the UI's duplicate prompt).
            if self._settings.get("dupes") and not force:
                vid = _extract_video_id(url)
                for i in self._items:
                    same_url = i["url"] == url
                    same_vid = vid and _extract_video_id(i["url"]) == vid
                    if same_url or same_vid:
                        return -1
            item = self._new_item(url)
            # Audio mode overrides any video format_id — we always want
            # bestaudio and let FFmpegExtractAudio postprocess to MP3.
            item["format_id"] = None if audio else format_id
            item["audio_only"] = bool(audio)
            item["audio_bitrate"] = str(bitrate or "192")
            # When set, the download goes into <folder>/<playlist_folder>/
            # so playlist items don't scatter across the root download dir.
            item["playlist_folder"] = _sanitize_folder_name(playlist_folder) if playlist_folder else ""
            # Target output container (mp4 / webm / mkv). Tells yt-dlp to
            # remux the merged file into this extension so the output
            # matches the label the user picked, instead of defaulting to
            # mkv/webm when video and audio streams have mixed containers.
            item["container"] = (container or "").lower()
            # Marks a re-download of an already-in-queue/history video.
            # The download step uses this to append " (1)", " (2)", ...
            # to the output filename instead of overwriting the earlier file.
            item["is_redownload"] = bool(force)
            # Whether to also fetch subtitles for this item (English + auto).
            item["subs"] = bool(subs)
            self._items.append(item)
        self._emit_queue()
        self._persist()
        self._log(item["id"], "tx3", "[queue] added — waiting for a worker slot")
        # Kick off metadata + download in one background task
        self._futures[item["id"]] = self._pool.submit(self._run, item["id"])
        return item["id"]

    def add_batch(self, urls: List[str], format_id: Optional[str] = None,
                  audio: bool = False, bitrate: str = "192",
                  playlist_folder: str = "", container: str = "",
                  force: bool = False, subs: bool = False) -> List[int]:
        return [self.add(u, format_id=format_id, audio=audio, bitrate=bitrate,
                         playlist_folder=playlist_folder, container=container,
                         force=force, subs=subs)
                for u in urls if u.strip()]

    def remove(self, id_: int) -> None:
        """Delete an item from the queue AND its file(s) from disk.

        This is what the user wants when they click Delete — a truly gone
        item, not just hidden from the list. Sweeps the completed output,
        any .part file left behind, and the .ytdl resume marker.
        """
        # Snapshot the item before we drop it from the queue so we know
        # what files to clean up.
        with self._lock:
            it = self._find(id_)
            captured = dict(it) if it else None
            self._items = [i for i in self._items if i["id"] != id_]
        self._cancelled.add(id_)

        if captured:
            out = captured.get("output_path")
            if out and Path(out).exists():
                # Completed download: delete THIS row's exact file plus its
                # own partial siblings only. A title-glob would also match
                # a sibling "Title (1).mp4" from a re-downloaded duplicate
                # and wipe it — not what the user asked for.
                target = Path(out)
                try:
                    target.unlink()
                except OSError:
                    pass
                for p in target.parent.glob(f"{target.stem}*"):
                    if p.suffix.lower() in (".part", ".ytdl", ".description"):
                        try:
                            p.unlink()
                        except OSError:
                            pass
            else:
                # Never completed (Queued / Paused / Failed): fall back to
                # a title-based glob to sweep leftover partials. Skips
                # finished-file extensions to avoid clobbering an in-flight
                # duplicate row's actual file.
                title = (captured.get("title") or "").strip()
                if title:
                    base_dir = Path(self._settings.get("folder", str(Path.home() / "Downloads")))
                    sub = captured.get("playlist_folder") or ""
                    download_dir = base_dir / sub if sub else base_dir
                    stem = title.replace(":", "-").replace("/", "-").replace("?", "")[:120]
                    for pattern in (f"{stem}*.part*", f"{stem}*.ytdl"):
                        for p in download_dir.glob(pattern):
                            if p.suffix.lower() in (".part", ".ytdl"):
                                try:
                                    p.unlink()
                                except OSError:
                                    pass

        self._emit_queue()
        self._persist()

    def pause(self, id_: int) -> None:
        """Suspend the download but keep the .part file so Resume can
        pick up where it left off."""
        self._cancelled.add(id_)
        self._update(id_, status="Paused", speed="paused", eta="—")

    def resume(self, id_: int) -> None:
        """Continue a paused download from the existing .part file.
        No-op if a future for this item is already in flight (Queued
        items already have one waiting in the pool)."""
        with self._lock:
            it = self._find(id_)
            if not it:
                return
            it["status"] = "Queued"
        self._cancelled.discard(id_)
        existing = self._futures.get(id_)
        if existing and not existing.done():
            # Already queued or running — just clear the cancel flag and
            # let the existing future do its job. Emitting keeps the UI
            # in sync (status back to Queued/Downloading).
            self._emit_queue()
            return
        self._futures[id_] = self._pool.submit(self._run, id_, fresh=False)
        self._emit_queue()

    def retry(self, id_: int) -> None:
        """Restart a failed download from the beginning."""
        with self._lock:
            it = self._find(id_)
            if not it:
                return
            it["status"] = "Queued"
            it["pct"] = 0
            it["got"] = "0 B"
            it["error"] = None
        self._cancelled.discard(id_)
        self._futures[id_] = self._pool.submit(self._run, id_, fresh=True)
        self._emit_queue()

    def stop(self, id_: int) -> None:
        """Stop the download AND discard the .part so the next Resume
        actually starts over from byte 0."""
        self._cancelled.add(id_)
        self._delete_partials_for(id_)
        self._update(id_, status="Paused", pct=0, got="0 B",
                     speed="—", eta="—")

    def _delete_partials_for(self, id_: int) -> None:
        """Remove any .part / .ytdl leftovers for one queue item."""
        with self._lock:
            it = self._find(id_)
        if not it:
            return
        title = (it.get("title") or "").strip()
        if not title:
            return
        download_dir = Path(self._settings.get("folder", str(Path.home() / "Downloads")))
        stem = title.replace(":", "-").replace("/", "-").replace("?", "")[:120]
        for pattern in (f"{stem}*.part*", f"{stem}*.ytdl"):
            for p in download_dir.glob(pattern):
                try:
                    p.unlink()
                except OSError:
                    pass

    def start_all(self) -> None:
        with self._lock:
            ids = [i["id"] for i in self._items if i["status"] in ("Queued", "Paused", "Failed")]
        for i in ids:
            self._cancelled.discard(i)
            self._futures[i] = self._pool.submit(self._run, i)

    def open_folder(self, id_: int) -> None:
        with self._lock:
            it = self._find(id_)
        target = None
        if it and it.get("output_path") and Path(it["output_path"]).exists():
            target = Path(it["output_path"]).parent
        else:
            target = Path(self._settings.get("folder", str(Path.home())))
        if sys.platform == "win32":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])

    def open_file(self, id_: int) -> bool:
        """Launch the downloaded file in the OS default player.

        Tries `output_path` first; if that's stale (the item was
        downloaded before the postprocessor-hook fix, so the path
        points at an intermediate that no longer exists), falls back
        to scanning the download folder for a file whose stem matches
        the video title.
        """
        with self._lock:
            it = self._find(id_)
        if not it:
            return False

        candidate = it.get("output_path")
        if not candidate or not Path(candidate).exists():
            candidate = self._locate_finished_file(it)
        if not candidate:
            return False

        try:
            if sys.platform == "win32":
                os.startfile(candidate)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", candidate])
            else:
                subprocess.Popen(["xdg-open", candidate])
        except OSError:
            return False

        # Cache the resolved path so subsequent opens skip the scan and
        # a future Delete knows exactly which file to remove.
        with self._lock:
            live = self._find(id_)
            if live:
                live["output_path"] = candidate
        self._persist()
        return True

    def _locate_finished_file(self, item: Dict[str, Any]) -> Optional[str]:
        """Best-effort scan of the download folder for the file matching
        this item's title. Used when output_path is stale/missing."""
        title = (item.get("title") or "").strip()
        if not title:
            return None
        base_dir = Path(self._settings.get("folder", str(Path.home() / "Downloads")))
        # Playlist items live in a subfolder — search there first.
        sub = item.get("playlist_folder") or ""
        download_dir = base_dir / sub if sub else base_dir
        if not download_dir.exists():
            return None
        # yt-dlp sanitizes some chars in the output template; mirror that.
        stem = title.replace(":", "-").replace("/", "-").replace("?", "").replace("|", "-")[:120]
        exts = (".mp3", ".m4a", ".mp4", ".mkv", ".webm") if item.get("audio_only") \
            else (".mp4", ".mkv", ".webm", ".m4a", ".mp3")
        # Prefer exact stem match, then fall back to prefix match.
        for ext in exts:
            p = download_dir / f"{stem}{ext}"
            if p.exists():
                return str(p)
        for ext in exts:
            for p in download_dir.glob(f"{stem}*{ext}"):
                # Skip .part / .ytdl artifacts.
                if p.suffix.lower() in exts:
                    return str(p)
        return None

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

    # ---- per-item log ----

    def _log(self, id_: int, tone: str, text: str) -> None:
        """Append one log line for an item and push an event to the UI.
        Tone is one of: tx (default), tx2, tx3, acc, ok, bad, warn."""
        text = str(text).rstrip()
        if not text:
            return
        buf = self._logs.setdefault(id_, [])
        buf.append([text, tone])
        if len(buf) > 300:  # cap so a chatty download doesn't grow unbounded
            del buf[:len(buf) - 300]
        self._on_event({"type": "log", "id": id_, "line": [text, tone]})

    def get_log(self, id_: int) -> List[List[str]]:
        return list(self._logs.get(id_, []))

    # ---- persistence ----

    def _load(self) -> None:
        """Restore the queue from QUEUE_FILE on startup."""
        if not QUEUE_FILE.exists():
            return
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                items = json.load(f) or []
        except (json.JSONDecodeError, OSError):
            return
        for it in items:
            # Anything that was mid-download when the app quit can't be
            # bit-perfectly resumed here — mark it Paused so the user can
            # explicitly retry.
            if it.get("status") == "Downloading":
                it["status"] = "Paused"
                it["speed"] = "—"
                it["eta"] = "—"
        self._items = items
        if items:
            self._next_id = max(int(i.get("id", 0)) for i in items) + 1

    def _persist(self) -> None:
        """Snapshot the current queue to disk. Called after every mutation."""
        try:
            with self._lock:
                snapshot = [dict(i) for i in self._items]
            tmp = QUEUE_FILE.with_suffix(QUEUE_FILE.suffix + ".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
            os.replace(tmp, QUEUE_FILE)
        except OSError:
            traceback.print_exc()

    # ---- internals ----

    def _find(self, id_: int) -> Optional[Dict[str, Any]]:
        for i in self._items:
            if i["id"] == id_:
                return i
        return None

    def _new_item(self, url: str) -> Dict[str, Any]:
        id_ = self._next_id
        self._next_id += 1
        return {
            "id": id_, "url": url, "file": url, "title": url,
            "uploader": "—", "dur": "—", "quality": "—",
            "status": "Queued", "pct": 0,
            "size": "—", "mb": 0, "speed": "—", "eta": "queued",
            "added": datetime.now().strftime("%H:%M:%S"),
            "got": "0 B", "error": None, "output_path": None,
            "thumbnail": "",
            "audio_only": False, "audio_bitrate": "192",
            "playlist_folder": "", "container": "",
        }

    def _update(self, id_: int, **fields) -> None:
        with self._lock:
            it = self._find(id_)
            if not it:
                return
            it.update(fields)
            snap = dict(it)
        # Throttle to ~10 Hz per item so a burst of progress hooks doesn't
        # thrash evaluate_js. Terminal statuses always emit.
        now = time.monotonic()
        status = fields.get("status") or snap.get("status")
        is_terminal = status in ("Done", "Failed", "Paused")
        last = self._last_emit.get(id_, 0)
        if is_terminal or now - last >= 0.1:
            self._last_emit[id_] = now
            self._emit_progress(id_)
        if status == "Downloading":
            self._batch_active = True
        if status == "Done":
            self._batch_done_count += 1
        elif status == "Failed":
            self._batch_fail_count += 1
        if status in ("Done", "Failed"):
            # A download resolved — persist so restart doesn't lose it,
            # and let the bridge log it to history.
            self._persist()
            try:
                self._on_finished(snap)
            except Exception:
                traceback.print_exc()
            self._maybe_batch_complete_toast()

    def _maybe_batch_complete_toast(self) -> None:
        """Fires a Windows toast when the last active download resolves.
        A "batch" here is loosely anything the user kicked off during the
        current session — no need to make them explicitly group items."""
        if not self._batch_active:
            return
        with self._lock:
            pending = any(i.get("status") in ("Queued", "Downloading", "Paused")
                          for i in self._items)
        if pending:
            return
        done, failed = self._batch_done_count, self._batch_fail_count
        self._batch_active = False
        self._batch_done_count = 0
        self._batch_fail_count = 0
        if done + failed == 0:
            return
        _fire_batch_toast(done, failed)

    def _emit_progress(self, id_: int) -> None:
        with self._lock:
            it = self._find(id_)
            if not it:
                return
            snap = dict(it)
        self._on_event({"type": "progress", "id": id_, "data": snap})

    def _emit_queue(self) -> None:
        self._on_event({"type": "queue", "data": self.all()})

    # ---- yt-dlp bridge ----

    # Player-client fallback chain. `None` means "let yt-dlp pick" — as of
    # 2026-07-31 that auto-selects visionos + android_vr, which surface the
    # full 144p–2160p ladder without needing a JS runtime. tv_embedded and
    # android are kept as fallbacks in case the defaults ever stop working
    # against YouTube's bot check.
    _CLIENT_CHAIN = (None, ["tv_embedded"], ["android"])

    def _ydl_opts(self, extra: Optional[Dict[str, Any]] = None,
                  player_client: Optional[List[str]] = None,
                  use_cookies: bool = True) -> Dict[str, Any]:
        """Shared yt-dlp options.

        `use_cookies=False` skips the cookies-from-browser step even when
        the user has one configured — used as a fallback when the browser
        is open and yt-dlp can't unlock the cookie DB.
        """
        opts: Dict[str, Any] = {
            "quiet": True, "no_warnings": True,
            "socket_timeout": int(self._settings.get("timeout", 30)),
            "retries": int(self._settings.get("retries", 3)),
            "fragment_retries": int(self._settings.get("retries", 3)),
            "no_check_certificate": True,
            # Never try to resume a previous partial file. YouTube rotates
            # its format URLs frequently, so a stale .part file leads to
            # HTTP 416 "Range not satisfiable". Fresh downloads every time.
            "continuedl": False,
            "overwrites": True,
            "nopart": False,   # still write to .part, just don't resume from it
            # Chunked HTTP downloads (10 MB) — friendlier to CDN edge nodes
            # and less likely to hit range-request weirdness on large files.
            "http_chunk_size": 10 * 1024 * 1024,
        }
        # yt-dlp needs a JS runtime to decrypt YouTube's nsig — without it
        # many videos only return storyboard formats and error out with
        # "Requested format is not available". Auto-detect node/deno/bun/qjs.
        js_rt = _detect_js_runtime()
        if js_rt:
            opts["js_runtimes"] = js_rt
        # Only pin a player_client when the caller explicitly asks for one.
        # Leaving it unset lets yt-dlp auto-pick working clients, which is
        # what we want for the first attempt in the fallback chain.
        if player_client:
            opts["extractor_args"] = {"youtube": {"player_client": player_client}}
        if use_cookies:
            # Prefer a static cookies.txt over browser cookies — it doesn't
            # need the browser closed and it's what we tell the user to
            # use when Chrome is always open.
            cookies_file = (self._settings.get("cookies_file") or "").strip()
            if cookies_file and Path(cookies_file).exists():
                opts["cookiefile"] = cookies_file
            else:
                browser = self._settings.get("cookies_browser")
                if browser and browser != "none":
                    opts["cookiesfrombrowser"] = (browser,)
        if extra:
            opts.update(extra)
        return opts

    def _has_cookies(self) -> bool:
        """True if any cookie source is configured (file OR browser)."""
        cf = (self._settings.get("cookies_file") or "").strip()
        if cf and Path(cf).exists():
            return True
        cb = self._settings.get("cookies_browser")
        return bool(cb and cb != "none")

    @staticmethod
    def _is_cookie_lock_error(exc: BaseException) -> bool:
        """True if the exception is 'browser is open, cookie DB is locked'.
        We want to silently retry without cookies in that case rather than
        surfacing a scary error to the user."""
        msg = str(exc).lower()
        return ("could not copy" in msg and "cookie" in msg) or "cookie database" in msg

    def _extract_with_fallback(self, url: str, **extra) -> Dict[str, Any]:
        """Try each player_client, with and without cookies, until one works.

        Order of attempts:
          1. tv_embedded + cookies   (best quality, satisfies bot check)
          2. tv_embedded no cookies  (in case cookies were locked)
          3. android + cookies       (bot-bypass, but only 360p)
          4. android no cookies
        Returns the info dict (with `_extraction_meta` attached describing
        which combo succeeded and whether cookies were unreachable) from
        the first success; raises the last real exception (non-cookie-lock)
        if everything fails.
        """
        last_exc: Optional[Exception] = None
        cookie_lock_seen = False
        cookies_configured = self._has_cookies()
        for client in self._CLIENT_CHAIN:
            cookie_modes = [True, False] if cookies_configured else [False]
            for use_cookies in cookie_modes:
                try:
                    with yt_dlp.YoutubeDL(
                        self._ydl_opts(extra, player_client=client, use_cookies=use_cookies)
                    ) as ydl:
                        info = ydl.extract_info(url, download=False)
                    if info:
                        # Attach so callers (and the UI) can tell why we
                        # may have been forced onto a lower-quality client.
                        info["_extraction_meta"] = {
                            "client": client,
                            "used_cookies": use_cookies,
                            "cookies_configured": cookies_configured,
                            "cookies_locked": cookie_lock_seen,
                        }
                        return info
                except Exception as exc:
                    # Don't record cookie-lock as the "real" error; keep
                    # trying so a locked browser doesn't kill the whole flow.
                    if self._is_cookie_lock_error(exc):
                        cookie_lock_seen = True
                    else:
                        last_exc = exc
                    continue
        if last_exc:
            raise last_exc
        raise RuntimeError("no info returned from any player_client")

    def _run(self, id_: int, fresh: bool = True) -> None:
        """Fetch metadata + download in a single worker task.

        `fresh=True`  → discard any existing .part and start from byte 0
                        (used by add / retry / stop→resume)
        `fresh=False` → try to continue from the .part left behind by a
                        prior pause (used by pause→resume)
        """
        if id_ in self._cancelled:
            return
        try:
            with self._lock:
                it = self._find(id_)
                if not it:
                    return
                url = it["url"]
            self._update(id_, status="Downloading", speed="—", eta="—")
            self._log(id_, "tx3", f"[info] starting download for {url}")

            # --- fetch metadata (best-effort) ---
            # Track which (client, use_cookies) combo actually worked so
            # the download step below reuses the exact same auth.
            info = None
            chosen_client: Optional[List[str]] = None
            chosen_use_cookies = True
            cookies_configured = self._has_cookies()
            last_meta_exc: Optional[Exception] = None
            for client in self._CLIENT_CHAIN:
                cookie_modes = [True, False] if cookies_configured else [False]
                for use_cookies in cookie_modes:
                    try:
                        with yt_dlp.YoutubeDL(
                            self._ydl_opts(player_client=client, use_cookies=use_cookies)
                        ) as ydl:
                            info = ydl.extract_info(url, download=False)
                        if info:
                            chosen_client = client
                            chosen_use_cookies = use_cookies
                            break
                    except Exception as exc:
                        if not self._is_cookie_lock_error(exc):
                            last_meta_exc = exc
                        info = None
                if info:
                    break
            if not info and last_meta_exc:
                self._update(id_, error=str(last_meta_exc)[:400])

            if info:
                # Audio-only items get an MP3-flavored label so users can
                # tell at a glance which rows will be muxed to .mp3 vs
                # kept as video.
                with self._lock:
                    it_snap = self._find(id_) or {}
                is_audio = bool(it_snap.get("audio_only"))
                bitrate = str(it_snap.get("audio_bitrate") or "192")
                picked_fmt_id = it_snap.get("format_id")

                # If the user picked a specific format, look up ITS stats
                # in info['formats'] instead of using yt-dlp's top-level
                # "best available" fields, which describe a different
                # format entirely (e.g. label showed 1080p WEBM when the
                # user picked 720p MP4).
                picked_stats = self._picked_format_stats(info, picked_fmt_id) if not is_audio else None
                if is_audio:
                    quality_label = f"MP3 {bitrate} kbps"
                    file_ext = "mp3"
                    total_bytes = 0
                elif picked_stats:
                    quality_label = f"{picked_stats['height']}p {picked_stats['ext'].upper()}"
                    file_ext = picked_stats["ext"]
                    total_bytes = picked_stats["bytes"] or 0
                else:
                    quality_label = self._quality_label(info)
                    file_ext = info.get("ext") or "mp4"
                    total_bytes = info.get("filesize") or info.get("filesize_approx") or 0

                self._update(
                    id_,
                    title=info.get("title") or url,
                    file=(info.get("title") or url) + "." + file_ext,
                    uploader=info.get("uploader") or "—",
                    dur=_fmt_duration(info.get("duration")),
                    quality=quality_label,
                    size=_fmt_bytes(total_bytes) if total_bytes else "—",
                    mb=int(total_bytes / 1_048_576) if total_bytes else 0,
                    thumbnail=self._pick_thumbnail(info),
                )

            if id_ in self._cancelled:
                self._update(id_, status="Paused")
                return

            # --- download ---
            base_dir = Path(self._settings.get("folder", str(Path.home() / "Downloads")))
            with self._lock:
                it_snap2 = self._find(id_) or {}
                subfolder = it_snap2.get("playlist_folder") or ""
                is_redownload = bool(it_snap2.get("is_redownload"))
            # Playlist items get their own subfolder so they don't scatter
            # across the root download folder alongside standalone videos.
            download_dir = base_dir / subfolder if subfolder else base_dir
            download_dir.mkdir(parents=True, exist_ok=True)
            outtmpl = str(download_dir / "%(title)s.%(ext)s")

            # Force-redownload: if a file with this title is already on disk,
            # bump the filename to "<title> (1).<ext>" (or (2), (3)...) so
            # the user ends up with both copies instead of the new one
            # silently overwriting the old.
            if is_redownload and info:
                base_title = (info.get("title") or "").strip()
                if base_title:
                    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", base_title).strip().rstrip(".")
                    # Any existing file with that stem, regardless of extension.
                    if any(download_dir.glob(f"{safe}.*")):
                        n = 1
                        while any(download_dir.glob(f"{safe} ({n}).*")):
                            n += 1
                        outtmpl = str(download_dir / f"%(title)s ({n}).%(ext)s")

            # Fresh runs sweep leftover .part / .ytdl files so yt-dlp's
            # resume logic can't try to continue from a stale byte offset
            # (which returns HTTP 416). Pause→Resume runs skip this so
            # they can actually pick up where they left off.
            title = (info.get("title") if info else "").strip()
            if fresh and title:
                stem_glob = title.replace(":", "-").replace("/", "-").replace("?", "")[:120]
                for pattern in (f"{stem_glob}*.part*", f"{stem_glob}*.ytdl"):
                    for p in download_dir.glob(pattern):
                        try:
                            p.unlink()
                        except OSError:
                            pass

            def hook(d: Dict[str, Any]) -> None:
                # Called on the download thread; must be quick.
                # KeyboardInterrupt (rather than DownloadError) so yt-dlp
                # treats it as terminal and doesn't retry the fragment —
                # otherwise the worker slot stays busy after a pause and
                # queued items never get a chance to run.
                if id_ in self._cancelled:
                    raise KeyboardInterrupt("cancelled by user")
                status = d.get("status")
                if status == "downloading":
                    downloaded = d.get("downloaded_bytes") or 0
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    # For DASH videos (all YouTube 720p+), `total_bytes`
                    # is the current FRAGMENT's total, not the whole file.
                    # yt-dlp populates fragment_index/count in that case,
                    # so use those for percentage instead of the byte
                    # ratio (which would jump 0→100 per fragment).
                    frag_i = d.get("fragment_index")
                    frag_n = d.get("fragment_count")
                    if frag_n:
                        pct = int(frag_i / frag_n * 100) if frag_i else 0
                    else:
                        pct = int(downloaded / total * 100) if total else 0
                    self._update(
                        id_,
                        pct=pct,
                        speed=_fmt_speed(d.get("speed")),
                        eta=_fmt_eta(d.get("eta")),
                        got=f"{_fmt_bytes(downloaded)} downloaded",
                        # Deliberately NOT setting `size` here — mid-download
                        # values are unreliable for fragmented streams and
                        # for anything that gets postprocessed (MP3, remux).
                        # pp_hook below stat()s the real file when done.
                    )
                elif status == "finished":
                    # Provisional path — for simple single-file downloads
                    # this is the final file. For anything that needs
                    # merging (video+audio) or postprocessing (MP3
                    # extraction), pp_hook below will overwrite it with
                    # the real output.
                    final_name = d.get("filename")
                    updates = {"pct": 100, "speed": "—", "eta": "—",
                               "output_path": final_name}
                    if final_name:
                        updates["file"] = Path(final_name).name
                    self._update(id_, **updates)

            def pp_hook(d: Dict[str, Any]) -> None:
                """Fires after each postprocessor step. The last one that
                fires is the true final file (mp3 after FFmpegExtractAudio,
                mp4 after FFmpegMerger, etc.). We also use it to correct
                `size` from the actual file on disk, since the value we
                had during download was per-fragment (DASH) or pre-mux
                (MP3 extraction) and often much smaller than reality."""
                if d.get("status") != "finished":
                    return
                info = d.get("info_dict") or {}
                final = (info.get("filepath")
                         or info.get("_filename")
                         or info.get("filename"))
                if not final:
                    return
                # Sync the display filename to what actually landed on
                # disk — otherwise "Download again" writes to "Title (1).mp4"
                # but the row still says "Title.mp4", and a later Delete
                # would target the wrong file.
                updates: Dict[str, Any] = {
                    "output_path": final,
                    "file":        Path(final).name,
                }
                try:
                    real_bytes = Path(final).stat().st_size
                    updates["size"] = _fmt_bytes(real_bytes)
                    updates["mb"] = int(real_bytes / 1_048_576)
                    updates["got"] = f"{_fmt_bytes(real_bytes)} · complete"
                except OSError:
                    pass
                self._update(id_, **updates)

            # Per-item mode: audio-only rips bestaudio and postprocesses
            # to MP3 with the user's chosen bitrate; video mode uses the
            # dialog-picked format_id (or the Settings quality default).
            with self._lock:
                cur = self._find(id_) or {}
                item_format = cur.get("format_id")
                is_audio = bool(cur.get("audio_only"))
                bitrate = str(cur.get("audio_bitrate") or "192")
                container = (cur.get("container") or "").lower()
                want_subs = bool(cur.get("subs"))

            extra_opts: Dict[str, Any] = {
                "outtmpl": outtmpl,
                "progress_hooks": [hook],
                "postprocessor_hooks": [pp_hook],
                # Route yt-dlp's own messages into the per-item log so the
                # Log tab shows what's actually happening for THIS video
                # (previously it showed a hardcoded fake trace).
                "logger": _ItemLogger(self, id_),
                "quiet": False, "no_warnings": False,
                "continuedl": not fresh,
                "overwrites": fresh,
            }
            # Per-item subtitle download (checkbox in Add URL). English +
            # auto-generated so it works on videos without a proper caption
            # track; format is vtt because it's the most player-friendly.
            if want_subs and not is_audio:
                extra_opts["writesubtitles"]      = True
                extra_opts["writeautomaticsub"]   = True
                extra_opts["subtitleslangs"]      = ["en", "en.*"]
                extra_opts["subtitlesformat"]     = "vtt"
            # Global speed limit — parsed from a human-friendly Settings
            # string like "500K" or "1M" (yt-dlp wants bytes/sec as int).
            rl = _parse_ratelimit(self._settings.get("speed_limit"))
            if rl:
                extra_opts["ratelimit"] = rl
            if is_audio:
                extra_opts["format"] = "bestaudio/best"
                extra_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": bitrate,
                }]
            else:
                # Map "1440p"/"1080p"/etc. shortcuts to real yt-dlp format
                # expressions; pass raw format IDs (like "137+bestaudio")
                # straight through.
                extra_opts["format"] = self._resolve_format(item_format)
                # Force the output container so the merged file matches
                # the label the user picked. Without this, YouTube's mixed
                # streams (mp4 video + webm audio) default to .mkv/.webm
                # even when the user asked for MP4. `merge_output_format`
                # supports only well-known containers.
                target_container = container or (
                    "mp4" if not item_format or item_format == "best" else ""
                )
                if target_container in ("mp4", "webm", "mkv", "m4a"):
                    extra_opts["merge_output_format"] = target_container

            # Reuse the same (player_client, use_cookies) combo that
            # succeeded during metadata extraction — otherwise the download
            # can hit the bot check even though we just verified formats.
            # Per-run overrides: `fresh` runs disable resume so a stale
            # .part can't cause HTTP 416; pause→resume runs enable it so
            # the download picks up where it stopped.
            opts = self._ydl_opts(extra_opts, player_client=chosen_client,
                                  use_cookies=chosen_use_cookies)

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            # Safety net: if the download didn't trigger any postprocessor
            # (single-file progressive download), pp_hook never fired and
            # `size` may still be missing. stat() the recorded output path.
            with self._lock:
                final_path = (self._find(id_) or {}).get("output_path")
            if final_path and Path(final_path).exists():
                try:
                    real_bytes = Path(final_path).stat().st_size
                    self._update(id_,
                                 size=_fmt_bytes(real_bytes),
                                 mb=int(real_bytes / 1_048_576),
                                 got=f"{_fmt_bytes(real_bytes)} · complete")
                except OSError:
                    pass

            self._update(id_, status="Done", pct=100, speed="—", eta="—", error=None)
            self._log(id_, "ok", "[done] download complete")

        except KeyboardInterrupt:
            # User-initiated pause / stop — clean exit, free the worker.
            self._update(id_, status="Paused", speed="—", eta="—")
            self._log(id_, "warn", "[paused] cancelled by user")
        except yt_dlp.DownloadError as exc:
            if id_ in self._cancelled:
                self._update(id_, status="Paused", speed="—", eta="—")
                self._log(id_, "warn", "[paused] cancelled by user")
            else:
                self._update(id_, status="Failed", speed="—", eta="—",
                             error=str(exc)[:400])
                self._log(id_, "bad", f"[error] {exc}")
        except Exception as exc:
            self._update(id_, status="Failed", speed="—", eta="—",
                         error=f"{type(exc).__name__}: {exc}"[:400])
            self._log(id_, "bad", f"[error] {type(exc).__name__}: {exc}")
            traceback.print_exc()

    # App-level quality shortcuts → yt-dlp format expressions. Each entry
    # ends in "…/bestvideo+bestaudio/best" so if no stream meets the ceiling
    # (e.g. user asks for 1440p on a 720p-only video), we fall through to
    # whatever the video does have instead of failing with "format not
    # available". Order matters: try the exact ceiling first, then merged
    # fallback, then any combined.
    _QUALITY_MAP: Dict[str, str] = {
        "best":  "bestvideo+bestaudio/best",
        "2160p": "bestvideo[height<=2160]+bestaudio/best[height<=2160]/bestvideo+bestaudio/best",
        "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]/bestvideo+bestaudio/best",
        "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/bestvideo+bestaudio/best",
        "720p":  "bestvideo[height<=720]+bestaudio/best[height<=720]/bestvideo+bestaudio/best",
        "480p":  "bestvideo[height<=480]+bestaudio/best[height<=480]/bestvideo+bestaudio/best",
        "360p":  "bestvideo[height<=360]+bestaudio/best[height<=360]/bestvideo+bestaudio/best",
        "audio": "bestaudio/best",
    }

    def _format_selector(self) -> str:
        q = self._settings.get("quality", "1080p")
        return self._QUALITY_MAP.get(q, self._QUALITY_MAP["1080p"])

    def _resolve_format(self, format_id: Optional[str]) -> str:
        """Translate whatever the UI sent us into a real yt-dlp format
        expression. Handles both quality shortcuts ("1440p") and
        already-resolved format IDs ("137+bestaudio")."""
        if not format_id:
            return self._format_selector()
        if format_id in self._QUALITY_MAP:
            return self._QUALITY_MAP[format_id]
        return format_id  # Trust it's a real yt-dlp format spec.

    def _quality_label(self, info: Dict[str, Any]) -> str:
        h = info.get("height")
        ext = info.get("ext") or "mp4"
        return f"{h}p {ext.upper()}" if h else ext.upper()

    def _picked_format_stats(self, info: Dict[str, Any], format_id: Optional[str]
                             ) -> Optional[Dict[str, Any]]:
        """Look up a specific format inside info['formats'] and return its
        height, ext, and estimated total size. Used so the queue row shows
        the picked format's numbers (e.g. "720p MP4 · 1.7 GB") instead of
        yt-dlp's top-level "best available" fields, which describe a
        different format entirely."""
        if not format_id or not info:
            return None
        formats = info.get("formats") or []
        # format_id like "136+bestaudio" -- the video part is what has height.
        video_id = format_id.split("+", 1)[0]
        video = next((f for f in formats if f.get("format_id") == video_id), None)
        if not video or not video.get("height"):
            return None
        vs = video.get("filesize") or video.get("filesize_approx") or 0
        needs_mux = video.get("acodec") in (None, "none")
        total = vs
        if needs_mux:
            # Add best-audio size for merged downloads so the size matches
            # what the user saw in the format dropdown.
            audios = [a for a in formats
                      if a.get("vcodec") == "none" and a.get("acodec") not in (None, "none")]
            best_audio = max(audios, key=lambda a: a.get("abr") or 0, default=None)
            if best_audio:
                total += best_audio.get("filesize") or best_audio.get("filesize_approx") or 0
        return {
            "height": video["height"],
            "ext":    (video.get("ext") or "mp4").lower(),
            "bytes":  total,
        }

    @staticmethod
    def _pick_thumbnail(info: Dict[str, Any]) -> str:
        """Best available thumbnail URL, preferring higher resolutions.
        yt-dlp puts them in info['thumbnails'] as a list sorted worst→best;
        info['thumbnail'] is the single "recommended" one. We want the
        best one that isn't ridiculously huge."""
        thumbs = info.get("thumbnails") or []
        if thumbs:
            # Pick the largest with width <= 640 (row + detail thumb are small).
            candidates = [t for t in thumbs if t.get("url") and (t.get("width") or 0) <= 640]
            if candidates:
                return max(candidates, key=lambda t: t.get("width") or 0)["url"]
            return thumbs[-1].get("url", "") or info.get("thumbnail", "")
        return info.get("thumbnail") or ""


# ---------------------------------------------------------------
# PyBridge — the object exposed to JavaScript
# ---------------------------------------------------------------

class PyBridge:
    """Every method on this class is callable from JS as
    `window.pywebview.api.<name>(args…)` and returns a JSON-serializable
    value (or promise on the JS side).
    """

    def __init__(self):
        self._window = None
        self._maximized = False
        self._settings = _load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        self._history: List[Dict[str, Any]] = self._load_history()
        self._mgr = DownloadManager(self._settings, self._push_event, self._record_finished)

    def install_crash_handler(self) -> None:
        """Route uncaught exceptions on the main thread and worker
        threads to a JS-side error modal so the user actually sees
        them instead of silently losing state to stderr."""
        def report(exc_type, exc_value, exc_tb):
            tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
            # Always log to stderr so it's captured even if JS side fails.
            sys.stderr.write(tb_text)
            sys.stderr.flush()
            self._push_event({
                "type": "crash",
                "name": getattr(exc_type, "__name__", "Error"),
                "message": str(exc_value)[:500],
                "traceback": tb_text[-4000:],  # cap so evaluate_js payload stays small
            })

        prev_hook = sys.excepthook
        def sys_hook(exc_type, exc_value, exc_tb):
            try:
                report(exc_type, exc_value, exc_tb)
            finally:
                prev_hook(exc_type, exc_value, exc_tb)
        sys.excepthook = sys_hook

        # Python 3.8+: also catch uncaught exceptions on worker threads.
        try:
            def thread_hook(args):
                report(args.exc_type, args.exc_value, args.exc_traceback)
            threading.excepthook = thread_hook
        except AttributeError:
            pass

    def _load_history(self) -> List[Dict[str, Any]]:
        if not HISTORY_FILE.exists():
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_history(self) -> None:
        try:
            tmp = HISTORY_FILE.with_suffix(HISTORY_FILE.suffix + ".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._history, f, indent=2)
            os.replace(tmp, HISTORY_FILE)
        except OSError:
            traceback.print_exc()

    def _record_finished(self, item: Dict[str, Any]) -> None:
        """Called from DownloadManager when a download reaches Done/Failed.
        Appends to history so analytics has real data.

        If a URL that previously Failed now succeeds, sweep the earlier
        Failed rows out — otherwise the same video would inflate both the
        Failed and Successful counts in Analytics."""
        now = datetime.now()
        entry = {
            "date":     now.date().isoformat(),
            "time":     now.strftime("%H:%M:%S"),
            "title":    item.get("title") or item.get("file") or "?",
            "url":      item.get("url", ""),
            "status":   item.get("status", "?"),
            "size":     item.get("size", "—"),
            "mb":       int(item.get("mb", 0) or 0),
            "quality":  item.get("quality", "—"),
            # Path on disk so check_duplicate can skip the "you've seen
            # this before" prompt after the user deletes the file.
            "output_path": item.get("output_path"),
        }
        url = entry["url"]
        if entry["status"] == "Done" and url:
            # Retry-after-failure supersedes the earlier failure entries
            # for the same URL. Keeps Done entries (the user might have
            # downloaded it twice deliberately).
            self._history = [h for h in self._history
                             if not (h.get("url") == url and h.get("status") == "Failed")]
        self._history.append(entry)
        # Cap history at 500 entries so the file stays sane.
        if len(self._history) > 500:
            self._history = self._history[-500:]
        self._save_history()

    # --- called by the app entry point, not JS ---

    def attach(self, window) -> None:
        self._window = window

    def _push_event(self, payload: Dict[str, Any]) -> None:
        if not self._window:
            return
        try:
            # pywebview escapes the arg automatically when you use %s style
            # placeholders. json.dumps is safe here because the payload is
            # our own dict (no user-controlled key names).
            self._window.evaluate_js(f"window.onEvent && window.onEvent({json.dumps(payload)})")
        except Exception:
            traceback.print_exc()

    # --- queue ---

    def get_queue(self) -> List[Dict[str, Any]]:
        return self._mgr.all()

    def check_duplicate(self, url: str) -> Dict[str, Any]:
        """Called from the Add URL dialog before submitting. Tells the UI
        if this URL matches anything already in the queue OR history, so
        it can prompt with Open / Show / Add-anyway options instead of
        silently skipping or overwriting.

        Returns the MOST RECENT match (highest queue id, or latest history
        row) along with a `count` of all copies — so someone with four
        `.mp4 / (1) / (2) / (3)` versions sees "you have 4 copies, latest
        is `(3).mp4`" rather than the details of the oldest one."""
        vid = _extract_video_id(url or "")

        # Live queue matches — collect all, then pick highest id.
        queue_hits: List[Dict[str, Any]] = []
        for it in self._mgr.all():
            it_vid = _extract_video_id(it.get("url", ""))
            if (vid and it_vid and vid == it_vid) or it.get("url") == url:
                queue_hits.append(it)
        if queue_hits:
            latest = max(queue_hits, key=lambda i: int(i.get("id", 0)))
            return {
                "where":   "queue",
                "id":      latest.get("id"),
                "title":   latest.get("title") or "?",
                # file is the actual on-disk name (may include "(1)"
                # from a prior re-download); shown in the prompt so
                # users can tell which duplicate copy is which.
                "file":    latest.get("file") or "",
                "status":  latest.get("status"),
                "size":    latest.get("size"),
                "quality": latest.get("quality"),
                "url":     latest.get("url"),
                "count":   len(queue_hits),
            }

        # History: match by video id only (URLs stored may vary). Skip
        # entries whose file is no longer on disk — the user obviously
        # deleted it and wants to re-download; prompting would just be
        # noise. Also skip Failed entries, since a failed attempt isn't
        # a "duplicate" of anything.
        if vid:
            dl_folder = Path(self._settings.get("folder", str(Path.home() / "Downloads")))
            hist_hits: List[Dict[str, Any]] = []
            for h in self._history:
                if _extract_video_id(h.get("url", "")) != vid:
                    continue
                if (h.get("status") or "").lower() != "done":
                    continue
                if not self._downloaded_file_exists(h, dl_folder):
                    continue
                hist_hits.append(h)
            if hist_hits:
                # History is chronological (append-only), so last = most recent.
                latest_h = hist_hits[-1]
                return {
                    "where":   "history",
                    "title":   latest_h.get("title") or "?",
                    "file":    Path(latest_h["output_path"]).name if latest_h.get("output_path") else "",
                    "status":  latest_h.get("status"),
                    "size":    latest_h.get("size"),
                    "quality": latest_h.get("quality"),
                    "date":    latest_h.get("date"),
                    "url":     latest_h.get("url"),
                    "count":   len(hist_hits),
                }
        return {}

    @staticmethod
    def _downloaded_file_exists(hist_entry: Dict[str, Any], dl_folder: Path) -> bool:
        """True if this history entry's downloaded file is still on disk.
        Prefers the stored `output_path`; falls back to scanning `dl_folder`
        (and its immediate subfolders — playlists live one level deep) for
        a file whose stem matches the sanitized title. Older history rows
        predate the `output_path` field, so the scan keeps them working."""
        path = hist_entry.get("output_path")
        if path and Path(path).exists():
            return True
        title = (hist_entry.get("title") or "").strip()
        if not title or not dl_folder.exists():
            return False
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip().rstrip(".")
        if not safe:
            return False
        # Search root + one level of subfolders (playlist folders).
        for parent in (dl_folder, *[p for p in dl_folder.iterdir() if p.is_dir()]):
            try:
                if any(parent.glob(f"{safe}.*")) or any(parent.glob(f"{safe} (*).*")):
                    return True
            except OSError:
                continue
        return False

    def add_url(self, url: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        options = options or {}
        id_ = self._mgr.add(
            url,
            format_id=options.get("format_id"),
            audio=bool(options.get("audio")),
            bitrate=options.get("bitrate") or self._settings.get("mp3_bitrate", "192"),
            playlist_folder=options.get("playlist_folder") or "",
            container=options.get("container") or "",
            force=bool(options.get("force")),
            subs=bool(options.get("subs")),
        )
        return {"id": id_}

    def add_batch(self, urls: List[str], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        options = options or {}
        return {"ids": self._mgr.add_batch(
            urls,
            format_id=options.get("format_id"),
            audio=bool(options.get("audio")),
            bitrate=options.get("bitrate") or self._settings.get("mp3_bitrate", "192"),
            playlist_folder=options.get("playlist_folder") or "",
            container=options.get("container") or "",
            force=bool(options.get("force")),
            subs=bool(options.get("subs")),
        )}

    def get_playlist_entries(self, url: str) -> Dict[str, Any]:
        """List the videos in a playlist without downloading anything.

        Uses `extract_flat="in_playlist"` so each entry only gets the
        cheap fields (id, title, duration, uploader, thumbnails) —
        important because a large playlist can otherwise take minutes
        to enumerate. Returns entries the UI can render as a checklist.
        """
        url = url.strip()
        if not url:
            return {"error": "empty url"}
        try:
            with yt_dlp.YoutubeDL({
                **self._mgr._ydl_opts(),
                "extract_flat": "in_playlist",
            }) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:
            return {"error": str(exc)[:400]}
        if not info:
            return {"error": "no data from yt-dlp"}
        raw_entries = info.get("entries") or []
        entries: List[Dict[str, Any]] = []
        total_secs = 0
        for e in raw_entries:
            if not e:
                continue
            vid_id = e.get("id") or ""
            vid_url = (e.get("url") or e.get("webpage_url")
                       or (f"https://www.youtube.com/watch?v={vid_id}" if vid_id else ""))
            if not vid_url:
                continue
            dur = e.get("duration")
            if dur:
                total_secs += int(dur)
            thumbs = e.get("thumbnails") or []
            thumb = ""
            if thumbs:
                # Pick a small one — playlist checklist is a compact view.
                small = [t for t in thumbs if t.get("url") and (t.get("width") or 0) <= 320]
                thumb = (small[-1] if small else thumbs[-1]).get("url", "")
            entries.append({
                "url": vid_url,
                "title": e.get("title") or "?",
                "dur": _fmt_duration(dur),
                "uploader": e.get("uploader") or "",
                "thumbnail": thumb,
            })
        return {
            "title": info.get("title") or "Playlist",
            "count": len(entries),
            "total_duration": _fmt_duration(total_secs) if total_secs else "—",
            "entries": entries,
        }

    def get_formats(self, url: str) -> Dict[str, Any]:
        """Return the list of formats yt-dlp actually finds for `url`, with
        estimated file sizes ready for display in the Add URL dialog.

        Groups by (height, ext), keeps the highest-bitrate representative
        of each group, and includes an audio-only entry plus a "Best
        available" default at the top. Video-only streams get audio size
        added since we'll be muxing them with the best audio track.
        """
        url = url.strip()
        if not url:
            return {"error": "empty url"}
        try:
            info = self._mgr._extract_with_fallback(url)
        except Exception as exc:
            return {"error": str(exc)[:400]}

        if info and "entries" in info:
            # Playlist — we can't sensibly pick per-video formats yet.
            entries = [e for e in (info.get("entries") or []) if e]
            return {
                "playlist": True,
                "title": info.get("title") or "Playlist",
                "count": len(entries),
                "formats": [{"format_id": "best", "label": "Best available", "size_str": "—", "height": 9999}],
            }

        formats = (info or {}).get("formats") or []

        def _known_bytes(f: Dict[str, Any]) -> int:
            """Only return a size when yt-dlp actually reports one. A
            tbr*duration estimate looked tempting but overshoots badly on
            VBR MP4 (peak vs average bitrate) — showing 589 MB for a file
            that lands at 176 MB is worse than showing nothing, because
            users abort the download thinking it's too big."""
            return int(f.get("filesize") or f.get("filesize_approx") or 0)

        # Best audio track (used both as a standalone option and as the
        # audio companion for muxing video-only streams).
        audio_only = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")]
        best_audio = max(audio_only, key=lambda f: f.get("abr") or 0, default=None)
        audio_size = _known_bytes(best_audio) if best_audio else 0

        # Any format that has video: progressive (has audio too) or
        # adaptive video-only (we'll mux).
        video = [f for f in formats if f.get("vcodec") not in (None, "none") and f.get("height")]

        # Keep the highest-bitrate representative per (height, ext).
        best_by_group: Dict[tuple, Dict[str, Any]] = {}
        for f in video:
            key = (f.get("height"), (f.get("ext") or "mp4").lower())
            existing = best_by_group.get(key)
            if not existing or (f.get("tbr") or 0) > (existing.get("tbr") or 0):
                best_by_group[key] = f

        out: List[Dict[str, Any]] = [
            # No container preference for Best; the backend defaults to mp4
            # via merge_output_format so the file is playable everywhere.
            {"format_id": "best", "label": "Best available",
             "height": 9999, "size_mb": None, "size_str": "—", "container": ""}
        ]
        for f in sorted(best_by_group.values(),
                        key=lambda x: (-(x.get("height") or 0), x.get("ext") or "")):
            h = f["height"]
            ext = (f.get("ext") or "mp4").lower()
            vs = _known_bytes(f)
            needs_mux = f.get("acodec") in (None, "none")
            # Only quote a total when we know the video part's real size.
            # If vs is 0 (nsig-protected MP4 with no reported filesize),
            # leave size blank rather than mislead.
            total = (vs + audio_size) if (vs and needs_mux) else vs
            out.append({
                "format_id": f["format_id"] + ("+bestaudio" if needs_mux else ""),
                "label": f"{h}p {ext.upper()}",
                "height": h,
                "size_mb": int(total / 1_048_576) if total else None,
                "size_str": _fmt_bytes(total) if total else "—",
                # Target container — tells the download to remux into this
                # extension so the output file matches the label the user saw.
                "container": ext,
            })

        if best_audio:
            audio_ext = (best_audio.get("ext") or "m4a").lower()
            out.append({
                "format_id": best_audio["format_id"],
                "label": f"Audio only ({audio_ext})",
                "height": 0,
                "size_mb": int(audio_size / 1_048_576) if audio_size else None,
                "size_str": _fmt_bytes(audio_size) if audio_size else "—",
                "container": audio_ext,
            })

        top_height = max((f.get("height") or 0) for f in out) if out else 0
        low_quality_only = top_height and top_height <= 360
        meta = info.get("_extraction_meta", {}) if info else {}
        note: Optional[str] = None
        if low_quality_only and not _detect_js_runtime():
            # Most common cause of "only low-res available" as of 2026 is a
            # missing JS runtime — YouTube's nsig deobfuscation needs one.
            # The app ships QuickJS in bin/, so this only fires if it's been
            # deleted or blocked (e.g. antivirus quarantined qjs.exe).
            note = (
                "Only low-quality formats are available because no JavaScript "
                "runtime is installed. The app ships QuickJS in its `bin/` "
                "folder — check that `qjs.exe` is still there and not blocked "
                "by antivirus, or install Node.js from nodejs.org."
            )
        elif low_quality_only:
            browser = self._mgr._settings.get("cookies_browser", "none")
            has_cookies_file = bool((self._mgr._settings.get("cookies_file") or "").strip())
            if meta.get("cookies_locked") and not has_cookies_file:
                note = (
                    f"Only 360p is available because your {browser.title()} "
                    f"cookies are locked (the browser is open). Close "
                    f"{browser.title()}, or set a Cookies file in Settings → "
                    f"Advanced to keep the browser open."
                )
            elif meta.get("cookies_configured"):
                note = (
                    "Only 360p is available even with cookies — this video is "
                    "age-restricted or region-locked and requires a signed-in session."
                )
            else:
                note = (
                    "Only 360p is available. Set a Cookies file (exported from a "
                    "browser extension) or pick Cookies from browser in "
                    "Settings → Advanced to unlock full quality."
                )

        # Format view count with thousands separator; the UI shows this
        # in the info card next to duration.
        views = info.get("view_count") if info else None
        return {
            "playlist": False,
            "title":     info.get("title") if info else url,
            "uploader":  info.get("uploader") if info else None,
            "duration":  _fmt_duration(info.get("duration") if info else None),
            "thumbnail": self._mgr._pick_thumbnail(info) if info else "",
            "views":     f"{int(views):,}" if isinstance(views, (int, float)) else None,
            "formats":   out,
            "note":      note,
        }

    def remove(self, id_: int) -> bool:
        self._mgr.remove(int(id_)); return True

    def pause(self, id_: int) -> bool:
        self._mgr.pause(int(id_)); return True

    def resume(self, id_: int) -> bool:
        self._mgr.resume(int(id_)); return True

    def stop(self, id_: int) -> bool:
        self._mgr.stop(int(id_)); return True

    def retry(self, id_: int) -> bool:
        self._mgr.retry(int(id_)); return True

    def start_all(self) -> bool:
        self._mgr.start_all(); return True

    def open_folder(self, id_: Optional[int] = None) -> bool:
        self._mgr.open_folder(int(id_) if id_ else 0); return True

    def open_file(self, id_: int) -> bool:
        return self._mgr.open_file(int(id_))

    def get_log(self, id_: int) -> List[List[str]]:
        return self._mgr.get_log(int(id_))

    # --- settings ---

    def get_settings(self) -> Dict[str, Any]:
        return {**self._settings, "config_path": str(SETTINGS_FILE)}

    def save_settings(self, patch: Dict[str, Any]) -> bool:
        # Merge and persist. Only whitelisted keys are accepted so a
        # malformed patch can't add arbitrary top-level keys.
        for k in DEFAULT_SETTINGS:
            if k in patch:
                self._settings[k] = patch[k]
        _save_json(SETTINGS_FILE, self._settings)
        return True

    def reset_settings(self) -> Dict[str, Any]:
        self._settings.update(DEFAULT_SETTINGS)
        _save_json(SETTINGS_FILE, self._settings)
        return self.get_settings()

    def browse_folder(self) -> str:
        # pywebview supports native folder picker
        if not self._window:
            return self._settings.get("folder", "")
        try:
            import webview
            result = self._window.create_file_dialog(webview.FOLDER_DIALOG)
            if result:
                return result[0]
        except Exception:
            pass
        return self._settings.get("folder", "")

    def default_browser(self) -> str:
        """Best-effort guess at the user's default browser on Windows.
        Returns a lowercase name matching yt-dlp's cookies vocabulary
        (chrome / edge / firefox / brave / opera / vivaldi) or "" if unknown.
        """
        if sys.platform != "win32":
            return ""
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice") as k:
                prog, _ = winreg.QueryValueEx(k, "ProgId")
            prog = str(prog).lower()
            for tag in ("chrome", "edge", "firefox", "brave", "opera", "vivaldi"):
                if tag in prog:
                    return tag
        except OSError:
            pass
        return ""

    def find_cookies_txt(self) -> List[str]:
        """Scan the user's Downloads folder for likely cookies.txt files.
        Sorted newest-first so the most-recent export bubbles up."""
        results: List[str] = []
        candidates = [Path.home() / "Downloads", Path.home() / "Desktop"]
        for d in candidates:
            if not d.exists():
                continue
            try:
                for p in d.iterdir():
                    if not p.is_file():
                        continue
                    name = p.name.lower()
                    if name.endswith(".txt") and ("cookie" in name or "youtube" in name):
                        results.append(str(p))
            except OSError:
                continue
        results.sort(key=lambda s: Path(s).stat().st_mtime, reverse=True)
        return results

    def browse_cookies_file(self) -> str:
        """Open a native file picker for the user to select a cookies.txt."""
        if not self._window:
            return self._settings.get("cookies_file", "")
        try:
            import webview
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=("Cookies file (*.txt)", "All files (*.*)"),
            )
            if result:
                return result[0]
        except Exception:
            traceback.print_exc()
        return self._settings.get("cookies_file", "")

    # --- analytics + history ---

    def get_analytics(self) -> Dict[str, Any]:
        """Build the analytics payload live from self._history."""
        history = self._history
        # Per-day counts for the last 30 days.
        today = datetime.now().date()
        per_day: List[List[int]] = []
        for i in range(29, -1, -1):
            day = today - timedelta(days=i)
            iso = day.isoformat()
            ok = sum(1 for h in history if h.get("date") == iso and h.get("status") == "Done")
            bad = sum(1 for h in history if h.get("date") == iso and h.get("status") == "Failed")
            per_day.append([ok, bad])

        total      = len(history)
        successful = sum(1 for h in history if h.get("status") == "Done")
        failed     = sum(1 for h in history if h.get("status") == "Failed")
        total_mb   = sum(int(h.get("mb", 0) or 0) for h in history if h.get("status") == "Done")

        since_date = min((h.get("date") for h in history if h.get("date")), default=None)
        since = (
            datetime.strptime(since_date, "%Y-%m-%d").strftime("%d %b %Y")
            if since_date else datetime.now().strftime("%d %b %Y")
        )
        stats = {
            "total":       total,
            "successful":  successful,
            "failed":      failed,
            "dataGB":      round(total_mb / 1024, 2),
            "since":       since,
            "failedNote":  (f"{failed} failed download{'s' if failed != 1 else ''}"
                            if failed else "no failures yet"),
        }
        # Recent activity as [time, title, status, size]; newest first.
        display_hist = [
            [h.get("time", ""), h.get("title", ""), h.get("status", ""), h.get("size", "—")]
            for h in history[-8:][::-1]
        ]
        return {"stats": stats, "perDay": per_day, "history": display_hist}

    def get_history_page(self, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Paginated + filtered slice of history. Powers the searchable
        history table in Analytics. Filters:
          q     -- case-insensitive match against title / url / uploader
          from  -- ISO date "YYYY-MM-DD", inclusive lower bound
          to    -- ISO date "YYYY-MM-DD", inclusive upper bound
          status -- "Done" / "Failed" / "" for all
          page      -- 1-based
          page_size -- default 15
        """
        options = options or {}
        q         = (options.get("q") or "").strip().lower()
        dfrom     = (options.get("from") or "").strip()
        dto       = (options.get("to") or "").strip()
        status_f  = (options.get("status") or "").strip()
        page      = max(1, int(options.get("page") or 1))
        page_size = max(1, min(200, int(options.get("page_size") or 15)))

        # Filter first, then reverse-chronological, then paginate.
        rows = []
        for h in self._history:
            if status_f and h.get("status") != status_f:
                continue
            d = h.get("date") or ""
            if dfrom and d < dfrom: continue
            if dto   and d > dto:   continue
            if q:
                hay = " ".join([
                    str(h.get("title") or ""),
                    str(h.get("url") or ""),
                    str(h.get("uploader") or ""),
                ]).lower()
                if q not in hay: continue
            rows.append(h)
        # Newest first for the UI.
        rows.reverse()
        total = len(rows)
        start = (page - 1) * page_size
        end   = start + page_size

        def _display_title(h: Dict[str, Any]) -> str:
            """Prefer the actual on-disk filename stem so re-downloaded
            copies show as `Title (1)`, `Title (2)` etc. instead of every
            row displaying the identical bare title. Falls back to the
            plain title for old history entries that predate `output_path`."""
            out = h.get("output_path") or ""
            if out:
                stem = Path(out).stem
                if stem:
                    return stem
            return h.get("title") or ""

        page_rows = [
            {
                "date":   h.get("date", ""),
                "time":   h.get("time", ""),
                "title":  _display_title(h),
                "url":    h.get("url", ""),
                "status": h.get("status", ""),
                "size":   h.get("size", "—"),
                "quality": h.get("quality", ""),
            }
            for h in rows[start:end]
        ]
        return {
            "rows":      page_rows,
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "pages":     max(1, (total + page_size - 1) // page_size),
        }

    def clear_history(self) -> bool:
        self._history = []
        self._save_history()
        return True

    def export_history_csv(self) -> Optional[str]:
        try:
            import webview
            path = self._window.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=f"youtube-downloader-history-{datetime.now().strftime('%Y%m%d')}.csv",
            )
            if not path:
                return None
            target = path if isinstance(path, str) else path[0]
            with open(target, "w", encoding="utf-8", newline="") as f:
                f.write("date,time,title,status,size,quality,url\n")
                for h in self._history:
                    row = [h.get("date", ""), h.get("time", ""), h.get("title", ""),
                           h.get("status", ""), h.get("size", ""), h.get("quality", ""),
                           h.get("url", "")]
                    f.write(",".join(f'"{c.replace(chr(34), chr(34)*2)}"' for c in row) + "\n")
            return target
        except Exception:
            traceback.print_exc()
            return None

    # --- misc ---

    def app_version(self) -> str:
        return APP_VERSION

    def ytdlp_version(self) -> str:
        try:
            return yt_dlp.version.__version__
        except Exception:
            return "?"

    def ytdlp_check_update(self) -> Dict[str, Any]:
        """Query PyPI for the latest yt-dlp release. Only checks — doesn't
        download anything. Returns current + latest + a boolean flag.

        Includes pre-releases (nightlies). YouTube ships breaking changes
        on ~monthly cadence and yt-dlp fixes them in nightlies days before
        the next stable — locking to stable means "Up to date" lies for
        days at a time when things are actively broken."""
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://pypi.org/pypi/yt-dlp/json",
                headers={"User-Agent": "YouTubeDownloaderPro/1.0"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
        except Exception as exc:
            return {"error": str(exc)[:200]}
        # info.version is stable-only; releases dict has every version
        # ever published, including pre-releases. Pick the highest.
        releases = list((data.get("releases") or {}).keys())
        latest = max(releases, key=self._version_tuple, default="") if releases else ""
        current = self.ytdlp_version()
        return {
            "current": current,
            "latest": latest,
            "is_prerelease": bool(latest and "dev" in latest.lower()),
            "update_available": self._version_is_newer(latest, current),
        }

    def ytdlp_update(self) -> Dict[str, Any]:
        """Actually run `pip install -U --pre yt-dlp` in the current Python.
        `--pre` lets us grab nightlies when YouTube has broken the current
        stable release. Requires an app restart to load the new module."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-U", "--pre", "yt-dlp"],
                capture_output=True, text=True, timeout=180,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode != 0:
                return {"ok": False, "error": (result.stderr or result.stdout)[-400:]}
            self._settings["ytdlp_last_check"] = datetime.now().isoformat()
            _save_json(SETTINGS_FILE, self._settings)
            return {"ok": True, "restart_needed": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:200]}

    @staticmethod
    def _version_tuple(v: str) -> tuple:
        """CalVer-friendly version parser. Drops non-numeric segments like
        `dev0` so nightlies compare cleanly against stables:
            2026.7.4                 -> (2026, 7, 4)
            2026.7.23.234303.dev0    -> (2026, 7, 23, 234303)
        Longer tuples with equal prefixes sort higher, which is what we want."""
        try:
            return tuple(int(p) for p in re.split(r"[.\-]", v or "") if p.isdigit())
        except Exception:
            return ()

    @classmethod
    def _version_is_newer(cls, latest: str, current: str) -> bool:
        l, c = cls._version_tuple(latest), cls._version_tuple(current)
        return bool(l and c and l > c)

    _YT_URL_RE = re.compile(
        r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com/(?:watch\?[^\s]*v=|playlist\?[^\s]*list=|shorts/|live/)|youtu\.be/)[\w\-?=&/]+",
        re.IGNORECASE,
    )

    def check_clipboard_url(self) -> Dict[str, str]:
        """If the OS clipboard contains a YouTube URL, return it. Empty
        dict otherwise. Used by the UI to offer one-click add when the
        user pastes a link into their browser and then focuses the app.

        Uses PowerShell's Get-Clipboard so we don't need a third-party
        package. Only reads text; safely ignores binary clipboard content.
        """
        if sys.platform != "win32":
            return {}
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                capture_output=True, text=True, timeout=2,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            return {}
        text = (result.stdout or "").strip()
        if not text or len(text) > 2000:
            return {}
        match = self._YT_URL_RE.search(text)
        if not match:
            return {}
        return {"url": match.group(0)}

    def minimize(self) -> bool:
        if self._window:
            self._window.minimize()
        return True

    def maximize(self) -> bool:
        # Toggle: if we've already maximized, restore back to windowed.
        if not self._window:
            return True
        try:
            if self._maximized:
                self._window.restore()
                self._maximized = False
            else:
                self._window.maximize()
                self._maximized = True
        except Exception:
            traceback.print_exc()
        return True

    def quit_app(self) -> bool:
        if self._window:
            self._window.destroy()
        return True
