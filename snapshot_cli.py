from __future__ import annotations

import argparse
from pathlib import Path

from snapshot_lib import SnapshotManager


def build_parser() -> argparse.ArgumentParser:
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        prog="snapshot_cli.py",
        description="Export or import a full book workspace snapshot as one JSON file.",
        epilog=(
            "Examples:\n"
            "  python snapshot_cli.py export --book-name DemoBook --snapshot-path DemoBook.snapshot.json\n"
            "  python snapshot_cli.py import --book-name DemoBook --snapshot-path DemoBook.snapshot.json\n"
            "  python snapshot_cli.py refresh --book-name Ramayan --snapshot-path snapshots/ramayan.json --workspace-root ./_workspace"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--config-path",
        default=str(script_dir / "init.json"),
        help="Path to init config JSON (default: ./init.json)",
    )
    parser.add_argument(
        "--workspace-root",
        default=str(script_dir / "_workspace"),
        help="Book workspace root folder (default: ./_workspace)",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Text encoding used for read/write (default: utf-8)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    export_parser = subparsers.add_parser("export", help="Read workspace files and write one snapshot JSON")
    export_parser.add_argument("--book-name", required=True, help="Book folder name under workspace root")
    export_parser.add_argument("--snapshot-path", required=True, help="Output snapshot JSON path")

    import_parser = subparsers.add_parser("import", help="Read one snapshot JSON and restore workspace files")
    import_parser.add_argument("--book-name", required=True, help="Target book folder name under workspace root")
    import_parser.add_argument("--snapshot-path", required=True, help="Input snapshot JSON path")

    refresh_parser = subparsers.add_parser(
        "refresh",
        help="Update snapshot JSON from current workspace file contents",
    )
    refresh_parser.add_argument("--book-name", required=True, help="Book folder name under workspace root")
    refresh_parser.add_argument("--snapshot-path", required=True, help="Snapshot JSON path to update")

    return parser


def _build_manager(args: argparse.Namespace) -> SnapshotManager:
    return SnapshotManager.from_config_file(args.config_path, encoding=args.encoding)


def run_export(args: argparse.Namespace) -> None:
    manager = _build_manager(args)
    manager.export_workspace_to_json(
        workspace_root=args.workspace_root,
        book_name=args.book_name,
        snapshot_path=args.snapshot_path,
    )
    print(f"Snapshot exported: {args.snapshot_path}")


def run_import(args: argparse.Namespace) -> None:
    manager = _build_manager(args)
    snapshot = manager.load_snapshot_json(args.snapshot_path)
    manager.restore_to_workspace(
        snapshot=snapshot,
        workspace_root=args.workspace_root,
        book_name=args.book_name,
    )
    print(f"Snapshot imported: {args.snapshot_path}")


def run_refresh(args: argparse.Namespace) -> None:
    manager = _build_manager(args)
    manager.refresh_snapshot_json_from_workspace(
        workspace_root=args.workspace_root,
        snapshot_path=args.snapshot_path,
        book_name=args.book_name,
    )
    print(f"Snapshot refreshed: {args.snapshot_path}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "export":
        run_export(args)
        return

    if args.command == "import":
        run_import(args)
        return

    if args.command == "refresh":
        run_refresh(args)
        return

    parser.error("Unsupported command")


if __name__ == "__main__":
    main()
