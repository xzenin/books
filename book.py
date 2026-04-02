from __future__ import annotations

import argparse
import sys
from pathlib import Path

from snapshot_lib import SnapshotManager
from write import write_dummy_content


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        prog="book.py",
        description="Initialize, export, import, clone, or write book workspaces.",
        epilog=(
            "Examples:\n"
            "  python book.py --book-name Ramayan\n"
            "  python book.py init --book-name Sita --workspace-root .\\.pkbook\\_wokspace\n"
            "  python book.py export --book-name Ramayan\n"
            "  python book.py export --book-name Ramayan --snapshot-path snapshots/ramayan.json\n"
            "  python book.py import --book-name Ramayan\n"
            "  python book.py import --book-name Ramayan --snapshot-path snapshots/ramayan.json\n"
            "  python book.py clone --source-book-name Ramayan --target-book-name Mahabharat\n"
            "  python book.py write --book-name Sita\n"
            "  python book.py --help"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--workspace-root",
        default=str(script_dir / ".pkbook" / "_wokspace"),
        help="Optional. Root directory where the book folder will be created.",
    )
    parser.add_argument(
        "--config-path",
        default=str(script_dir / "templates" / "init.json"),
        help="Optional. Path to JSON config template.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Optional. Text encoding used for read/write.",
    )

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Create book folder and file structure")
    init_parser.add_argument("--book-name", required=True, help="Book folder name to create under workspace root.")

    export_parser = subparsers.add_parser("export", help="Read workspace files and write one snapshot JSON")
    export_parser.add_argument("--book-name", required=True, help="Book folder name under workspace root")
    export_parser.add_argument("--snapshot-path", help="Output snapshot JSON path (default: <book-name>.json)")

    import_parser = subparsers.add_parser("import", help="Read one snapshot JSON and restore workspace files")
    import_parser.add_argument("--book-name", required=True, help="Target book folder name under workspace root")
    import_parser.add_argument("--snapshot-path", help="Input snapshot JSON path (default: <book-name>.json)")

    clone_parser = subparsers.add_parser("clone", help="Clone one workspace book into another book folder")
    clone_parser.add_argument("--source-book-name", required=True, help="Existing source book folder name")
    clone_parser.add_argument("--target-book-name", required=True, help="New target book folder name")

    write_parser = subparsers.add_parser("write", help="Write dummy content into the configured book files")
    write_parser.add_argument("--book-name", required=True, help="Target book folder name under workspace root")

    argv = sys.argv[1:]
    if not argv:
        parser.print_help()
        parser.exit(1)

    if argv[0] in {"-h", "--help"}:
        return parser.parse_args(argv)

    if argv[0] not in {"init", "export", "import", "clone", "write"}:
        argv = ["init", *argv]

    return parser.parse_args(argv)


def _build_manager(args: argparse.Namespace) -> SnapshotManager:
    return SnapshotManager.from_config_file(args.config_path, encoding=args.encoding)


def _resolve_snapshot_path(args: argparse.Namespace) -> str:
    snapshot_path = getattr(args, "snapshot_path", None)
    if snapshot_path:
        return snapshot_path

    book_name = getattr(args, "book_name", None)
    if not book_name:
        raise ValueError("book_name is required to resolve the default snapshot path.")

    return f"{book_name}.json"


def run_init(args: argparse.Namespace) -> None:
    manager = _build_manager(args)
    book_path = manager.initialize_workspace(
        workspace_root=args.workspace_root,
        book_name=args.book_name,
    )
    print(f"Structure created at: {book_path}")


def run_export(args: argparse.Namespace) -> None:
    manager = _build_manager(args)
    snapshot_path = _resolve_snapshot_path(args)
    manager.export_workspace_to_json(
        workspace_root=args.workspace_root,
        book_name=args.book_name,
        snapshot_path=snapshot_path,
    )
    print(f"Snapshot exported: {snapshot_path}")


def run_import(args: argparse.Namespace) -> None:
    manager = _build_manager(args)
    snapshot_path = _resolve_snapshot_path(args)
    snapshot = manager.load_snapshot_json(snapshot_path)
    manager.restore_to_workspace(
        snapshot=snapshot,
        workspace_root=args.workspace_root,
        book_name=args.book_name,
    )
    print(f"Snapshot imported: {snapshot_path}")


def run_clone(args: argparse.Namespace) -> None:
    manager = _build_manager(args)
    manager.clone_workspace(
        workspace_root=args.workspace_root,
        source_book_name=args.source_book_name,
        target_book_name=args.target_book_name,
    )
    print(f"Book cloned: {args.source_book_name} -> {args.target_book_name}")


def run_write(args: argparse.Namespace) -> None:
    book_path = write_dummy_content(
        workspace_root=args.workspace_root,
        book_name=args.book_name,
        config_path=args.config_path,
        encoding=args.encoding,
    )
    print(f"Dummy content written to: {book_path}")


def main() -> None:
    args = parse_args()

    if args.command == "init":
        run_init(args)
        return

    if args.command == "export":
        run_export(args)
        return

    if args.command == "import":
        run_import(args)
        return

    if args.command == "clone":
        run_clone(args)
        return

    if args.command == "write":
        run_write(args)
        return

    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()