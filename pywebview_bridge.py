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

        # Restore any queue that was persisted from the previous session.
        # Anything that had been Downloading gets flipped to Paused since
        # we can't actually resume mid-stream after a restart.
        self._load()

    # ---- public API ----

    def all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(i) for i in self._items]

    def add(self, url: str, format_id: Optional[str] = None) -> int:
        url = url.strip()
        if not url:
            raise ValueError("empty url")
        with self._lock:
            if self._settings.get("dupes") and any(i["url"] == url for i in self._items):
                return -1
            item = self._new_item(url)
            item["format_id"] = format_id  # explicit format override, or None to use settings
            self._items.append(item)
        self._emit_queue()
        self._persist()
        # Kick off metadata + download in one background task
        self._futures[item["id"]] = self._pool.submit(self._run, item["id"])
        return item["id"]

    def add_batch(self, urls: List[str], format_id: Optional[str] = None) -> List[int]:
        return [self.add(u, format_id=format_id) for u in urls if u.strip()]

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
            # Delete the completed output file if the download finished.
            out = captured.get("output_path")
            if out:
                try:
                    Path(out).unlink()
                except OSError:
                    pass
            # Delete any partials from an incomplete / interrupted download.
            title = (captured.get("title") or "").strip()
            if title:
                download_dir = Path(self._settings.get("folder", str(Path.home() / "Downloads")))
                stem = title.replace(":", "-").replace("/", "-").replace("?", "")[:120]
                for pattern in (f"{stem}*.part*", f"{stem}*.ytdl", f"{stem}.*"):
                    for p in download_dir.glob(pattern):
                        # Guard against deleting an unrelated file that only
                        # shares the stem — only delete files clearly derived
                        # from this download.
                        if p.suffix.lower() in (".mp4", ".mkv", ".webm", ".m4a",
                                                ".mp3", ".part", ".ytdl", ".description"):
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
        """Continue a paused download from the existing .part file."""
        with self._lock:
            it = self._find(id_)
            if not it:
                return
            it["status"] = "Queued"
        self._cancelled.discard(id_)
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

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)

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
        if status in ("Done", "Failed"):
            # A download resolved — persist so restart doesn't lose it,
            # and let the bridge log it to history.
            self._persist()
            try:
                self._on_finished(snap)
            except Exception:
                traceback.print_exc()

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

    # Player-client fallback chain. tv_embedded is preferred because it
    # surfaces the full 144p–2160p ladder including video-only streams;
    # android is the last resort because it bypasses YouTube's bot check
    # but only returns up to 360p. See the diagnostics from 2026-07-29.
    _CLIENT_CHAIN = (["tv_embedded"], ["android"])

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
            "extractor_args": {
                "youtube": {"player_client": player_client or self._CLIENT_CHAIN[0]},
            },
        }
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

            # --- fetch metadata (best-effort) ---
            # Track which (client, use_cookies) combo actually worked so
            # the download step below reuses the exact same auth.
            info = None
            chosen_client: Optional[List[str]] = None
            chosen_use_cookies = True
            cookies_configured = bool(self._settings.get("cookies_browser") and
                                      self._settings["cookies_browser"] != "none")
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
                self._update(
                    id_,
                    title=info.get("title") or url,
                    file=(info.get("title") or url) + "." + (info.get("ext") or "mp4"),
                    uploader=info.get("uploader") or "—",
                    dur=_fmt_duration(info.get("duration")),
                    quality=self._quality_label(info),
                    size=_fmt_bytes(info.get("filesize") or info.get("filesize_approx")),
                    mb=int((info.get("filesize") or info.get("filesize_approx") or 0) / 1_048_576),
                    thumbnail=self._pick_thumbnail(info),
                )

            if id_ in self._cancelled:
                self._update(id_, status="Paused")
                return

            # --- download ---
            download_dir = Path(self._settings.get("folder", str(Path.home() / "Downloads")))
            download_dir.mkdir(parents=True, exist_ok=True)
            outtmpl = str(download_dir / "%(title)s.%(ext)s")

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
                if id_ in self._cancelled:
                    raise yt_dlp.DownloadError("cancelled")
                status = d.get("status")
                if status == "downloading":
                    downloaded = d.get("downloaded_bytes") or 0
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    pct = int(downloaded / total * 100) if total else 0
                    self._update(
                        id_,
                        pct=pct,
                        speed=_fmt_speed(d.get("speed")),
                        eta=_fmt_eta(d.get("eta")),
                        got=f"{_fmt_bytes(downloaded)} / {_fmt_bytes(total)}",
                        size=_fmt_bytes(total),
                    )
                elif status == "finished":
                    self._update(id_, pct=100, speed="—", eta="—",
                                 output_path=d.get("filename"))

            # Prefer the specific format_id chosen in the Add URL dialog;
            # fall back to the Settings quality preference otherwise.
            with self._lock:
                item_format = (self._find(id_) or {}).get("format_id")
            format_selector = item_format if item_format else self._format_selector()

            # Reuse the same (player_client, use_cookies) combo that
            # succeeded during metadata extraction — otherwise the download
            # can hit the bot check even though we just verified formats.
            # Per-run overrides: `fresh` runs disable resume so a stale
            # .part can't cause HTTP 416; pause→resume runs enable it so
            # the download picks up where it stopped.
            opts = self._ydl_opts({
                "outtmpl": outtmpl,
                "format": format_selector,
                "progress_hooks": [hook],
                "writesubtitles": bool(self._settings.get("desc")),
                "continuedl": not fresh,
                "overwrites": fresh,
            }, player_client=chosen_client, use_cookies=chosen_use_cookies)

            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])

            self._update(id_, status="Done", pct=100, speed="—", eta="—", error=None)

        except yt_dlp.DownloadError as exc:
            if id_ in self._cancelled:
                self._update(id_, status="Paused", speed="—", eta="—")
            else:
                self._update(id_, status="Failed", speed="—", eta="—",
                             error=str(exc)[:400])
        except Exception as exc:
            self._update(id_, status="Failed", speed="—", eta="—",
                         error=f"{type(exc).__name__}: {exc}"[:400])
            traceback.print_exc()

    def _format_selector(self) -> str:
        q = self._settings.get("quality", "1080p")
        m = {
            "best": "bestvideo+bestaudio/best",
            "2160p": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p":  "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p":  "bestvideo[height<=360]+bestaudio/best[height<=360]",
            "audio": "bestaudio/best",
        }
        return m.get(q, m["1080p"])

    def _quality_label(self, info: Dict[str, Any]) -> str:
        h = info.get("height")
        ext = info.get("ext") or "mp4"
        return f"{h}p {ext.upper()}" if h else ext.upper()

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
        Appends to history so analytics has real data."""
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
        }
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

    def add_url(self, url: str, format_id: Optional[str] = None) -> Dict[str, Any]:
        id_ = self._mgr.add(url, format_id=format_id)
        return {"id": id_}

    def add_batch(self, urls: List[str], format_id: Optional[str] = None) -> Dict[str, Any]:
        return {"ids": self._mgr.add_batch(urls, format_id=format_id)}

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
        # Best audio track (used both as a standalone option and as the
        # audio companion for muxing video-only streams).
        audio_only = [f for f in formats if f.get("vcodec") == "none" and f.get("acodec") not in (None, "none")]
        best_audio = max(audio_only, key=lambda f: f.get("abr") or 0, default=None)
        audio_size = 0
        if best_audio:
            audio_size = best_audio.get("filesize") or best_audio.get("filesize_approx") or 0

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
            {"format_id": "best", "label": "Best available",
             "height": 9999, "size_mb": None, "size_str": "—"}
        ]
        for f in sorted(best_by_group.values(),
                        key=lambda x: (-(x.get("height") or 0), x.get("ext") or "")):
            h = f["height"]
            ext = (f.get("ext") or "mp4").lower()
            vs = f.get("filesize") or f.get("filesize_approx") or 0
            needs_mux = f.get("acodec") in (None, "none")
            total = vs + (audio_size if needs_mux else 0)
            out.append({
                "format_id": f["format_id"] + ("+bestaudio" if needs_mux else ""),
                "label": f"{h}p {ext.upper()}" + ("" if not needs_mux else ""),
                "height": h,
                "size_mb": int(total / 1_048_576) if total else None,
                "size_str": _fmt_bytes(total) if total else "~ unknown",
            })

        if best_audio:
            out.append({
                "format_id": best_audio["format_id"],
                "label": f"Audio only ({(best_audio.get('ext') or 'm4a').lower()})",
                "height": 0,
                "size_mb": int(audio_size / 1_048_576) if audio_size else None,
                "size_str": _fmt_bytes(audio_size) if audio_size else "~ unknown",
            })

        top_height = max((f.get("height") or 0) for f in out) if out else 0
        low_quality_only = top_height and top_height <= 360
        meta = info.get("_extraction_meta", {}) if info else {}
        note: Optional[str] = None
        if low_quality_only:
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

        return {
            "playlist": False,
            "title": info.get("title") if info else url,
            "uploader": info.get("uploader") if info else None,
            "duration": _fmt_duration(info.get("duration") if info else None),
            "formats": out,
            "note": note,
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

    def ytdlp_version(self) -> str:
        try:
            return yt_dlp.version.__version__
        except Exception:
            return "?"

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
