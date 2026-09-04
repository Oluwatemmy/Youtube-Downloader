"""On-disk yt-dlp override — lets the packaged app update yt-dlp without pip.

The installable build is a PyInstaller bundle: there is no pip inside it,
and the bundled yt-dlp lives in the frozen archive. Shelling out to
`sys.executable -m pip` from there just launches a second copy of the app
(that's what the v1.0.0 updater did).

Instead we download the pure-Python wheel straight from PyPI, verify its
SHA-256 against the digest PyPI reports, unpack it into

    %APPDATA%\\YouTubeDownloader\\ytdlp\\<version>\\

and record it in `active.json`. At startup `activate()` puts that folder at
the front of `sys.path` so it shadows the bundled copy. PyInstaller 6
resolves imports through `sys.path` (its frozen finder is a path hook), so
a plain insert is enough — and the same mechanism works in dev mode.

yt-dlp pins `yt-dlp-ejs` (its JS-challenge solver) to an exact version. When
a release moves that pin, the matching yt-dlp-ejs wheel is unpacked into the
same folder so the two stay in step.

The override retires itself: if the app is rebuilt with a yt-dlp that is
equal to or newer than the override, `activate()` deletes the override.

IMPORTANT: nothing in this module may import yt_dlp. `activate()` has to run
before the first `import yt_dlp` anywhere in the process.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

DIST = "yt-dlp"
PACKAGE = "yt_dlp"
COMPANION = "yt-dlp-ejs"
ACTIVE_FILE = "active.json"
USER_AGENT = "YouTManager/1.0 (+https://github.com/Oluwatemmy/Youtube-Downloader)"
HTTP_TIMEOUT = 30


class UpdateError(Exception):
    """A user-presentable reason the update could not be installed."""


# ---------------------------------------------------------------
# paths
# ---------------------------------------------------------------

def config_dir() -> Path:
    """%APPDATA%\\YouTubeDownloader (or ~/.config/YouTubeDownloader)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        base = Path.home() / ".config"
    d = base / "YouTubeDownloader"
    d.mkdir(parents=True, exist_ok=True)
    return d


def override_root() -> Path:
    return config_dir() / "ytdlp"


# ---------------------------------------------------------------
# versions
# ---------------------------------------------------------------

def version_tuple(v: Optional[str]) -> tuple:
    """CalVer-friendly parser. Drops non-numeric segments (`dev0`) so
    nightlies compare cleanly against stables:
        2026.7.4              -> (2026, 7, 4)
        2026.07.14            -> (2026, 7, 14)
        2026.7.23.234303.dev0 -> (2026, 7, 23, 234303)"""
    try:
        return tuple(int(p) for p in re.split(r"[.\-]", v or "") if p.isdigit())
    except Exception:
        return ()


def is_newer(candidate: Optional[str], current: Optional[str]) -> bool:
    a, b = version_tuple(candidate), version_tuple(current)
    return bool(a and b and a > b)


def installed_version(name: str) -> str:
    """Version of `name` as shipped with the app (bundle or venv), ignoring
    any override folder that may already be on sys.path."""
    root = str(override_root())
    paths = [p for p in sys.path if not str(p).startswith(root)]
    try:
        for dist in importlib.metadata.Distribution.discover(name=name, path=paths):
            return dist.version
    except Exception:
        pass
    return ""


def base_version() -> str:
    return installed_version(DIST)


# ---------------------------------------------------------------
# activation (startup)
# ---------------------------------------------------------------

_active: Optional[str] = None


def read_active() -> Optional[Dict[str, Any]]:
    """The manifest for the currently installed override, or None if there
    is none / it's unreadable / its folder is missing."""
    path = override_root() / ACTIVE_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    version, dir_name = data.get("version"), data.get("dir")
    if not version or not dir_name:
        return None
    if not (override_root() / dir_name / PACKAGE / "__init__.py").exists():
        return None
    return data


def activate() -> Optional[str]:
    """Put a newer-than-bundled override at the front of sys.path.
    Returns the override version, or None when nothing was activated.
    Must run before the first `import yt_dlp`."""
    global _active
    manifest = read_active()
    if not manifest:
        return None
    if not is_newer(manifest["version"], base_version()):
        # App now ships something at least as new — the override is dead
        # weight and would only hide future bundled fixes.
        discard()
        return None
    path = str(override_root() / manifest["dir"])
    if path in sys.path:
        sys.path.remove(path)
    sys.path.insert(0, path)
    _active = str(manifest["version"])
    return _active


def active_version() -> Optional[str]:
    return _active


def discard() -> None:
    """Remove the override folder entirely (best effort)."""
    global _active
    root = override_root()
    try:
        (root / ACTIVE_FILE).unlink()
    except OSError:
        pass
    if root.exists():
        for child in root.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
    _active = None


# ---------------------------------------------------------------
# PyPI access (module-level so tests can swap them out)
# ---------------------------------------------------------------

def pypi_url(name: str, version: Optional[str] = None) -> str:
    if version:
        return f"https://pypi.org/pypi/{name}/{version}/json"
    return f"https://pypi.org/pypi/{name}/json"


def _http_json(url: str) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read()


def latest_stable() -> str:
    """PyPI's `info.version` is the latest non-prerelease upload."""
    data = _http_json(pypi_url(DIST))
    return str((data.get("info") or {}).get("version") or "")


def pick_wheel(payload: Dict[str, Any]) -> Dict[str, Any]:
    for entry in payload.get("urls") or []:
        if entry.get("packagetype") == "bdist_wheel" and str(entry.get("filename", "")).endswith("py3-none-any.whl"):
            return entry
    name = (payload.get("info") or {}).get("name", "package")
    raise UpdateError(f"no pure-Python wheel published for {name}")


_COMPANION_RE = re.compile(
    r"^\s*yt-dlp-ejs\s*==\s*([0-9A-Za-z.]+)\s*;(.*)$", re.IGNORECASE)


def companion_pin(requires_dist: List[str]) -> Optional[str]:
    """The exact yt-dlp-ejs version this yt-dlp release wants (from its
    `default` extra). None if the metadata doesn't pin one."""
    for req in requires_dist or []:
        m = _COMPANION_RE.match(req)
        if m and 'extra == "default"' in m.group(2):
            return m.group(1)
    return None


def python_satisfies(spec: Optional[str]) -> bool:
    """Minimal PEP 440 specifier check against the running interpreter.
    Only the operators yt-dlp actually uses (>=, >, <=, <, ==, !=)."""
    if not spec:
        return True
    current = tuple(sys.version_info[:3])
    for clause in spec.split(","):
        clause = clause.strip()
        m = re.match(r"^(>=|<=|==|!=|>|<)\s*([0-9.]+)$", clause)
        if not m:
            continue
        op, want = m.group(1), version_tuple(m.group(2))
        ok = {
            ">=": current >= want, ">": current > want,
            "<=": current <= want, "<": current < want,
            "==": current[:len(want)] == want,
            "!=": current[:len(want)] != want,
        }[op]
        if not ok:
            return False
    return True


# ---------------------------------------------------------------
# install
# ---------------------------------------------------------------

def _safe_extract(blob: bytes, dest: Path) -> None:
    """Unzip a wheel into `dest`, refusing anything that would escape it."""
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        members = zf.infolist()
        for info in members:
            name = info.filename
            p = PurePosixPath(name)
            if (name.startswith(("/", "\\")) or "\\" in name or p.is_absolute()
                    or ".." in p.parts or re.match(r"^[A-Za-z]:", name)):
                raise UpdateError(f"unsafe path in wheel: {name}")
        for info in members:
            if info.is_dir():
                continue
            target = dest / PurePosixPath(info.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def _retire(path: Path) -> None:
    """Get an existing folder out of the way. Delete if we can; if Windows
    holds something open, rename it aside and let cleanup catch it later."""
    shutil.rmtree(path, ignore_errors=True)
    if not path.exists():
        return
    aside = path.with_name(f".old-{path.name}-{int(time.time())}")
    try:
        os.replace(path, aside)
    except OSError as exc:
        raise UpdateError(f"could not replace existing folder {path.name}: {exc}") from exc


def install_update(version: Optional[str] = None) -> Dict[str, Any]:
    """Download yt-dlp `version` (default: latest stable) into the override
    folder and mark it active. Raises UpdateError with a readable message.
    The new code only takes effect after the app restarts."""
    payload = _http_json(pypi_url(DIST, version))
    info = payload.get("info") or {}
    target = str(info.get("version") or version or "")
    if not target:
        raise UpdateError("PyPI did not report a version")

    requires_python = info.get("requires_python")
    if not python_satisfies(requires_python):
        running = ".".join(str(n) for n in sys.version_info[:3])
        raise UpdateError(
            f"yt-dlp {target} needs Python {requires_python}; this build runs "
            f"Python {running}. A new app release is needed for that update.")

    wheels = [pick_wheel(payload)]
    companion: Optional[str] = None
    pin = companion_pin(info.get("requires_dist") or [])
    if pin and pin != installed_version(COMPANION):
        wheels.append(pick_wheel(_http_json(pypi_url(COMPANION, pin))))
        companion = pin

    root = override_root()
    root.mkdir(parents=True, exist_ok=True)
    staging = root / f".staging-{target}"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    try:
        for wheel in wheels:
            blob = _http_bytes(wheel["url"])
            expected = str((wheel.get("digests") or {}).get("sha256", "")).lower()
            actual = hashlib.sha256(blob).hexdigest()
            if not expected or actual != expected:
                raise UpdateError(f"checksum mismatch for {wheel.get('filename')} — download aborted")
            _safe_extract(blob, staging)
        if not (staging / PACKAGE / "__init__.py").exists():
            raise UpdateError("downloaded wheel did not contain the yt_dlp package")
        dest = root / target
        if dest.exists():
            _retire(dest)
        os.replace(staging, dest)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    manifest = {
        "version": target,
        "dir": dest.name,
        "companion": companion,
        "installed": datetime.now().isoformat(timespec="seconds"),
        "wheels": [w.get("filename") for w in wheels],
    }
    tmp = root / (ACTIVE_FILE + ".tmp")
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    os.replace(tmp, root / ACTIVE_FILE)

    # Sweep older override folders (and anything _retire renamed aside).
    for child in root.iterdir():
        if child.is_dir() and child.name != dest.name:
            shutil.rmtree(child, ignore_errors=True)

    return {"ok": True, "version": target, "restart_needed": True}
