from __future__ import annotations

import argparse
from pathlib import Path

from snapshot_lib import SnapshotManager


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(
        prog="init.py",
        description="Create book folder/file structure from init.json template.",
        epilog=(
            "Examples:\n"
            "  python init.py --book-name Ramayan\n"
            "  python init.py --book-name Sita --workspace-root .\\_workspace\n"
            "  python init.py --book-name Demo --config-path .\\init.json"
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--workspace-root",
        default=str(script_dir / "_workspace"),
        help="Optional. Root directory where the book folder will be created.",
    )
    parser.add_argument(
        "--book-name",
        required=True,
        help="Mandatory. Book folder name to create under workspace root.",
    )
    parser.add_argument(
        "--config-path",
        default=str(script_dir / "init.json"),
        help="Optional. Path to JSON config template.",
    )

    return parser.parse_args()

def main() -> None:
    args = parse_args()

    workspace_root = Path(args.workspace_root)
    book_name = args.book_name
    manager = SnapshotManager.from_config_file(args.config_path)
    book_path = manager.initialize_workspace(workspace_root=workspace_root, book_name=book_name)

    print(f"Structure created at: {book_path}")


if __name__ == "__main__":
    main()
