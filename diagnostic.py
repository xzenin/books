#!/usr/bin/env python3
"""Diagnostic script to check MongoDB connection and manager selection."""

from pathlib import Path
import sys

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.io.factory import resolve_snapshot_type, build_snapshot_manager_from_files
from lib.models import SnapshotConfig

print("=" * 60)
print("DIAGNOSTIC: MongoDB Manager Selection & Connection")
print("=" * 60)

# Check config
config_path = Path(".pkbook/config.json")
print(f"\n1. Config path: {config_path}")
print(f"   Exists: {config_path.exists()}")

if config_path.exists():
    import json
    config = json.loads(config_path.read_text())
    snapshot_type = config.get("snapshot", {}).get("type")
    print(f"   snapshot.type: {snapshot_type}")

# Check backend selection
print(f"\n2. Backend selection:")
backend = resolve_snapshot_type(
    app_config_path=config_path,
    workspace_root=Path(".pkbook/_workspace")
)
print(f"   Selected backend: {backend}")

# Try to build manager
print(f"\n3. Building manager:")
try:
    config = SnapshotConfig.from_json_file("templates/init.json")
    manager = build_snapshot_manager_from_files(
        config_path="templates/init.json",
        workspace_root=Path(".pkbook/_workspace"),
        verbose=True,
    )
    print(f"   ✓ Manager created: {type(manager).__name__}")
    print(f"   Storage backend: {manager.storage_backend}")
    
    # Check if MongoDB collection is available
    if hasattr(manager, '_pkbook_collection'):
        print(f"   MongoDB collection: {manager._pkbook_collection}")
    if hasattr(manager, '_files_collection'):
        print(f"   Files collection: {manager._files_collection}")
        
except Exception as e:
    print(f"   ✗ ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
