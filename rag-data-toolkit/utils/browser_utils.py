from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Iterable


def _existing(paths: Iterable[Path]) -> str | None:
    for path in paths:
        try:
            if path and path.is_file():
                return str(path)
        except OSError:
            continue
    return None


def find_system_chrome(explicit_path: str | None = None) -> str | None:
    """Return a local Google Chrome executable path when available.

    Resolution order:
    1. explicit path from config
    2. executable names found on PATH
    3. common install locations for Windows/macOS/Linux
    """
    if explicit_path:
        p = Path(os.path.expandvars(os.path.expanduser(explicit_path)))
        if p.is_file():
            return str(p)

    # PATH candidates first. On Windows, `where chrome` is not always available,
    # so common install paths are still checked below.
    for name in ("chrome", "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        found = shutil.which(name)
        if found:
            return found

    candidates: list[Path] = []

    if sys.platform.startswith("win"):
        env = os.environ
        for base_key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = env.get(base_key)
            if base:
                candidates.append(Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe")
    elif sys.platform == "darwin":
        candidates.extend([
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ])
    else:
        candidates.extend([
            Path("/usr/bin/google-chrome"),
            Path("/usr/bin/google-chrome-stable"),
            Path("/usr/bin/chromium"),
            Path("/usr/bin/chromium-browser"),
            Path("/snap/bin/chromium"),
        ])

    return _existing(candidates)


def browser_launch_args(cfg: dict) -> tuple[dict, dict]:
    """Build Playwright launch kwargs and diagnostics.

    System Chrome is preferred. If it cannot be found, the returned launch args
    intentionally omit executable_path so Playwright can fall back to its bundled
    Chromium when that browser has been installed.
    """
    pagination = cfg.get("pagination", {})
    browser_cfg = pagination.get("browser", {}) or {}

    headless = bool(pagination.get("headless", True))
    prefer_system = bool(browser_cfg.get("prefer_system_chrome", True))
    explicit_path = browser_cfg.get("executable_path") or None

    args: dict = {"headless": headless}
    diagnostics = {
        "prefer_system_chrome": prefer_system,
        "browser_source": "playwright_chromium",
        "browser_executable": None,
    }

    if prefer_system:
        chrome = find_system_chrome(explicit_path)
        if chrome:
            args["executable_path"] = chrome
            diagnostics["browser_source"] = "system_chrome"
            diagnostics["browser_executable"] = chrome

    return args, diagnostics
