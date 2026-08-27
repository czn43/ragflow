from __future__ import annotations

from pathlib import Path


FLAT_MARKER = '.flat_workspace'


def is_flat_workspace(root: Path) -> bool:
    return (Path(root) / FLAT_MARKER).exists()


def mark_flat_workspace(root: Path) -> None:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / FLAT_MARKER).write_text('v1\n', encoding='ascii')


def data_root(root: Path) -> Path:
    """Resolve stage-data root.

    Backward-compatible/default behavior is <root>/data. Multi-source site runs are
    explicitly marked with .flat_workspace and keep 00_urls..06_final directly
    beneath the site run directory.
    """
    root = Path(root)
    return root if is_flat_workspace(root) else root / 'data'


def reports_root(root: Path) -> Path:
    return Path(root) / 'reports'


def data_path(root: Path, *parts: str) -> Path:
    return data_root(Path(root)).joinpath(*parts)


def report_path(root: Path, *parts: str) -> Path:
    return reports_root(Path(root)).joinpath(*parts)


def relative_data_path(root: Path, *parts: str) -> str:
    prefix = Path() if is_flat_workspace(Path(root)) else Path('data')
    return str(prefix.joinpath(*parts)).replace('\\', '/')
