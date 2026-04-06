from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from lib.writer import AbstractSnapshotManager, build_snapshot_manager_from_files
from lib.models import WorkspaceSnapshot
from lib.writer.write import publish_book_content, write_authored_content, write_dummy_content, write_generated_content


_GLOBAL_SNAPSHOT_MANAGER: AbstractSnapshotManager | None = None
_GLOBAL_WORKSPACE_SNAPSHOT: WorkspaceSnapshot | None = None


def _ensure_config(script_dir: Path) -> None:
    config_path = script_dir / ".pkbook" / "config.json"
    if config_path.exists():
        return
    template_path = script_dir / "templates" / "config.example.json"
    if not template_path.exists():
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(template_path, config_path)


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


def _print_console_text(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        stream_encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_text = text.encode(stream_encoding, errors="replace").decode(stream_encoding, errors="replace")
        print(safe_text)


def _normalize_argv(argv: list[str]) -> list[str]:
    commands = {"init", "list", "export", "import", "clone", "layout", "draft", "publish", "read", "rm", "purge"}
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
        "--debug",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Show full Python traceback on failures.",
    )
    parser.add_argument(
        "--json",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Emit machine-readable JSON lines for verbose events (default can come from .pkbook/config.json log.content-type).",
    )


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: {value}") from exc

    if parsed < 1:
        raise argparse.ArgumentTypeError("must be >= 1")

    return parsed


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent

    if "--version" in sys.argv[1:]:
        print(_format_version_output(script_dir))
        raise SystemExit(0)

    parser = argparse.ArgumentParser(
        prog="book.py",
        description="Initialize, list, export, import, clone, layout, draft, publish, read, rm, or purge book workspaces.",
        epilog=(
            "Examples:\n"
            "  python book.py --book-name Ramayan\n"
            "  python book.py --workspace-root .\\.pkbook\\_workspace init --book-name Sita\n"
            "  python book.py init --book-name Sita --chapter-count 8\n"
            "  python book.py list\n"
            "  python book.py --workspace-root .\\.pkbook\\_workspace list\n"
            "  python book.py export --book-name Ramayan\n"
            "  python book.py export --book-name Ramayan --snapshot-path snapshots/ramayan.json\n"
            "  python book.py import --book-name Ramayan\n"
            "  python book.py import --book-name Ramayan --snapshot-path snapshots/ramayan.json\n"
            "  python book.py clone --source-book-name Ramayan --target-book-name Mahabharat\n"
            "  python book.py layout --book-name Sita --gist \"A historical Bengali epic\"\n"
            "  python book.py layout --book-name Sita --mode dummy\n"
            "  python book.py draft --book-name Sita --gist \"A historical Bengali epic\"\n"
            "  python book.py publish --book-name Sita\n"
            "  python book.py read --book-name Sita\n"
            "  python book.py rm --book-name Sita --yes\n"
            "  python book.py purge --yes\n"
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
        default=str(script_dir / ".pkbook" / "_workspace"),
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
        type=_positive_int,
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

    layout_parser = subparsers.add_parser("layout", help="Generate prompts/content for a book or use the legacy dummy writer")
    layout_parser.add_argument("--book-name", required=True, help="Target book folder name under workspace root")
    layout_parser.add_argument(
        "--chapter-count",
        type=_positive_int,
        help="Optional. Number of chapter folders to create when layout auto-initializes a missing workspace.",
    )
    layout_parser.add_argument(
        "--mode",
        choices=("genai", "dummy"),
        default="genai",
        help="Layout mode. 'genai' creates prompts and JSON from the model; 'dummy' keeps the old sample-content flow.",
    )
    layout_parser.add_argument("--gist", help="Optional novel gist. If omitted in genai mode, you will be prompted.")
    layout_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable GenAI response caching for the layout command.",
    )
    layout_parser.add_argument(
        "--human-in-loop",
        action="store_true",
        help="Enable optional per-chapter manual refinement note during layout.",
    )
    layout_parser.add_argument(
        "--no-randomize-thoughts",
        action="store_true",
        help="Disable randomized refinement thought injection for chapter context.",
    )

    draft_parser = subparsers.add_parser(
        "draft",
        help="Write chapter-by-chapter story outputs from BookOutline and ChapterParameter context",
    )
    draft_parser.add_argument("--book-name", required=True, help="Target book folder name under workspace root")
    draft_parser.add_argument(
        "--chapter-count",
        type=_positive_int,
        help="Optional. Number of chapter folders to create when draft auto-initializes a missing workspace.",
    )
    draft_parser.add_argument(
        "--gist",
        help="Optional novel gist override. If omitted, gist is read from BookOutline.json when available.",
    )
    draft_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable GenAI response caching for the draft command.",
    )

    publish_parser = subparsers.add_parser(
        "publish",
        help="Append chapter generated text into a single BookPublished.txt file",
    )
    publish_parser.add_argument("--book-name", required=True, help="Target book folder name under workspace root")
    publish_parser.add_argument(
        "--output-path",
        help="Optional output file path (default: <workspace>/<book-name>/BookPublished.txt)",
    )

    read_parser = subparsers.add_parser(
        "read",
        help="Read and print BookPublished.txt for a book",
    )
    read_parser.add_argument("--book-name", required=True, help="Target book folder name under workspace root")

    rm_parser = subparsers.add_parser(
        "rm",
        help="Remove one book folder from workspace root",
    )
    rm_parser.add_argument("--book-name", required=True, help="Target book folder name under workspace root")
    rm_parser.add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation flag for deletion.",
    )

    purge_parser = subparsers.add_parser(
        "purge",
        help="Remove all book folders under workspace root",
    )
    purge_parser.add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation flag for deleting all books.",
    )

    for command_parser in (
        init_parser,
        list_parser,
        export_parser,
        import_parser,
        clone_parser,
        layout_parser,
        draft_parser,
        publish_parser,
        read_parser,
        rm_parser,
        purge_parser,
    ):
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
    if args.debug is None:
        args.debug = False
    return args


def _resolve_entry_book_name(args: argparse.Namespace) -> str | None:
    if hasattr(args, "book_name") and args.book_name:
        return str(args.book_name)
    if hasattr(args, "source_book_name") and args.source_book_name:
        return str(args.source_book_name)
    if hasattr(args, "target_book_name") and args.target_book_name:
        return str(args.target_book_name)
    return None


def _bootstrap_entrypoint_singletons(args: argparse.Namespace) -> None:
    global _GLOBAL_SNAPSHOT_MANAGER
    global _GLOBAL_WORKSPACE_SNAPSHOT

    if _GLOBAL_SNAPSHOT_MANAGER is not None and _GLOBAL_WORKSPACE_SNAPSHOT is not None:
        return

    entry_book_name = _resolve_entry_book_name(args)
    manager = build_snapshot_manager_from_files(
        config_path=args.config_path,
        workspace_root=args.workspace_root,
        book_name=entry_book_name,
        encoding=args.encoding,
        verbose=args.verbose or args.json,
        json_logs=args.json,
    )
    snapshot = manager.initialize_workspace_snapshot(book_name=entry_book_name)
    WorkspaceSnapshot.set_singleton(snapshot)
    _GLOBAL_SNAPSHOT_MANAGER = manager
    _GLOBAL_WORKSPACE_SNAPSHOT = snapshot


def _build_manager(args: argparse.Namespace) -> AbstractSnapshotManager:
    global _GLOBAL_SNAPSHOT_MANAGER

    if _GLOBAL_SNAPSHOT_MANAGER is None:
        _bootstrap_entrypoint_singletons(args)

    if _GLOBAL_SNAPSHOT_MANAGER is None:
        raise RuntimeError("Failed to initialize global SnapshotManager at entry point")

    current_book_name = _resolve_entry_book_name(args)
    if current_book_name:
        _GLOBAL_SNAPSHOT_MANAGER.book_name = current_book_name

    return _GLOBAL_SNAPSHOT_MANAGER


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


def _relative_path_text(path: str | Path) -> str:
    raw_path = Path(path)
    cwd = Path.cwd()
    try:
        return str(raw_path.resolve().relative_to(cwd.resolve()))
    except ValueError:
        return os.path.relpath(str(raw_path), start=str(cwd))


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


def _build_project_settings(args: argparse.Namespace, manager: AbstractSnapshotManager) -> ProjectSettings:
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
    published_path = manager.get_published_path(workspace_root=args.workspace_root, book_name=args.book_name)
    manager.write_text_file(published_path, manager.read_text_file(published_path))

    settings = _build_project_settings(args, manager)
    settings_string = _serialize_project_settings(settings)

    settings_path = manager.get_book_file_path("Settings.json", args.workspace_root, args.book_name)
    manager.write_text_file(settings_path, settings_string)

    snapshot = manager.read_from_workspace(args.workspace_root, args.book_name)
    snapshot.rootFiles["Settings.json"] = settings_string
    snapshot_path = _resolve_snapshot_path(args)
    manager.write_snapshot_json(snapshot, snapshot_path)

    print(f"Structure created at: {book_path}")
    print(f"Settings initialized at: {settings_path}")
    print(f"Publish target initialized at: {published_path}")
    print(f"Snapshot exported: {snapshot_path}")


def run_list(args: argparse.Namespace) -> None:
    _emit_verbose(
        args,
        event="list.start",
        message=f"Listing books under: .pkbook/_workspace",
    )
    manager = _build_manager(args)
    book_names = manager.list_book_names(args.workspace_root)

    if not book_names:
        print(f"No books found in: .pkbook/_workspace")
        return

    print("book_name\tchapter_count")
    for book_name in book_names:
        manager.book_name = book_name
        try:
            settings = manager.load_project_settings()
            chapter_count: int | str = settings.chapter_count
        except (ValueError, OSError, KeyError):
            chapter_count = manager.discover_chapter_numbers()
            chapter_count = len(chapter_count) if chapter_count else "unknown"
        print(f"{book_name}\t{chapter_count}")


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


def _ensure_layout_initialized(args: argparse.Namespace) -> None:
    manager = _build_manager(args)
    settings_path = manager.get_book_file_path("Settings.json", args.workspace_root, args.book_name)

    if manager.path_exists(settings_path):
        if args.chapter_count is None:
            return

        try:
            payload = json.loads(manager.read_text_file(settings_path))
        except (OSError, json.JSONDecodeError):
            payload = {}

        if not isinstance(payload, dict):
            payload = {}

        current_count_raw = payload.get("chapter_count")
        try:
            current_count = int(current_count_raw)
        except (TypeError, ValueError):
            current_count = None

        if current_count == args.chapter_count:
            return

        manager.initialize_workspace(
            workspace_root=args.workspace_root,
            book_name=args.book_name,
            number_of_chapters=args.chapter_count,
        )
        payload["book_name"] = str(payload.get("book_name", args.book_name))
        payload["chapter_count"] = args.chapter_count
        payload["root_folder"] = str(payload.get("root_folder", str(Path(args.workspace_root))))
        payload["date_created"] = str(payload.get("date_created", datetime.now(timezone.utc).isoformat()))
        payload["location"] = str(payload.get("location", platform.node() or "unknown"))
        payload["user"] = str(payload.get("user", os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"))
        manager.write_text_file(settings_path, json.dumps(payload, ensure_ascii=False, indent=2))
        _emit_verbose(
            args,
            event="layout.reconfigure",
            message=f"Updated chapter_count to {args.chapter_count} for '{args.book_name}'",
        )
        return

    settings = _build_project_settings(args, manager)
    manager.initialize_workspace(
        workspace_root=args.workspace_root,
        book_name=args.book_name,
        number_of_chapters=settings.chapter_count,
    )
    manager.write_text_file(settings_path, _serialize_project_settings(settings))
    _emit_verbose(
        args,
        event="layout.autoinit",
        message=f"Auto-initialized missing workspace for '{args.book_name}'",
    )


def run_layout(args: argparse.Namespace) -> None:
    _emit_verbose(args, event="layout.start", message=f"Running layout for '{args.book_name}' in mode '{args.mode}'")
    _ensure_layout_initialized(args)
    if args.mode == "dummy":
        book_path = write_dummy_content(
            workspace_root=args.workspace_root,
            book_name=args.book_name,
            config_path=args.config_path,
            chapter_count=args.chapter_count,
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
        randomize_thoughts=not args.no_randomize_thoughts,
        human_in_loop=args.human_in_loop,
        verbose=args.verbose or args.json,
        json_logs=args.json,
    )
    print(f"Generated content written to: {book_path}")


def run_draft(args: argparse.Namespace) -> None:
    _emit_verbose(
        args,
        event="draft.start",
        message=f"Running draft for '{args.book_name}'",
        extra={"use_cache": not args.no_cache, "chapter_count": args.chapter_count},
    )
    _ensure_layout_initialized(args)
    book_path = write_authored_content(
        workspace_root=args.workspace_root,
        book_name=args.book_name,
        config_path=args.config_path,
        encoding=args.encoding,
        gist=args.gist,
        use_cache=not args.no_cache,
        verbose=args.verbose or args.json,
        json_logs=args.json,
    )
    _emit_verbose(
        args,
        event="draft.done",
        message=f"Draft completed for '{args.book_name}'",
        extra={"path": _relative_path_text(book_path)},
    )
    print(f"Draft chapter outputs written to: {book_path}")


def run_publish(args: argparse.Namespace) -> None:
    _emit_verbose(args, event="publish.start", message=f"Running publish for '{args.book_name}'")
    output_path = publish_book_content(
        workspace_root=args.workspace_root,
        book_name=args.book_name,
        config_path=args.config_path,
        output_path=args.output_path,
        encoding=args.encoding,
        verbose=args.verbose or args.json,
        json_logs=args.json,
    )
    _emit_verbose(
        args,
        event="publish.done",
        message=f"Publish completed for '{args.book_name}'",
        extra={"path": _relative_path_text(output_path)},
    )
    print(f"Published book output: {output_path}")


def run_read(args: argparse.Namespace) -> None:
    manager = _build_manager(args)
    published_path = manager.get_published_path(
        workspace_root=args.workspace_root,
        book_name=args.book_name,
    )
    _emit_verbose(
        args,
        event="read.start",
        message=f"Reading published output for '{args.book_name}'",
        extra={"path": _relative_path_text(published_path)},
    )
    if not manager.path_exists(published_path):
        raise FileNotFoundError(f"Published file not found: {published_path}")

    _print_console_text(manager.read_text_file(published_path))

    _emit_verbose(
        args,
        event="read.done",
        message=f"Read completed for '{args.book_name}'",
    )


def _dispatch_command(args: argparse.Namespace) -> None:
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

    if args.command == "layout":
        run_layout(args)
        return

    if args.command == "draft":
        run_draft(args)
        return

    if args.command == "publish":
        run_publish(args)
        return

    if args.command == "read":
        run_read(args)
        return

    if args.command == "rm":
        run_rm(args)
        return

    if args.command == "purge":
        run_purge(args)
        return

    raise RuntimeError(f"Unsupported command: {args.command}")


def _format_business_error(command: str, error: Exception) -> str:
    command_name = command or "startup"

    if isinstance(error, FileNotFoundError):
        return f"{command_name} failed. Required file or folder was not found. Details: {error}"
    if isinstance(error, json.JSONDecodeError):
        return (
            f"{command_name} failed due to invalid JSON content at line {error.lineno}, "
            f"column {error.colno}."
        )
    if isinstance(error, ModuleNotFoundError):
        return f"{command_name} failed due to missing dependency. Details: {error}"
    if isinstance(error, (ValueError, NotADirectoryError, PermissionError)):
        return f"{command_name} failed. {error}"

    return f"{command_name} failed due to an unexpected error. Use --debug for full traceback."


def run_rm(args: argparse.Namespace) -> None:
    if not args.yes:
        raise ValueError("Refusing to delete without --yes. Example: book.py rm --book-name <name> --yes")

    _emit_verbose(
        args,
        event="rm.start",
        message=f"Removing book '{args.book_name}'",
    )
    manager = _build_manager(args)
    if args.book_name not in manager.list_book_names(args.workspace_root):
        print(f"Book not found: .pkbook/_workspace/{args.book_name}")
        return
    manager.remove_book(args.workspace_root, args.book_name)
    _emit_verbose(args, event="rm.done", message=f"Removed book '{args.book_name}'")
    print(f"Book removed: .pkbook/_workspace/{args.book_name}")


def run_purge(args: argparse.Namespace) -> None:
    if not args.yes:
        raise ValueError("Refusing to purge without --yes. Example: book.py purge --yes")

    _emit_verbose(
        args,
        event="purge.start",
        message="Purging all books under: .pkbook/_workspace",
    )
    manager = _build_manager(args)
    removed_count = manager.purge_workspace(args.workspace_root)
    _emit_verbose(
        args,
        event="purge.done",
        message=f"Purge completed. Removed {removed_count} book(s).",
    )
    print(f"Purge completed. Removed {removed_count} book(s) from: .pkbook/_workspace")


def main() -> None:
    _ensure_config(Path(__file__).resolve().parent)
    args: argparse.Namespace | None = None
    try:
        args = parse_args()
        _bootstrap_entrypoint_singletons(args)
        _dispatch_command(args)
    except KeyboardInterrupt:
        command = args.command if args is not None and hasattr(args, "command") else "command"
        print(f"{command} cancelled by user.")
        raise SystemExit(130)
    except SystemExit:
        raise
    except Exception as error:
        if args is not None and getattr(args, "debug", False):
            raise

        command = args.command if args is not None and hasattr(args, "command") else "startup"
        message = _format_business_error(command, error)
        if args is not None and (args.verbose or args.json):
            _emit_verbose(
                args,
                event=f"{command}.error",
                message=message,
                extra={
                    "error_type": type(error).__name__,
                    "detail": str(error),
                },
            )
        print(message)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
