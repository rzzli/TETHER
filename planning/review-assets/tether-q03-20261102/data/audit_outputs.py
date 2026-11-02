"""Reserve fresh Q03 output directories and refuse all file replacement."""
from __future__ import annotations

import json
import re
from pathlib import Path


def reserve_run_directories(run_id: str, report_root: Path, cache_root: Path) -> tuple[Path, Path]:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", run_id) is None:
        raise ValueError("run_id must be 1-80 ASCII letters/digits/underscores/hyphens, starting with a letter/digit")
    roots = (report_root.resolve(), cache_root.resolve())
    paths = tuple((root / run_id).resolve() for root in roots)
    if paths[0] == paths[1] or any(path.parent != root for path, root in zip(paths, roots)):
        raise ValueError("Run directories must be distinct direct children of their roots")
    if any(path.exists() for path in paths):
        raise FileExistsError("Run ID already exists in report or cache outputs; choose a fresh run ID")
    for root in roots:
        root.mkdir(parents=True, exist_ok=True)
    # exist_ok=False also protects against a race after the preflight check.
    # A partial directory reservation remains as an honest failed-attempt record.
    for path in paths:
        path.mkdir(exist_ok=False)
    return paths


def save_new_json(path: Path, value) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
