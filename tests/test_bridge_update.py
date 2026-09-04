"""PyBridge update + restart wiring.

The bug these guard against: the old updater shelled out to
`sys.executable -m pip`, which in the PyInstaller build is YouTManager.exe
itself — so "Update" launched a second copy of the app and reported
success when the user closed it."""
import subprocess

import pytest

from app import bridge, relaunch, ytdlp_runtime


@pytest.fixture
def api(monkeypatch, tmp_path):
    monkeypatch.setattr(bridge, "SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr(bridge, "HISTORY_FILE", tmp_path / "history.json")
    monkeypatch.setattr(bridge, "QUEUE_FILE", tmp_path / "queue.json")
    monkeypatch.setattr(bridge, "LOGS_DIR", tmp_path / "logs")
    (tmp_path / "logs").mkdir()
    b = bridge.PyBridge()
    yield b
    b._mgr.shutdown()


def test_ytdlp_update_never_spawns_the_interpreter(api, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("ytdlp_update must not shell out to sys.executable")
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)

    seen = {}
    def fake_install(version=None):
        seen["version"] = version
        return {"ok": True, "version": version or "2026.8.19", "restart_needed": True}
    monkeypatch.setattr(ytdlp_runtime, "install_update", fake_install)

    res = api.ytdlp_update("2026.8.19")

    assert res == {"ok": True, "version": "2026.8.19", "restart_needed": True}
    assert seen["version"] == "2026.8.19"
    assert api._settings.get("ytdlp_last_check")


def test_ytdlp_update_reports_failure_without_marking_checked(api, monkeypatch):
    def fake_install(version=None):
        raise ytdlp_runtime.UpdateError("checksum mismatch")
    monkeypatch.setattr(ytdlp_runtime, "install_update", fake_install)
    api._settings.pop("ytdlp_last_check", None)

    res = api.ytdlp_update("2026.8.19")

    assert res["ok"] is False
    assert "checksum" in res["error"]
    assert not api._settings.get("ytdlp_last_check")


def test_ytdlp_check_update_reports_override(api, monkeypatch):
    monkeypatch.setattr(ytdlp_runtime, "_http_json",
                        lambda url: {"info": {"version": "2026.8.19"}})
    monkeypatch.setattr(api, "ytdlp_version", lambda: "2026.7.4")
    monkeypatch.setattr(ytdlp_runtime, "active_version", lambda: None)

    res = api.ytdlp_check_update()

    assert res["current"] == "2026.7.4"
    assert res["latest"] == "2026.8.19"
    assert res["update_available"] is True


def test_restart_app_pauses_downloads_spawns_and_closes(api, monkeypatch):
    events = []
    monkeypatch.setattr(relaunch, "spawn_replacement", lambda: events.append("spawn") or 1)

    class FakeWindow:
        def destroy(self):
            events.append("destroy")
        def evaluate_js(self, _js):
            pass
    api.attach(FakeWindow())

    # Two queue rows: one mid-download, one already done.
    with api._mgr._lock:
        api._mgr._items.append({**api._mgr._new_item("https://youtu.be/abc"), "status": "Downloading"})
        api._mgr._items.append({**api._mgr._new_item("https://youtu.be/def"), "status": "Done"})
    downloading_id = api._mgr._items[0]["id"]

    assert api.restart_app() is True

    assert events == ["spawn", "destroy"]
    assert downloading_id in api._mgr._cancelled
    statuses = {i["url"]: i["status"] for i in api._mgr.all()}
    assert statuses["https://youtu.be/abc"] == "Paused"
    assert statuses["https://youtu.be/def"] == "Done"


def test_restart_app_reports_spawn_failure(api, monkeypatch):
    def boom():
        raise OSError("no exe")
    monkeypatch.setattr(relaunch, "spawn_replacement", boom)
    destroyed = []

    class FakeWindow:
        def destroy(self):
            destroyed.append(True)
        def evaluate_js(self, _js):
            pass
    api.attach(FakeWindow())

    assert api.restart_app() is False
    assert not destroyed          # don't close the app if we couldn't start a new one
