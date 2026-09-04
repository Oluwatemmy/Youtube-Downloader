"""Restart the app in place.

`spawn_replacement()` starts a fresh copy of whatever is running (the
frozen exe, or `python launcher.py` in dev) and hands it our PID through
an environment variable. The new copy calls `wait_for_parent()` first
thing, so it doesn't start touching queue.json / settings.json while the
old process is still flushing them on the way out.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import List

WAIT_ENV = "YOUTMANAGER_WAIT_FOR_PID"


def relaunch_command() -> List[str]:
    if getattr(sys, "frozen", False):
        # PyInstaller: sys.executable IS the app.
        return [sys.executable, *sys.argv[1:]]
    # Dev: sys.executable is python, argv[0] is launcher.py / app/main.py.
    return [sys.executable, *sys.argv]


def spawn_replacement() -> int:
    """Start the replacement process and return its PID. Raises on failure
    so the caller can keep the current window open."""
    env = dict(os.environ)
    env[WAIT_ENV] = str(os.getpid())
    kwargs = dict(cwd=os.getcwd(), env=env, close_fds=True)
    if sys.platform == "win32":
        # Own process group so closing our window can't take it down with us.
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(relaunch_command(), **kwargs)
    return proc.pid


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.WaitForSingleObject.restype = wintypes.DWORD
        k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        SYNCHRONIZE = 0x00100000
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        WAIT_TIMEOUT = 0x102
        handle = k32.OpenProcess(SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False  # gone (or not ours to watch — don't block startup)
        try:
            return k32.WaitForSingleObject(handle, 0) == WAIT_TIMEOUT
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def wait_for_parent(timeout: float = 20.0) -> bool:
    """If we were spawned as a replacement, block until the old process is
    gone (or `timeout` seconds pass). Returns True when it's safe to go on,
    False if we gave up waiting. Consumes the env var either way."""
    raw = os.environ.pop(WAIT_ENV, None)
    if not raw:
        return True
    try:
        pid = int(raw)
    except ValueError:
        return True
    deadline = time.monotonic() + timeout
    while _pid_alive(pid):
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.1)
    return True
