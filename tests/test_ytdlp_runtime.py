"""Tests for app.ytdlp_runtime — the on-disk yt-dlp override that lets the
packaged (PyInstaller) app update yt-dlp without pip."""
import hashlib
import io
import json
import sys
import zipfile

import pytest

from app import ytdlp_runtime as rt


# ---------------------------------------------------------------
# helpers
# ---------------------------------------------------------------

def make_wheel(package: str, version: str, extra_files=None) -> bytes:
    """Build a minimal pure-Python wheel in memory with a `version.py`."""
    dist = package.replace("-", "_")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{dist}/__init__.py", "from .version import __version__\n")
        zf.writestr(f"{dist}/version.py", f"__version__ = {version!r}\n")
        zf.writestr(f"{dist}-{version}.dist-info/METADATA",
                    f"Metadata-Version: 2.1\nName: {package}\nVersion: {version}\n")
        for name, content in (extra_files or {}).items():
            zf.writestr(name, content)
    return buf.getvalue()


def pypi_payload(name: str, version: str, blob: bytes, requires_dist=None,
                 requires_python=">=3.10") -> dict:
    dist = name.replace("-", "_")
    return {
        "info": {
            "name": name,
            "version": version,
            "requires_python": requires_python,
            "requires_dist": requires_dist or [],
        },
        "urls": [
            {
                "packagetype": "sdist",
                "filename": f"{dist}-{version}.tar.gz",
                "url": f"https://files.example/{dist}-{version}.tar.gz",
                "digests": {"sha256": "0" * 64},
            },
            {
                "packagetype": "bdist_wheel",
                "filename": f"{dist}-{version}-py3-none-any.whl",
                "url": f"https://files.example/{dist}-{version}-py3-none-any.whl",
                "digests": {"sha256": hashlib.sha256(blob).hexdigest()},
            },
        ],
    }


@pytest.fixture
def override_root(tmp_path, monkeypatch):
    root = tmp_path / "ytdlp"
    monkeypatch.setattr(rt, "override_root", lambda: root)
    return root


@pytest.fixture
def isolated_imports(monkeypatch):
    """Snapshot sys.path / sys.modules so activate() tests can't leak a
    stub yt_dlp into other tests."""
    saved_path = list(sys.path)
    saved_mods = {k: v for k, v in sys.modules.items() if k.split(".")[0] in ("yt_dlp", "yt_dlp_ejs")}
    for k in list(saved_mods):
        del sys.modules[k]
    yield
    sys.path[:] = saved_path
    for k in list(sys.modules):
        if k.split(".")[0] in ("yt_dlp", "yt_dlp_ejs"):
            del sys.modules[k]
    sys.modules.update(saved_mods)


# ---------------------------------------------------------------
# version comparison
# ---------------------------------------------------------------

@pytest.mark.parametrize("newer,older", [
    ("2026.8.19", "2026.7.4"),
    ("2026.07.14", "2026.7.4"),        # zero-padded CalVer still compares numerically
    ("2026.7.4.1", "2026.7.4"),
    ("2027.1.1", "2026.12.31"),
])
def test_is_newer(newer, older):
    assert rt.is_newer(newer, older)
    assert not rt.is_newer(older, newer)
    assert not rt.is_newer(newer, newer)


def test_is_newer_handles_garbage():
    assert not rt.is_newer("", "2026.7.4")
    assert not rt.is_newer("2026.7.4", "")
    assert not rt.is_newer("?", "?")


# ---------------------------------------------------------------
# activation at startup
# ---------------------------------------------------------------

def _write_override(root, version: str, dir_name: str | None = None):
    dir_name = dir_name or version
    pkg = root / dir_name / "yt_dlp"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("from .version import __version__\n")
    (pkg / "version.py").write_text(f"__version__ = {version!r}\n")
    root.mkdir(exist_ok=True)
    (root / rt.ACTIVE_FILE).write_text(json.dumps({"version": version, "dir": dir_name}))
    return root / dir_name


def test_activate_prefers_newer_override(override_root, isolated_imports, monkeypatch):
    monkeypatch.setattr(rt, "base_version", lambda: "2026.7.4")
    _write_override(override_root, "2026.8.19")

    assert rt.activate() == "2026.8.19"
    assert sys.path[0] == str(override_root / "2026.8.19")

    import yt_dlp
    assert yt_dlp.__version__ == "2026.8.19"
    assert rt.active_version() == "2026.8.19"


def test_activate_discards_stale_override(override_root, isolated_imports, monkeypatch):
    """A new app build that ships a newer yt-dlp than the override must win,
    and the now-useless override gets cleaned up."""
    monkeypatch.setattr(rt, "base_version", lambda: "2026.9.1")
    d = _write_override(override_root, "2026.8.19")

    assert rt.activate() is None
    assert str(d) not in sys.path
    assert not (override_root / rt.ACTIVE_FILE).exists()
    assert not d.exists()
    assert rt.active_version() is None


def test_activate_ignores_missing_or_broken_manifest(override_root, isolated_imports, monkeypatch):
    monkeypatch.setattr(rt, "base_version", lambda: "2026.7.4")
    assert rt.activate() is None                       # nothing on disk
    override_root.mkdir()
    (override_root / rt.ACTIVE_FILE).write_text("{not json")
    assert rt.activate() is None
    (override_root / rt.ACTIVE_FILE).write_text(json.dumps({"version": "2026.8.19", "dir": "gone"}))
    assert rt.activate() is None                       # dir doesn't exist


# ---------------------------------------------------------------
# installing an update
# ---------------------------------------------------------------

@pytest.fixture
def fake_pypi(monkeypatch):
    """Route the module's HTTP helpers to an in-memory PyPI."""
    store = {"json": {}, "bytes": {}}

    def http_json(url):
        try:
            return store["json"][url]
        except KeyError:
            raise rt.UpdateError(f"unexpected JSON fetch: {url}")

    def http_bytes(url):
        try:
            return store["bytes"][url]
        except KeyError:
            raise rt.UpdateError(f"unexpected download: {url}")

    monkeypatch.setattr(rt, "_http_json", http_json)
    monkeypatch.setattr(rt, "_http_bytes", http_bytes)

    def add(name, version, blob, **kw):
        payload = pypi_payload(name, version, blob, **kw)
        store["json"][rt.pypi_url(name, version)] = payload
        store["json"].setdefault(rt.pypi_url(name), payload)
        wheel = next(u for u in payload["urls"] if u["packagetype"] == "bdist_wheel")
        store["bytes"][wheel["url"]] = blob
        return payload

    store["add"] = add
    return store


def test_install_update_writes_override_and_manifest(override_root, fake_pypi, monkeypatch):
    monkeypatch.setattr(rt, "installed_version", lambda name: {"yt-dlp": "2026.7.4", "yt-dlp-ejs": "0.8.0"}[name])
    blob = make_wheel("yt-dlp", "2026.8.19")
    fake_pypi["add"]("yt-dlp", "2026.8.19", blob,
                     requires_dist=['yt-dlp-ejs==0.8.0; extra == "default"'])

    res = rt.install_update("2026.8.19")

    assert res == {"ok": True, "version": "2026.8.19", "restart_needed": True}
    dest = override_root / "2026.8.19"
    assert (dest / "yt_dlp" / "__init__.py").exists()
    manifest = json.loads((override_root / rt.ACTIVE_FILE).read_text())
    assert manifest["version"] == "2026.8.19"
    assert manifest["dir"] == "2026.8.19"
    # companion pin matches what's bundled → not downloaded
    assert not (dest / "yt_dlp_ejs").exists()


def test_install_update_defaults_to_latest_stable(override_root, fake_pypi, monkeypatch):
    monkeypatch.setattr(rt, "installed_version", lambda name: "0")
    blob = make_wheel("yt-dlp", "2026.8.19")
    fake_pypi["add"]("yt-dlp", "2026.8.19", blob)

    res = rt.install_update()
    assert res["version"] == "2026.8.19"


def test_install_update_rejects_bad_checksum(override_root, fake_pypi, monkeypatch):
    monkeypatch.setattr(rt, "installed_version", lambda name: "0")
    blob = make_wheel("yt-dlp", "2026.8.19")
    payload = fake_pypi["add"]("yt-dlp", "2026.8.19", blob)
    wheel = next(u for u in payload["urls"] if u["packagetype"] == "bdist_wheel")
    fake_pypi["bytes"][wheel["url"]] = blob + b"tampered"

    with pytest.raises(rt.UpdateError, match="checksum"):
        rt.install_update("2026.8.19")
    assert not (override_root / rt.ACTIVE_FILE).exists()
    assert not (override_root / "2026.8.19").exists()


def test_install_update_rejects_unsupported_python(override_root, fake_pypi, monkeypatch):
    monkeypatch.setattr(rt, "installed_version", lambda name: "0")
    blob = make_wheel("yt-dlp", "2026.8.19")
    fake_pypi["add"]("yt-dlp", "2026.8.19", blob, requires_python=">=3.99")

    with pytest.raises(rt.UpdateError, match="Python"):
        rt.install_update("2026.8.19")


def test_install_update_fetches_companion_when_pin_changes(override_root, fake_pypi, monkeypatch):
    """yt-dlp pins yt-dlp-ejs exactly; when a release moves the pin, the
    override must carry the matching yt-dlp-ejs too or the JS challenge
    solver refuses to run."""
    monkeypatch.setattr(rt, "installed_version", lambda name: {"yt-dlp": "2026.7.4", "yt-dlp-ejs": "0.8.0"}[name])
    fake_pypi["add"]("yt-dlp", "2026.9.1", make_wheel("yt-dlp", "2026.9.1"),
                     requires_dist=['yt-dlp-ejs==0.9.0; extra == "default"'])
    fake_pypi["add"]("yt-dlp-ejs", "0.9.0", make_wheel("yt-dlp-ejs", "0.9.0"))

    res = rt.install_update("2026.9.1")

    assert res["ok"]
    dest = override_root / "2026.9.1"
    assert (dest / "yt_dlp_ejs" / "version.py").read_text().strip() == "__version__ = '0.9.0'"
    manifest = json.loads((override_root / rt.ACTIVE_FILE).read_text())
    assert manifest["companion"] == "0.9.0"


def test_install_update_replaces_previous_override(override_root, fake_pypi, monkeypatch):
    monkeypatch.setattr(rt, "installed_version", lambda name: "0")
    old = _write_override(override_root, "2026.8.19")
    fake_pypi["add"]("yt-dlp", "2026.9.1", make_wheel("yt-dlp", "2026.9.1"))

    rt.install_update("2026.9.1")

    manifest = json.loads((override_root / rt.ACTIVE_FILE).read_text())
    assert manifest["dir"] == "2026.9.1"
    assert not old.exists()


def test_install_update_refuses_unsafe_wheel_paths(override_root, fake_pypi, monkeypatch):
    monkeypatch.setattr(rt, "installed_version", lambda name: "0")
    blob = make_wheel("yt-dlp", "2026.8.19", extra_files={"../escape.py": "x = 1\n"})
    fake_pypi["add"]("yt-dlp", "2026.8.19", blob)

    with pytest.raises(rt.UpdateError, match="unsafe"):
        rt.install_update("2026.8.19")
    assert not (override_root.parent / "escape.py").exists()


def test_companion_pin_parsing():
    reqs = [
        'brotli; implementation_name == "cpython" and extra == "default"',
        'yt-dlp-ejs==0.8.0; extra == "default"',
        'yt-dlp-ejs==0.9.9; extra == "pin"',
    ]
    assert rt.companion_pin(reqs) == "0.8.0"
    assert rt.companion_pin([]) is None


@pytest.mark.parametrize("spec,ok", [
    (">=3.10", True),
    (">=3.99", False),
    ("<3.0", False),
    ("", True),
    (None, True),
    (">=3.10, <4", True),
])
def test_python_requirement_check(spec, ok):
    assert rt.python_satisfies(spec) is ok
