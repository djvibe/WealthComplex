"""Snapshot persistence utilities for wealthgrabber."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

DEFAULT_DATA_DIR = ".wealthgrabber"


# Supported snapshot categories used by CLI commands.
SNAPSHOT_ACCOUNTS = "accounts"
SNAPSHOT_ACTIVITIES = "activities"
SNAPSHOT_ASSETS = "assets"


def get_data_root() -> Path:
    """Return root directory for wealthgrabber local data files."""
    override = os.getenv("WEALTHGRABBER_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / DEFAULT_DATA_DIR


def get_snapshots_root() -> Path:
    """Return root directory where snapshots are stored."""
    return get_data_root() / "snapshots"


def _serialize_record(record: Any) -> dict[str, Any]:
    """Serialize a record object into JSON-compatible dict."""
    if is_dataclass(record):
        return asdict(record)
    if isinstance(record, dict):
        return record
    return {"value": str(record)}


def write_snapshot(snapshot_type: str, records: Sequence[Any]) -> Path | None:
    """Write a timestamped snapshot file for fetched command data.

    Returns created file path on success, None on failure.
    """
    now = datetime.now(UTC)
    target_dir = (
        get_snapshots_root()
        / snapshot_type
        / f"{now.year:04d}"
        / f"{now.month:02d}"
        / f"{now.day:02d}"
    )
    filename = f"{now.strftime('%H%M%S')}-{now.microsecond:06d}.json"
    payload = {
        "snapshot_type": snapshot_type,
        "created_at": now.isoformat(),
        "record_count": len(records),
        "records": [_serialize_record(r) for r in records],
    }

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / filename
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path
    except Exception:
        # Snapshot persistence should not break command execution.
        return None


def _iter_snapshot_files(snapshot_type: str) -> list[Path]:
    """Return snapshot files for a snapshot type in chronological order."""
    root = get_snapshots_root() / snapshot_type
    if not root.exists():
        return []
    files = [p for p in root.rglob("*.json") if p.is_file()]
    return sorted(files)


def load_snapshots(snapshot_type: str, lookback_days: int | None = None) -> list[dict[str, Any]]:
    """Load snapshot payloads for a type, optionally within lookback window."""
    now = datetime.now(UTC)
    cutoff = None
    if lookback_days is not None and lookback_days > 0:
        cutoff = now.timestamp() - (lookback_days * 24 * 60 * 60)

    snapshots: list[dict[str, Any]] = []
    for file_path in _iter_snapshot_files(snapshot_type):
        if cutoff is not None and file_path.stat().st_mtime < cutoff:
            continue
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                snapshots.append(data)
        except Exception:
            continue

    snapshots.sort(key=lambda s: str(s.get("created_at", "")))
    return snapshots
