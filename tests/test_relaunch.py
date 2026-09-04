"""Tests for app.relaunch — spawning a replacement process and having the
new instance wait for the old one to exit."""
import os
import subprocess
import sys
import time

import pytest

from app import relaunch


def test_command_in_dev_mode_reruns_the_script(monkeypatch):
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "argv", ["launcher.py"])
    assert relaunch.relaunch_command() == [sys.executable, "launcher.py"]


def test_command_when_frozen_reruns_the_exe(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\apps\YouTManager.exe")
    monkeypatch.setattr(sys, "argv", [r"C:\apps\YouTManager.exe", "--flag"])
    assert relaunch.relaunch_command() == [r"C:\apps\YouTManager.exe", "--flag"]


def test_spawn_replacement_passes_parent_pid(monkeypatch):
    calls = []

    class FakeProc:
        pid = 4242

    def fake_popen(cmd, **kw):
        calls.append((cmd, kw))
        return FakeProc()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(sys, "argv", ["launcher.py"])

    pid = relaunch.spawn_replacement()

    assert pid == 4242
    cmd, kw = calls[0]
    assert cmd == [sys.executable, "launcher.py"]
    assert kw["env"][relaunch.WAIT_ENV] == str(os.getpid())
    assert kw["close_fds"] is True


def test_wait_for_parent_noop_without_env(monkeypatch):
    monkeypatch.delenv(relaunch.WAIT_ENV, raising=False)
    assert relaunch.wait_for_parent(timeout=0.1) is True


def test_wait_for_parent_returns_once_process_exits(monkeypatch):
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(0.5)"])
    monkeypatch.setenv(relaunch.WAIT_ENV, str(proc.pid))
    t0 = time.monotonic()
    assert relaunch.wait_for_parent(timeout=10) is True
    assert time.monotonic() - t0 < 8
    proc.wait()
    # env var is consumed so a later restart doesn't wait on a stale pid
    assert relaunch.WAIT_ENV not in os.environ


def test_wait_for_parent_gives_up_after_timeout(monkeypatch):
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"])
    try:
        monkeypatch.setenv(relaunch.WAIT_ENV, str(proc.pid))
        assert relaunch.wait_for_parent(timeout=0.5) is False
    finally:
        proc.kill()
        proc.wait()


def test_wait_for_parent_tolerates_garbage_pid(monkeypatch):
    monkeypatch.setenv(relaunch.WAIT_ENV, "not-a-pid")
    assert relaunch.wait_for_parent(timeout=0.1) is True
