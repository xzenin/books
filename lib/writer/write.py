from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .agents import (
    BookLayout,
    DraftChapterSegment,
    GenerateChapterSegment,
    LayoutChapter,
    RefinetChapter,
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
from .prompt_builders import (
    build_author_prompt,
    build_chapter_prompt,
    build_novel_prompt,
    build_segment_prompt,
)


def _resolve_provider_instance(mapping: dict[str, str], level_key: str) -> str | None:
    return mapping.get(level_key.strip().lower()) or mapping.get("default")


def _build_runtime_state(manager: Any) -> RuntimeWorkspaceState:
    snapshot = manager.read_from_workspace()
    return RuntimeWorkspaceState(snapshot=snapshot)


def _record_runtime_write(
    runtime_state: RuntimeWorkspaceState,
    path: str | Path,
    content: str,
    *,
    chapter_number: int | None = None,
    is_out_file: bool = False,
    entry_name: str | None = None,
) -> None:
    if chapter_number is None:
        runtime_state.snapshot.set_root_file(Path(path).name, content)
    else:
        file_key = entry_name or Path(path).name
        if is_out_file:
            runtime_state.snapshot.set_chapter_out_file(chapter_number, file_key, content)
        else:
            runtime_state.snapshot.set_chapter_file(chapter_number, file_key, content)
    runtime_state.mark_dirty(path)
    runtime_state.bump_version()


def _write_text_with_runtime(
    manager: Any,
    runtime_state: RuntimeWorkspaceState,
    path: str | Path,
    content: str,
    *,
    chapter_number: int | None = None,
    is_out_file: bool = False,
    entry_name: str | None = None,
) -> None:
    manager.write_text_file(path, content)
    _record_runtime_write(
        runtime_state,
        path,
        content,
        chapter_number=chapter_number,
        is_out_file=is_out_file,
        entry_name=entry_name,
    )


def _write_json_with_runtime(
    manager: Any,
    runtime_state: RuntimeWorkspaceState,
    path: str | Path,
    payload: Any,
    *,
    chapter_number: int | None = None,
    is_out_file: bool = False,
    entry_name: str | None = None,
) -> None:
    manager.write_json_file(path, payload)
    serialised = json.dumps(payload, ensure_ascii=False, indent=2)
    _record_runtime_write(
        runtime_state,
        path,
        serialised,
        chapter_number=chapter_number,
        is_out_file=is_out_file,
        entry_name=entry_name,
    )



def write_dummy_content(
    *,
    workspace_root: str | Path,
    book_name: str,
    config_path: str | Path,
    chapter_count: int | None = None,
    encoding: str = "utf-8",
    content_provider: Callable[[Path], Any] | None = None,
    verbose: bool = False,
    json_logs: bool = False,
) -> Path:
    config = SnapshotConfig.from_json_file(config_path)
    manager = build_snapshot_manager(
        config,
        workspace_root=workspace_root,
        book_name=book_name,
        encoding=encoding,
        verbose=verbose,
        json_logs=json_logs,
    )
    book_path = manager.initialize_workspace(number_of_chapters=chapter_count)
    verbose_print(
        verbose,
        json_logs,
        f"Writing dummy content under: {relative_path_text(book_path)}",
        "dummy.start",
    )

    provider = content_provider or prompt_content_for_file

    for path in manager.iter_configured_files():
        content = provider(path)
        manager.write_dummy_file(path, content)

    verbose_print(verbose, json_logs, f"Dummy content write completed for: {book_name}", "dummy.done")

    return book_path


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
    config = SnapshotConfig.from_json_file(config_path)
    manager = build_snapshot_manager(
        config,
        workspace_root=workspace_root,
        book_name=book_name,
        encoding=encoding,
        verbose=verbose,
        json_logs=json_logs,
    )
    genai_mapping = manager.load_genai_mapping()
    book_path = manager.get_book_path()
    book_history_root = book_path

    settings = manager.load_project_settings()
    verbose_print(
        verbose,
        json_logs,
        f"Loaded Settings.json for {settings.book_name} with chapter_count={settings.chapter_count}",
        "settings.loaded",
    )
    manager.initialize_workspace(
        number_of_chapters=settings.chapter_count,
    )
    runtime_state = _build_runtime_state(manager)
    novel_gist = gist.strip() if gist else prompt_for_gist(book_name)
    if not novel_gist:
        raise ValueError("Novel gist is required.")

    novel_template = manager.load_template_payload("book.json")
    chapter_template = manager.load_template_payload("chapter.json")
    segment_template = manager.load_template_payload("segment.json")
    verbose_print(verbose, json_logs, "Loaded book, chapter, and segment JSON templates", "templates.loaded")

    book_provider = _resolve_provider_instance(genai_mapping, "book_level_generation")
    book_layout_agent = BookLayout(
        book_name=book_name,
        history_root=book_history_root,
        use_cache=use_cache,
        verbose=verbose,
        json_logs=json_logs,
        call_genai=call_genai,
        extract_json_payload=extract_json_payload,
        agent_name="BookLayout",
        provider_instance_name=book_provider,
    )
    chapter_refiner = RefinetChapter(
        randomize_thoughts=randomize_thoughts,
        human_in_loop=human_in_loop,
    )
    chapter_layout_agent = LayoutChapter(
        book_name=book_name,
        use_cache=use_cache,
        verbose=verbose,
        json_logs=json_logs,
        call_genai=call_genai,
        extract_json_payload=extract_json_payload,
        agent_name="LayoutChapter",
        provider_instance_name=None,  # Will be set per chapter
    )
    segment_prompt_agent = DraftChapterSegment(encoding=encoding, manager=manager)
    segment_generate_agent = GenerateChapterSegment(
        book_name=book_name,
        use_cache=use_cache,
        verbose=verbose,
        json_logs=json_logs,
        call_genai=call_genai,
        extract_json_payload=extract_json_payload,
        agent_name="GenerateChapterSegment",
        provider_instance_name=None,  # Will be set per segment
    )

    base_book_prompt = build_novel_prompt(settings=settings, gist=novel_gist, template_payload=novel_template)
    book_prompt, outline_payload = book_layout_agent.create_master_plan(base_prompt=base_book_prompt)
    book_prompt_path = manager.get_book_prompt_path()
    _write_text_with_runtime(manager, runtime_state, book_prompt_path, book_prompt)
    verbose_print(
        verbose,
        json_logs,
        f"Saved novel prompt to: {relative_path_text(book_prompt_path)}",
        "prompt.novel.saved",
    )

    outline_path = manager.get_outline_path()
    _write_json_with_runtime(manager, runtime_state, outline_path, outline_payload)
    verbose_print(
        verbose,
        json_logs,
        f"Saved novel outline to: {relative_path_text(outline_path)}",
        "outline.saved",
    )

    chapters = outline_payload.get("chapters", [])
    if not isinstance(chapters, list):
        raise ValueError("BookOutline.json must contain a chapters array.")

    sorted_chapters = sorted(
        (chapter for chapter in chapters if isinstance(chapter, dict)),
        key=lambda chapter: chapter_sort_key(chapter, 0),
    )
    verbose_print(
        verbose,
        json_logs,
        f"Generating chapter prompts and parameters for {len(sorted_chapters)} chapters",
        "chapters.start",
    )

    for fallback_index, chapter_payload in enumerate(sorted_chapters, start=1):
        chapter_number = chapter_sort_key(chapter_payload, fallback_index)
        chapter_payload = normalize_chapter_payload(chapter_payload, chapter_number)
        chapter_root = manager.get_chapter_path(chapter_number)
        prompt_path, parameter_path = manager.get_chapter_file_paths(chapter_number)
        manager.ensure_dir(chapter_root)
        chapter_history_root = manager.get_chapter_path(chapter_number)

        # Extract book_summary and chapter_summary as plain text
        book_summary = outline_payload.get("running_summary", "")
        chapter_summary = chapter_payload.get("chapter_summary", "")
        # If they are dicts, rationalize to text
        if isinstance(book_summary, dict):
            book_summary = book_summary.get("running_summary", "")
        if isinstance(chapter_summary, dict):
            chapter_summary = chapter_summary.get("chapter_summary", "")
        chapter_prompt = build_chapter_prompt(
            settings=settings,
            book_gist=novel_gist,
            book_summary=book_summary,
            chapter_summary=chapter_summary,
            chapter_payload=chapter_payload,
            chapter_template_json=chapter_template,
            encoding=encoding,
        )
        _write_text_with_runtime(
            manager,
            runtime_state,
            prompt_path,
            chapter_prompt,
            chapter_number=chapter_number,
        )
        verbose_print(
            verbose,
            json_logs,
            f"Saved chapter {chapter_number} prompt to: {relative_path_text(prompt_path)}",
            "prompt.chapter.saved",
        )

        refined_payload = chapter_refiner.refine_chapter_context(
            chapter_payload=chapter_payload,
            chapter_number=chapter_number,
        )

        chapter_provider = _resolve_provider_instance(genai_mapping, "chapter_level_generation")
        chapter_layout_agent.provider_instance_name = chapter_provider
        layout_prompt, segments = chapter_layout_agent.create_segment_layout(
            chapter_number=chapter_number,
            chapter_payload=refined_payload,
            outline_payload=outline_payload,
            history_root=chapter_history_root,
        )
        layout_prompt_path = manager.get_chapter_layout_prompt_path(chapter_number)
        _write_text_with_runtime(
            manager,
            runtime_state,
            layout_prompt_path,
            layout_prompt + "\n",
            chapter_number=chapter_number,
            is_out_file=True,
        )

        drafted_segments = segment_prompt_agent.draft_segment_prompts(
            settings=settings,
            gist=novel_gist,
            chapter_number=chapter_number,
            outline_payload=outline_payload,
            chapter_payload=refined_payload,
            segments=segments,
            template_payload=segment_template,
        )
        segment_provider = _resolve_provider_instance(genai_mapping, "segment_level_generation")
        segment_generate_agent.provider_instance_name = segment_provider
        generated_segments = segment_generate_agent.generate_segment_content(
            chapter_number=chapter_number,
            chapter_root=chapter_root,
            drafted_segments=drafted_segments,
            segment_history_roots={
                int(item.index): manager.get_segment_path(chapter_number, int(item.index))
                for item in drafted_segments
            },
        )
        chapter_segment_payloads: list[dict[str, str]] = []
        chapter_generated_path = manager.get_chapter_generated_path(chapter_number)
        _write_text_with_runtime(
            manager,
            runtime_state,
            chapter_generated_path,
            "",
            chapter_number=chapter_number,
            is_out_file=True,
        )

        # Persist segment artifacts in the configured Segment{s} structure.
        for drafted_item in drafted_segments:
            segment_index = int(drafted_item.index)
            segment_root, segment_parameter_path, segment_prompt_path, segment_generated_path = manager.get_segment_structured_paths(
                chapter_number,
                segment_index,
            )
            manager.ensure_dir(segment_root)

            if segment_prompt_path is not None:
                _write_text_with_runtime(
                    manager,
                    runtime_state,
                    segment_prompt_path,
                    drafted_item.prompt + "\n",
                    chapter_number=chapter_number,
                    is_out_file=True,
                    entry_name=f"segment-{segment_index}/{Path(segment_prompt_path).name}",
                )

            generated_item = next(
                (
                    item
                    for item in generated_segments
                    if item.section == f"segment-{segment_index}"
                ),
                None,
            )
            generated_text = "" if generated_item is None else generated_item.text
            chapter_segment_payloads.append(
                {
                    "segment_title": str(drafted_item.segment.name).strip() or f"segment-{segment_index}",
                    "goal": drafted_item.segment.goal,
                    "stakes": drafted_item.segment.stakes,
                    "vulnerability": drafted_item.segment.vulnerability,
                    "conflict": drafted_item.segment.conflict,
                    "tension": drafted_item.segment.tension,
                    "rationalize": drafted_item.segment.rationalize,
                    "subversion": drafted_item.segment.subversion,
                    "catharsis": drafted_item.segment.catharsis,
                    "segment_text": generated_text,
                }
            )

            if segment_parameter_path is not None:
                parameter_payload = {
                    "segment_index": segment_index,
                    "name": drafted_item.segment.name,
                    "goal": drafted_item.segment.goal,
                    "stakes": drafted_item.segment.stakes,
                    "vulnerability": drafted_item.segment.vulnerability,
                    "conflict": drafted_item.segment.conflict,
                    "tension": drafted_item.segment.tension,
                    "rationalize": drafted_item.segment.rationalize,
                    "subversion": drafted_item.segment.subversion,
                    "catharsis": drafted_item.segment.catharsis,
                    "generated_text": generated_text,
                }
                _write_json_with_runtime(
                    manager,
                    runtime_state,
                    segment_parameter_path,
                    parameter_payload,
                    chapter_number=chapter_number,
                    is_out_file=True,
                    entry_name=f"segment-{segment_index}/{Path(segment_parameter_path).name}",
                )

            if segment_generated_path is not None and generated_item is not None:
                _write_text_with_runtime(
                    manager,
                    runtime_state,
                    segment_generated_path,
                    generated_item.text + "\n",
                    chapter_number=chapter_number,
                    is_out_file=True,
                    entry_name=f"segment-{segment_index}/{Path(segment_generated_path).name}",
                )
                try:
                    existing_chapter_generated = manager.read_text_file(chapter_generated_path).strip()
                except OSError:
                    existing_chapter_generated = ""

                segment_title = str(drafted_item.segment.name).strip() or f"segment-{segment_index}"
                segment_text = generated_item.text.strip()
                segment_block = f"Segment Title: {segment_title}\n{segment_text}".strip()
                if existing_chapter_generated:
                    appended_chapter_generated = f"{existing_chapter_generated}\n\n{segment_block}".strip()
                else:
                    appended_chapter_generated = segment_block

                _write_text_with_runtime(
                    manager,
                    runtime_state,
                    chapter_generated_path,
                    appended_chapter_generated + ("\n" if appended_chapter_generated else ""),
                    chapter_number=chapter_number,
                    is_out_file=True,
                )

        chapter_json = dict(refined_payload)
        chapter_json["chapter_segments"] = chapter_segment_payloads
        chapter_json = normalize_chapter_payload(chapter_json, chapter_number)
        _write_json_with_runtime(
            manager,
            runtime_state,
            parameter_path,
            chapter_json,
            chapter_number=chapter_number,
        )
        verbose_print(
            verbose,
            json_logs,
            f"Saved chapter {chapter_number} parameters to: {relative_path_text(parameter_path)}",
            "chapter.parameters.saved",
        )

    verbose_print(verbose, json_logs, f"Generated content write completed for: {book_name}", "generated.done")
    return book_path


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
    config = SnapshotConfig.from_json_file(config_path)
    manager = build_snapshot_manager(
        config,
        workspace_root=workspace_root,
        book_name=book_name,
        encoding=encoding,
        verbose=verbose,
        json_logs=json_logs,
    )
    genai_mapping = manager.load_genai_mapping()
    book_path = manager.get_book_path()

    settings = manager.load_project_settings()
    manager.initialize_workspace(
        number_of_chapters=settings.chapter_count,
    )
    runtime_state = _build_runtime_state(manager)

    outline_path = manager.get_outline_path()
    running_summary_path = manager.get_book_file_path("BookRunningSummary.txt")
    outline_payload: dict[str, Any]
    chapters: list[dict[str, Any]]

    if manager.path_exists(outline_path):
        try:
            loaded_outline = manager.load_json_file(outline_path)
        except (ValueError, OSError):
            loaded_outline = {}
    else:
        loaded_outline = {}

    if isinstance(loaded_outline, dict) and isinstance(loaded_outline.get("chapters", []), list):
        outline_payload = loaded_outline
        chapters = [item for item in loaded_outline.get("chapters", []) if isinstance(item, dict)]
    else:
        chapter_numbers = manager.discover_chapter_numbers()
        chapters = [
            normalize_chapter_payload(
                {
                    "sl": number,
                    "name": f"Chapter {number}",
                    "chapter_title": f"Chapter {number}",
                    "chapter_summary": "",
                    "chapter_segments": [],
                },
                number,
            )
            for number in chapter_numbers
        ]
        outline_payload = {
            "novel_name": book_name,
            "chapters": chapters,
            "running_summary": "",
            "all_characters": [],
        }
        verbose_print(
            verbose,
            json_logs,
            f"BookOutline.json missing/invalid. Falling back to discovered chapter folders for: {book_name}",
            "draft.outline.fallback",
        )

    if not chapters:
        raise ValueError(
            f"No chapters found for draft under: {manager.get_chapter_root()}. "
            "Run layout first to generate chapter structure."
        )

    novel_gist = (gist or str(outline_payload.get("gist", "")).strip() or prompt_for_gist(book_name)).strip()
    if not novel_gist:
        raise ValueError("Novel gist is required for draft command.")

    sorted_chapters = sorted(
        (chapter for chapter in chapters if isinstance(chapter, dict)),
        key=lambda chapter: chapter_sort_key(chapter, 0),
    )
    verbose_print(
        verbose,
        json_logs,
        f"Drafting {len(sorted_chapters)} chapters for: {book_name} (cache={'on' if use_cache else 'off'})",
        "draft.start",
    )

    for fallback_index, chapter_payload in enumerate(sorted_chapters, start=1):
        chapter_number = chapter_sort_key(chapter_payload, fallback_index)
        chapter_payload = normalize_chapter_payload(chapter_payload, chapter_number)
        chapter_root = manager.get_chapter_path(chapter_number)
        _, parameter_path = manager.get_chapter_file_paths(chapter_number)
        chapter_history_root = manager.get_chapter_path(chapter_number)
        out_path = manager.get_chapter_out_path(chapter_number)
        manager.ensure_dir(out_path)

        if manager.path_exists(parameter_path):
            try:
                chapter_parameter_payload = manager.load_json_file(parameter_path)
            except (ValueError, OSError):
                chapter_parameter_payload = chapter_payload
            if not isinstance(chapter_parameter_payload, dict):
                chapter_parameter_payload = chapter_payload
            chapter_parameter_payload = normalize_chapter_payload(chapter_parameter_payload, chapter_number)
        else:
            chapter_parameter_payload = chapter_payload

        previous_running_summary = str(outline_payload.get("running_summary", "")).strip()
        verbose_print(
            verbose,
            json_logs,
            f"Drafting chapter {chapter_number} using context: {relative_path_text(parameter_path)}",
            "draft.chapter.start",
        )
        chapter_sections = chapter_parameter_payload.get("chapter_segments", [])
        if not isinstance(chapter_sections, list) or not chapter_sections:
            chapter_sections = chapter_payload.get("chapter_segments", [])
        if not isinstance(chapter_sections, list) or not chapter_sections:
            chapter_sections = [{"segment_title": "segment-1", "segment_text": ""}]

        aggregated_section_texts: list[str] = []
        aggregated_segments: list[dict[str, str]] = []
        aggregated_characters: list[dict[str, str]] = []
        chapter_title = str(chapter_payload.get("chapter_title", "")).strip() or f"Chapter {chapter_number}"
        chapter_summary_parts: list[str] = []
        next_running_summary = previous_running_summary

        for section_index, section_payload in enumerate(chapter_sections, start=1):
            if isinstance(section_payload, dict):
                section_name = str(
                    section_payload.get(
                        "segment_title",
                        section_payload.get("section-title", section_payload.get("section", f"segment-{section_index}")),
                    )
                ).strip() or f"segment-{section_index}"
                section_seed_text = str(section_payload.get("segment_text", section_payload.get("text", ""))).strip()
            else:
                section_name = f"segment-{section_index}"
                section_seed_text = str(section_payload).strip()

            section_chapter_payload = dict(chapter_payload)
            section_chapter_payload["chapter_segments"] = [{"segment_title": section_name, "segment_text": section_seed_text}]

            section_parameter_payload = dict(chapter_parameter_payload)
            section_parameter_payload["chapter_segments"] = [{"segment_title": section_name, "segment_text": section_seed_text}]

            prompt = build_author_prompt(
                settings=settings,
                gist=novel_gist,
                outline_payload=outline_payload,
                chapter_payload=section_chapter_payload,
                chapter_parameter_payload=section_parameter_payload,
                chapter_number=chapter_number,
                previous_running_summary=next_running_summary,
            )
            response = call_genai(
                prompt,
                conversation_id=f"{book_name}-draft-chapter-{chapter_number}-section-{section_index}",
                use_cache=use_cache,
                history_root=chapter_history_root,
                agent_name="DraftAuthor",
                verbose=verbose,
                json_logs=json_logs,
                provider_instance_name=_resolve_provider_instance(genai_mapping, "chapter_level_generation"),
            )
            author_payload_raw = extract_json_payload(response)
            if not isinstance(author_payload_raw, dict):
                raise ValueError(
                    f"Draft response for chapter {chapter_number} section {section_index} must be a JSON object."
                )
            author_payload = normalize_author_payload(author_payload_raw)

            section_text = author_payload["chapter_text"].strip()
            if section_text:
                aggregated_section_texts.append(section_text)
                aggregated_segments.append(
                    {
                        "segment_title": section_name,
                        "segment_text": section_text,
                    }
                )

            if author_payload["chapter_title"].strip():
                chapter_title = author_payload["chapter_title"].strip()

            summary_text = author_payload["chapter_summary"].strip()
            if summary_text:
                chapter_summary_parts.append(summary_text)

            next_running_summary = author_payload["next_running_summary"].strip() or next_running_summary
            aggregated_characters.extend(author_payload["next_characters"])

            verbose_print(
                verbose,
                json_logs,
                f"Drafted chapter {chapter_number} section {section_index}: {section_name}",
                "draft.chapter.section.done",
            )

        chapter_text = "\n\n".join(part for part in aggregated_section_texts if part).strip()
        chapter_summary = "\n".join(dict.fromkeys(part for part in chapter_summary_parts if part)).strip()
        next_characters = aggregated_characters

        generated_text = f"{chapter_text}".strip() + "\n"
        chapter_generated_path = manager.get_chapter_generated_path(chapter_number)
        chapter_summary_path = manager.get_chapter_summary_path(chapter_number)
        chapter_character_path = manager.get_chapter_character_path(chapter_number)

        _write_text_with_runtime(
            manager,
            runtime_state,
            chapter_generated_path,
            generated_text,
            chapter_number=chapter_number,
            is_out_file=True,
        )
        _write_text_with_runtime(
            manager,
            runtime_state,
            chapter_summary_path,
            chapter_summary + "\n",
            chapter_number=chapter_number,
            is_out_file=True,
        )
        character_text = render_character_text(next_characters)
        _write_text_with_runtime(
            manager,
            runtime_state,
            chapter_character_path,
            character_text,
            chapter_number=chapter_number,
            is_out_file=True,
        )

        verbose_print(
            verbose,
            json_logs,
            (
                f"Wrote chapter {chapter_number} outputs: "
                f"{relative_path_text(chapter_generated_path)}, "
                f"{relative_path_text(chapter_summary_path)}, "
                f"{relative_path_text(chapter_character_path)}"
            ),
            "draft.chapter.files",
        )

        chapter_payload["chapter_title"] = chapter_title
        chapter_payload["chapter_summary"] = chapter_summary
        chapter_payload["chapter_segments"] = aggregated_segments
        outline_payload["running_summary"] = next_running_summary
        try:
            existing_running_summary = manager.read_text_file(running_summary_path).strip()
        except OSError:
            existing_running_summary = ""

        chapter_running_block = f"Chapter {chapter_number}:\n{next_running_summary}".strip()
        if existing_running_summary:
            appended_running_summary = f"{existing_running_summary}\n\n{chapter_running_block}".strip()
        else:
            appended_running_summary = chapter_running_block

        _write_text_with_runtime(
            manager,
            runtime_state,
            running_summary_path,
            appended_running_summary + ("\n" if appended_running_summary else ""),
        )
        extend_outline_characters(outline_payload, next_characters)

        verbose_print(
            verbose,
            json_logs,
            f"Drafted chapter {chapter_number}: {relative_path_text(chapter_generated_path)}",
            "draft.chapter.done",
        )

    _write_json_with_runtime(manager, runtime_state, outline_path, outline_payload)
    verbose_print(
        verbose,
        json_logs,
        f"Updated running summary and characters in: {relative_path_text(outline_path)}",
        "draft.outline.updated",
    )
    verbose_print(verbose, json_logs, f"Draft command completed for: {book_name}", "draft.done")
    return book_path


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
    config = SnapshotConfig.from_json_file(config_path)
    manager = build_snapshot_manager(
        config,
        workspace_root=workspace_root,
        book_name=book_name,
        encoding=encoding,
        verbose=verbose,
        json_logs=json_logs,
    )
    book_path = manager.get_book_path()
    outline_path = manager.get_outline_path()

    published_path = manager.get_published_path(output_path)
    manager.ensure_dir(published_path.parent)

    chapter_numbers: list[int] = []
    chapter_titles: dict[int, str] = {}

    if manager.path_exists(outline_path):
        try:
            outline_payload = manager.load_json_file(outline_path)
            if isinstance(outline_payload, dict) and isinstance(outline_payload.get("chapters", []), list):
                chapters = outline_payload.get("chapters", [])
                sorted_chapters = sorted(
                    (chapter for chapter in chapters if isinstance(chapter, dict)),
                    key=lambda chapter: chapter_sort_key(chapter, 0),
                )
                chapter_numbers = [chapter_sort_key(chapter, index) for index, chapter in enumerate(sorted_chapters, start=1)]
                chapter_titles = {
                    chapter_sort_key(chapter, index): str(chapter.get("chapter_title", "")).strip()
                    for index, chapter in enumerate(sorted_chapters, start=1)
                    if isinstance(chapter, dict)
                }
            else:
                verbose_print(
                    verbose,
                    json_logs,
                    f"BookOutline.json is not in expected shape. Falling back to chapter folders under: {relative_path_text(manager.get_chapter_root())}",
                    "publish.outline.fallback",
                )
        except (ValueError, OSError):
            verbose_print(
                verbose,
                json_logs,
                f"BookOutline.json is empty/invalid. Falling back to chapter folders under: {relative_path_text(manager.get_chapter_root())}",
                "publish.outline.fallback",
            )

    if not chapter_numbers:
        chapter_numbers = manager.discover_chapter_numbers()

    if not chapter_numbers:
        raise ValueError(
            f"No chapters found to publish under: {manager.get_chapter_root()}. "
            "Run layout/draft first to generate chapter content."
        )

    verbose_print(
        verbose,
        json_logs,
        f"Publishing {len(chapter_numbers)} chapters into: {relative_path_text(published_path)}",
        "publish.start",
    )

    chunks: list[str] = []
    for chapter_number in chapter_numbers:
        generated_path = manager.get_chapter_generated_path(chapter_number)
        if not manager.path_exists(generated_path):
            raise FileNotFoundError(f"Generated chapter content not found: {generated_path}")

        chapter_title = chapter_titles.get(chapter_number, "")
        heading = chapter_title or f"Chapter {chapter_number}"
        content = manager.read_text_file(generated_path).strip()
        chunks.append(f"Chapter {chapter_number}\n\n{heading}\n\n{content}\n===========================\n\n")
        verbose_print(
            verbose,
            json_logs,
            f"Included chapter {chapter_number} from: {relative_path_text(generated_path)}",
            "publish.chapter.appended",
        )

    manager.write_text_file(published_path, "\n\n".join(chunks).strip() + "\n")
    verbose_print(
        verbose,
        json_logs,
        f"Published manuscript written to: {relative_path_text(published_path)}",
        "publish.done",
    )
    return published_path
