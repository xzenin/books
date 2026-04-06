
# All provider resolution, runtime state, and write helpers are now in AuthorAssistant.
# Use AuthorAssistant for all logic related to provider selection, runtime state management, and writing with runtime tracking.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .agents.crew_agents import (
    BookLayout,
    RefinetChapter,
    LayoutChapter,
    DraftChapterSegment,
    GenerateChapterSegment,
)
from .chapter_normalizers import (
    chapter_sort_key,
    extend_outline_characters,
    normalize_author_payload,
    normalize_chapter_payload,
    render_character_text,
)
from ..io.io_helpers import (
    call_genai,
    extract_json_payload,
    prompt_content_for_file,
    prompt_for_gist,
    relative_path_text,
    verbose_print,
)
from lib.io import build_snapshot_manager
from lib.models import RuntimeWorkspaceState, SnapshotConfig




from .author_assistant import AuthorAssistant



def write_dummy_content(*, workspace_root: str | Path, book_name: str, config_path: str | Path, chapter_count: int | None = None, encoding: str = "utf-8", content_provider: Callable[[Path], Any] | None = None, verbose: bool = False, json_logs: bool = False) -> Path:
    """
    Orchestrator: delegates to AuthorAssistant.write_dummy_content
    """
    from .author_assistant import AuthorAssistant
    return AuthorAssistant.write_dummy_content(
        workspace_root=workspace_root,
        book_name=book_name,
        config_path=config_path,
        chapter_count=chapter_count,
        encoding=encoding,
        content_provider=content_provider,
        verbose=verbose,
        json_logs=json_logs,
    )


def write_generated_content(
    *,
    workspace_root: str | Path,
    book_name: str,
    config_path: str | Path,
    encoding: str = "utf-8",
    gist: str | None = None,
    use_cache: bool = True,
    randomize_thoughts: bool = True,
    human_in_loop: bool = False,
    verbose: bool = False,
    json_logs: bool = False,
) -> Path:
    # Delegate to AuthorAssistant for all logic
    return AuthorAssistant.write_generated_content(
        workspace_root=workspace_root,
        book_name=book_name,
        config_path=config_path,
        encoding=encoding,
        gist=gist,
        use_cache=use_cache,
        randomize_thoughts=randomize_thoughts,
        human_in_loop=human_in_loop,
        verbose=verbose,
        json_logs=json_logs,
    )


def write_authored_content(
    *,
    workspace_root: str | Path,
    book_name: str,
    config_path: str | Path,
    encoding: str = "utf-8",
    gist: str | None = None,
    use_cache: bool = True,
    verbose: bool = False,
    json_logs: bool = False,
) -> Path:
    # Delegate to AuthorAssistant for all logic
    return AuthorAssistant.write_authored_content(
        workspace_root=workspace_root,
        book_name=book_name,
        config_path=config_path,
        encoding=encoding,
        gist=gist,
        use_cache=use_cache,
        verbose=verbose,
        json_logs=json_logs,
    )


def publish_book_content(
    *,
    workspace_root: str | Path,
    book_name: str,
    config_path: str | Path,
    output_path: str | Path | None = None,
    encoding: str = "utf-8",
    verbose: bool = False,
    json_logs: bool = False,
) -> Path:
    # Delegate to AuthorAssistant for all logic
    return AuthorAssistant.publish_book_content(
        workspace_root=workspace_root,
        book_name=book_name,
        config_path=config_path,
        output_path=output_path,
        encoding=encoding,
        verbose=verbose,
        json_logs=json_logs,
    )
