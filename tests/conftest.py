"""Shared pytest setup.

`app.bridge` creates the config directory under %APPDATA% at import
time, so point APPDATA at a throwaway folder before any test imports it.
"""
import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_TEST_APPDATA = Path(tempfile.mkdtemp(prefix="youtmanager-tests-"))
os.environ["APPDATA"] = str(_TEST_APPDATA)
