from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Iterable


def ensure_parent(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def dump_json(path: str | Path, data: Any) -> None:
    p = ensure_parent(path)
    with p.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(path: str | Path, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    with p.open('r', encoding='utf-8') as f:
        return json.load(f)


def append_jsonl(path: str | Path, item: Any) -> None:
    p = ensure_parent(path)
    if is_dataclass(item):
        item = asdict(item)
    with p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')


def write_jsonl(path: str | Path, items: Iterable[Any]) -> None:
    p = ensure_parent(path)
    with p.open('w', encoding='utf-8') as f:
        for item in items:
            if is_dataclass(item):
                item = asdict(item)
            f.write(json.dumps(item, ensure_ascii=False) + '\n')


def read_jsonl(path: str | Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    with p.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
