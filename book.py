from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from lib.writer import SnapshotManager
from lib.writer.write import write_dummy_content, write_generated_content


def _load_app_config(script_dir: Path) -> dict[str, object]:
    config_path = script_dir / ".pkbook" / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError(f"Config file must contain a JSON object: {config_path}")

    return payload


def _format_version_output(script_dir: Path) -> str:
    payload = _load_app_config(script_dir)
    app_name = str(payload.get("appname", "book"))
    version = str(payload.get("version", "unknown"))
    return f"{app_name} {version}"


def _default_json_log_mode(script_dir: Path) -> bool:
    try:
        payload = _load_app_config(script_dir)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return False

    log_config = payload.get("log", {})
    if not isinstance(log_config, dict):
        return False

    raw_content_type = log_config.get("content-type", log_config.get("content_type", ""))
    content_type = str(raw_content_type).strip().lower()
    return content_type == "json"


def _normalize_argv(argv: list[str]) -> list[str]:
    commands = {"init", "list", "export", "import", "clone", "write"}
    global_option_values = {"--workspace-root", "--config-path", "--encoding"}

    if not argv:
        return argv

    index = 0
    while index < len(argv):
        token = argv[index]
        if token in commands:
            return argv

        if token.startswith("-"):
            if token in global_option_values:
                index += 2
                continue
            index += 1
            continue

        return ["init", *argv]

    return ["init", *argv]


def _add_runtime_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging for major workflow steps.",
    )
    parser.add_argument(
        "--json",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Emit machine-readable JSON lines for verbose events (default can come from .pkbook/config.json log.content-type).",
    )


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent

    if "--version" in sys.argv[1:]:
        print(_format_version_output(script_dir))
        raise SystemExit(0)

    parser = argparse.ArgumentParser(
        prog="book.py",
        description="Initialize, list, export, import, clone, or write book workspaces.",
        epilog=(
            "Examples:\n"
            "  python book.py --book-name Ramayan\n"
            "  python book.py --workspace-root .\\.pkbook\\_wokspace init --book-name Sita\n"
            "  python book.py init --book-name Sita --chapter-count 8\n"
            "  python book.py list\n"
            "  python book.py --workspace-root .\\.pkbook\\_wokspace list\n"
            "  python book.py export --book-name Ramayan\n"
            "  python book.py export --book-name Ramayan --snapshot-path snapshots/ramayan.json\n"
            "  python book.py import --book-name Ramayan\n"
            "  python book.py import --book-name Ramayan --snapshot-path snapshots/ramayan.json\n"
            "  python book.py clone --source-book-name Ramayan --target-book-name Mahabharat\n"
            "  python book.py write --book-name Sita --gist \"A historical Bengali epic\"\n"
            "  python book.py write --book-name Sita --mode dummy\n"
            "  python book.py --verbose --json list\n"
            "  python book.py --version\n"
            "  python book.py --help"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show application version from .pkbook/config.json and exit.",
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
    _add_runtime_flags(parser)

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Create book folder and file structure")
    init_parser.add_argument("--book-name", required=True, help="Book folder name to create under workspace root.")
    init_parser.add_argument(
        "--chapter-count",
        type=int,
        help="Optional. Number of chapter folders to create from the configured start chapter.",
    )

    list_parser = subparsers.add_parser("list", help="List book folders under workspace root")

    export_parser = subparsers.add_parser("export", help="Read workspace files and write one snapshot JSON")
    export_parser.add_argument("--book-name", required=True, help="Book folder name under workspace root")
    export_parser.add_argument("--snapshot-path", help="Output snapshot JSON path (default: snapshots/<book-name>.json)")

    import_parser = subparsers.add_parser("import", help="Read one snapshot JSON and restore workspace files")
    import_parser.add_argument("--book-name", required=True, help="Target book folder name under workspace root")
    import_parser.add_argument("--snapshot-path", help="Input snapshot JSON path (default: snapshots/<book-name>.json)")

    clone_parser = subparsers.add_parser("clone", help="Clone one workspace book into another book folder")
    clone_parser.add_argument("--source-book-name", required=True, help="Existing source book folder name")
    clone_parser.add_argument("--target-book-name", required=True, help="New target book folder name")

    write_parser = subparsers.add_parser("write", help="Generate prompts/content for a book or use the legacy dummy writer")
    write_parser.add_argument("--book-name", required=True, help="Target book folder name under workspace root")
    write_parser.add_argument(
        "--mode",
        choices=("genai", "dummy"),
        default="genai",
        help="Write mode. 'genai' creates prompts and JSON from the model; 'dummy' keeps the old sample-content flow.",
    )
    write_parser.add_argument("--gist", help="Optional novel gist. If omitted in genai mode, you will be prompted.")
    write_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable GenAI response caching for the write command.",
    )

    for command_parser in (init_parser, list_parser, export_parser, import_parser, clone_parser, write_parser):
        _add_runtime_flags(command_parser)

    argv = sys.argv[1:]
    if not argv:
        parser.print_help()
        parser.exit(1)

    if argv[0] in {"-h", "--help"}:
        return parser.parse_args(argv)

    argv = _normalize_argv(argv)
    args = parser.parse_args(argv)
    if args.json is None:
        args.json = False
    return args


def _build_manager(args: argparse.Namespace) -> SnapshotManager:
    return SnapshotManager.from_config_file(
        args.config_path,
        encoding=args.encoding,
        verbose=args.verbose or args.json,
        json_logs=args.json,
    )


def _emit_verbose(args: argparse.Namespace, *, event: str, message: str, extra: dict[str, object] | None = None) -> None:
    if not (args.verbose or args.json):
        return

    if args.json:
        payload: dict[str, object] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": "book",
            "event": event,
            "message": message,
        }
        if extra:
            payload.update(extra)
        print(json.dumps(payload, ensure_ascii=False))
        return

    print(f"[verbose][book] {message}")


def _resolve_snapshot_path(args: argparse.Namespace) -> str:
    snapshot_path = getattr(args, "snapshot_path", None)
    if snapshot_path:
        return snapshot_path

    book_name = getattr(args, "book_name", None)
    if not book_name:
        raise ValueError("book_name is required to resolve the default snapshot path.")

    return str(Path("snapshots") / f"{book_name}.json")


@dataclass
class ProjectSettings:
    book_name: str
    chapter_count: int
    root_folder: str
    date_created: str
    location: str
    user: str


def _build_project_settings(args: argparse.Namespace, manager: SnapshotManager) -> ProjectSettings:
    chapter_count = args.chapter_count
    if chapter_count is None:
        chapters = manager.config.chapters
        chapter_count = chapters.end - chapters.start + 1

    return ProjectSettings(
        book_name=args.book_name,
        chapter_count=chapter_count,
        root_folder=str(Path(args.workspace_root)),
        date_created=datetime.now(timezone.utc).isoformat(),
        location=platform.node() or "unknown",
        user=os.environ.get("USERNAME") or os.environ.get("USER") or "unknown",
    )


def _serialize_project_settings(settings: ProjectSettings) -> str:
    return json.dumps(asdict(settings), ensure_ascii=False, indent=2)


def run_init(args: argparse.Namespace) -> None:
    _emit_verbose(args, event="init.start", message=f"Running init for '{args.book_name}'")
    manager = _build_manager(args)
    book_path = manager.initialize_workspace(
        workspace_root=args.workspace_root,
        book_name=args.book_name,
        number_of_chapters=args.chapter_count,
    )

    settings = _build_project_settings(args, manager)
    settings_string = _serialize_project_settings(settings)

    settings_path = book_path / "Settings.json"
    settings_path.write_text(settings_string, encoding=args.encoding)

    snapshot = manager.read_from_workspace(args.workspace_root, args.book_name)
    snapshot.rootFiles["Settings.json"] = settings_string
    snapshot_path = _resolve_snapshot_path(args)
    manager.write_snapshot_json(snapshot, snapshot_path)

    print(f"Structure created at: {book_path}")
    print(f"Settings initialized at: {settings_path}")
    print(f"Snapshot exported: {snapshot_path}")


def run_list(args: argparse.Namespace) -> None:
    _emit_verbose(args, event="list.start", message=f"Listing books under: {Path(args.workspace_root)}")
    workspace_root = Path(args.workspace_root)
    if not workspace_root.exists():
        print(f"Workspace root does not exist: {workspace_root}")
        return

    book_names = sorted(
        child.name
        for child in workspace_root.iterdir()
        if child.is_dir()
    )

    if not book_names:
        print(f"No books found in: {workspace_root}")
        return

    print("book_name\tchapter_count")
    for book_name in book_names:
        print(f"{book_name}\t{_resolve_book_chapter_count(workspace_root / book_name, args.encoding)}")


def _resolve_book_chapter_count(book_path: Path, encoding: str) -> int | str:
    settings_path = book_path / "Settings.json"
    if settings_path.exists():
        try:
            payload = json.loads(settings_path.read_text(encoding=encoding))
            return int(payload["chapter_count"])
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            pass

    chapter_root = book_path / "BookChapters"
    if chapter_root.exists():
        return sum(1 for child in chapter_root.iterdir() if child.is_dir())

    return "unknown"


def run_export(args: argparse.Namespace) -> None:
    _emit_verbose(args, event="export.start", message=f"Running export for '{args.book_name}'")
    manager = _build_manager(args)
    snapshot_path = _resolve_snapshot_path(args)
    manager.export_workspace_to_json(
        workspace_root=args.workspace_root,
        book_name=args.book_name,
        snapshot_path=snapshot_path,
    )
    print(f"Snapshot exported: {snapshot_path}")


def run_import(args: argparse.Namespace) -> None:
    _emit_verbose(args, event="import.start", message=f"Running import for '{args.book_name}'")
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
    _emit_verbose(
        args,
        event="clone.start",
        message=f"Running clone from '{args.source_book_name}' to '{args.target_book_name}'",
    )
    manager = _build_manager(args)
    manager.clone_workspace(
        workspace_root=args.workspace_root,
        source_book_name=args.source_book_name,
        target_book_name=args.target_book_name,
    )
    print(f"Book cloned: {args.source_book_name} -> {args.target_book_name}")


def run_write(args: argparse.Namespace) -> None:
    _emit_verbose(args, event="write.start", message=f"Running write for '{args.book_name}' in mode '{args.mode}'")
    if args.mode == "dummy":
        book_path = write_dummy_content(
            workspace_root=args.workspace_root,
            book_name=args.book_name,
            config_path=args.config_path,
            encoding=args.encoding,
            verbose=args.verbose or args.json,
            json_logs=args.json,
        )
        print(f"Dummy content written to: {book_path}")
        return

    book_path = write_generated_content(
        workspace_root=args.workspace_root,
        book_name=args.book_name,
        config_path=args.config_path,
        encoding=args.encoding,
        gist=args.gist,
        use_cache=not args.no_cache,
        verbose=args.verbose or args.json,
        json_logs=args.json,
    )
    print(f"Generated content written to: {book_path}")


def main() -> None:
    args = parse_args()

    if args.command == "init":
        run_init(args)
        return

    if args.command == "list":
        run_list(args)
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