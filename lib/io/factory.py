from __future__ import annotations

import json
from pathlib import Path

from .filemanager import FileSnapshotManager
from lib.io.manager import SnapshotManager as AbstractSnapshotManager
from lib.models import SnapshotConfig
from .mongomanager import MongoSnapshotManager


def normalize_snapshot_type(raw_value: object) -> str:
    value = str(raw_value or "filesystem").strip().lower()
    if value in {"mongo", "mongodb"}:
        return "mongo"
    return "filesystem"


def infer_app_config_path(workspace_root: str | Path | None = None) -> Path:
    if workspace_root is not None:
        root = Path(workspace_root)
        candidate = root.parent / "config.json"
        if candidate.exists():
            return candidate
    return Path(".pkbook") / "config.json"


def resolve_snapshot_type(
    *,
    snapshot_type: str | None = None,
    app_config_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
) -> str:
    if snapshot_type:
        return normalize_snapshot_type(snapshot_type)

    resolved_path = Path(app_config_path) if app_config_path is not None else infer_app_config_path(workspace_root)
    try:
        payload = json.loads(resolved_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            snapshot_payload = payload.get("snapshot", {})
            if isinstance(snapshot_payload, dict):
                return normalize_snapshot_type(snapshot_payload.get("type"))
    except (OSError, json.JSONDecodeError):
        pass

    return "filesystem"


def build_snapshot_manager(
    config: SnapshotConfig,
    *,
    workspace_root: str | Path | None = None,
    book_name: str | None = None,
    encoding: str = "utf-8",
    verbose: bool = False,
    json_logs: bool = False,
    snapshot_type: str | None = None,
    app_config_path: str | Path | None = None,
) -> AbstractSnapshotManager:
    backend = resolve_snapshot_type(
        snapshot_type=snapshot_type,
        app_config_path=app_config_path,
        workspace_root=workspace_root,
    )
    manager_cls = MongoSnapshotManager if backend == "mongo" else FileSnapshotManager
    return manager_cls(
        config,
        workspace_root=workspace_root,
        book_name=book_name,
        encoding=encoding,
        verbose=verbose,
        json_logs=json_logs,
    )


def build_snapshot_manager_from_files(
    *,
    config_path: str | Path,
    workspace_root: str | Path | None = None,
    book_name: str | None = None,
    encoding: str = "utf-8",
    verbose: bool = False,
    json_logs: bool = False,
    snapshot_type: str | None = None,
    app_config_path: str | Path | None = None,
) -> AbstractSnapshotManager:
    config = SnapshotConfig.from_json_file(config_path)
    return build_snapshot_manager(
        config,
        workspace_root=workspace_root,
        book_name=book_name,
        encoding=encoding,
        verbose=verbose,
        json_logs=json_logs,
        snapshot_type=snapshot_type,
        app_config_path=app_config_path,
    )
