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
    chapter_paths,
    chapter_sort_key,
    chapter_text_to_sections,
    chapter_texts_to_text,
    discover_chapter_numbers_from_workspace,
    extend_outline_characters,
    iter_configured_files,
    normalize_author_payload,
    normalize_chapter_payload,
    render_character_text,
    segment_paths,
)
from .io_helpers import (
    call_genai,
    extract_json_payload,
    load_json_file,
    load_project_settings,
    prompt_content_for_file,
    prompt_for_gist,
    read_text,
    relative_path_text,
    verbose_print,
    write_dummy_file,
    write_json,
    write_text,
)
from .manager import SnapshotManager
from .models import SnapshotConfig
from .prompt_builders import (
    build_author_prompt,
    build_chapter_prompt,
    build_novel_prompt,
    load_template_payload,
)


def _load_genai_mapping() -> dict[str, str]:
    """Load provider-instance mapping from .pkbook/config.json."""
    config_path = Path(__file__).resolve().parents[2] / ".pkbook" / "config.json"
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(payload, dict):
        return {}
    genai_cfg = payload.get("genai", {})
    if not isinstance(genai_cfg, dict):
        return {}
    mapping = genai_cfg.get("mapping", {})
    if not isinstance(mapping, dict):
        return {}

    normalized: dict[str, str] = {}
    for key, value in mapping.items():
        if isinstance(key, str) and isinstance(value, str):
            normalized[key.strip().lower()] = value.strip()
    return normalized


def _resolve_provider_instance(mapping: dict[str, str], level_key: str) -> str | None:
    return mapping.get(level_key.strip().lower()) or mapping.get("default")



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
    manager = SnapshotManager(config, encoding=encoding, verbose=verbose, json_logs=json_logs)
    book_path = manager.initialize_workspace(workspace_root, book_name, number_of_chapters=chapter_count)
    verbose_print(
        verbose,
        json_logs,
        f"Writing dummy content under: {relative_path_text(book_path)}",
        "dummy.start",
    )

    provider = content_provider or prompt_content_for_file

    for path in iter_configured_files(book_path, config):
        content = provider(path)
        write_dummy_file(path, content, encoding=encoding)

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
    genai_mapping = _load_genai_mapping()
    manager = SnapshotManager(
        config,
        workspace_root=workspace_root,
        book_name=book_name,
        encoding=encoding,
        verbose=verbose,
        json_logs=json_logs,
    )
    book_path = manager.get_book_path()
    book_history_root = book_path

    settings = load_project_settings(book_path, encoding=encoding)
    verbose_print(
        verbose,
        json_logs,
        f"Loaded Settings.json for {settings.book_name} with chapter_count={settings.chapter_count}",
        "settings.loaded",
    )
    manager.initialize_workspace(
        number_of_chapters=settings.chapter_count,
    )
    novel_gist = gist.strip() if gist else prompt_for_gist(book_name)
    if not novel_gist:
        raise ValueError("Novel gist is required.")

    novel_template = load_template_payload("book.json", encoding=encoding)
    chapter_template = load_template_payload("chapter.json", encoding=encoding)
    verbose_print(verbose, json_logs, "Loaded book and chapter JSON templates", "templates.loaded")

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
    segment_prompt_agent = DraftChapterSegment(encoding=encoding)
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
    book_prompt_path = book_path / "BookPrompt.txt"
    write_text(book_prompt_path, book_prompt, encoding=encoding)
    verbose_print(
        verbose,
        json_logs,
        f"Saved novel prompt to: {relative_path_text(book_prompt_path)}",
        "prompt.novel.saved",
    )

    outline_path = book_path / "BookOutline.json"
    write_json(outline_path, outline_payload, encoding=encoding)
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
        chapter_root, prompt_path, parameter_path = chapter_paths(book_path, config, chapter_number)
        chapter_root.mkdir(parents=True, exist_ok=True)
        chapter_history_root = manager.get_chapter_path(chapter_number)

        chapter_prompt = build_chapter_prompt(
            settings=settings,
            gist=novel_gist,
            outline_payload=outline_payload,
            chapter_payload=chapter_payload,
            template_payload=chapter_template,
            encoding=encoding,
        )
        write_text(prompt_path, chapter_prompt, encoding=encoding)
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
        layout_prompt_path = chapter_root / "ChapterLayoutPrompt.txt"
        write_text(layout_prompt_path, layout_prompt + "\n", encoding=encoding)

        drafted_segments = segment_prompt_agent.draft_segment_prompts(
            chapter_number=chapter_number,
            chapter_root=chapter_root,
            chapter_payload=refined_payload,
            segments=segments,
        )
        segment_provider = _resolve_provider_instance(genai_mapping, "segment_level_generation")
        segment_generate_agent.provider_instance_name = segment_provider
        chapter_texts = segment_generate_agent.generate_segment_content(
            chapter_number=chapter_number,
            chapter_root=chapter_root,
            drafted_segments=drafted_segments,
            segment_history_roots={
                int(item.index): manager.get_segment_path(chapter_number, int(item.index))
                for item in drafted_segments
            },
        )

        # Persist segment artifacts in the configured Segment{s} structure.
        for drafted_item in drafted_segments:
            segment_index = int(drafted_item.index)
            segment_root, segment_parameter_path, segment_prompt_path, segment_generated_path = segment_paths(
                chapter_root,
                config,
                chapter_number,
                segment_index,
            )
            segment_root.mkdir(parents=True, exist_ok=True)

            if segment_prompt_path is not None:
                write_text(segment_prompt_path, drafted_item.prompt + "\n", encoding=encoding)

            generated_item = next(
                (
                    item
                    for item in chapter_texts
                    if item.section == f"segment-{segment_index}"
                ),
                None,
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
                    "generated_text": "" if generated_item is None else generated_item.text,
                }
                write_json(segment_parameter_path, parameter_payload, encoding=encoding)

            if segment_generated_path is not None and generated_item is not None:
                write_text(segment_generated_path, generated_item.text + "\n", encoding=encoding)

        chapter_text_dicts = [item.to_dict() for item in chapter_texts]

        chapter_json = dict(refined_payload)
        chapter_json["chapter_texts"] = chapter_text_dicts
        chapter_json["chapter_text"] = chapter_texts_to_text(chapter_texts)
        chapter_json = normalize_chapter_payload(chapter_json, chapter_number)
        write_json(parameter_path, chapter_json, encoding=encoding)
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
    genai_mapping = _load_genai_mapping()
    manager = SnapshotManager(
        config,
        workspace_root=workspace_root,
        book_name=book_name,
        encoding=encoding,
        verbose=verbose,
        json_logs=json_logs,
    )
    book_path = manager.get_book_path()
    book_history_root = book_path

    settings = load_project_settings(book_path, encoding=encoding)
    manager.initialize_workspace(
        number_of_chapters=settings.chapter_count,
    )

    outline_path = book_path / "BookOutline.json"
    outline_payload: dict[str, Any]
    chapters: list[dict[str, Any]]

    if outline_path.exists():
        try:
            loaded_outline = load_json_file(outline_path, encoding=encoding)
        except (ValueError, OSError):
            loaded_outline = {}
    else:
        loaded_outline = {}

    if isinstance(loaded_outline, dict) and isinstance(loaded_outline.get("chapters", []), list):
        outline_payload = loaded_outline
        chapters = [item for item in loaded_outline.get("chapters", []) if isinstance(item, dict)]
    else:
        chapter_numbers = discover_chapter_numbers_from_workspace(book_path, config)
        chapters = [
            normalize_chapter_payload(
                {
                    "sl": number,
                    "name": f"Chapter {number}",
                    "chapter_title": f"Chapter {number}",
                    "chapter_summary": "",
                    "chapter_text": "",
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
            f"No chapters found for draft under: {book_path / 'BookChapters'}. "
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
        chapter_root, _, parameter_path = chapter_paths(book_path, config, chapter_number)
        chapter_history_root = manager.get_chapter_path(chapter_number)
        chapter_cfg = config.chapters
        out_folder = chapter_cfg.chapterOutFolderPattern.replace("{n}", str(chapter_number))
        out_path = chapter_root / out_folder
        out_path.mkdir(parents=True, exist_ok=True)

        if parameter_path.exists():
            try:
                chapter_parameter_payload = load_json_file(parameter_path, encoding=encoding)
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
        chapter_sections = chapter_parameter_payload.get("chapter_texts", [])
        if not isinstance(chapter_sections, list) or not chapter_sections:
            chapter_sections = chapter_payload.get("chapter_texts", [])
        if not isinstance(chapter_sections, list) or not chapter_sections:
            chapter_sections = [{"section-title": "part-1", "text": chapter_payload.get("chapter_text", "")}]

        aggregated_section_texts: list[str] = []
        aggregated_characters: list[dict[str, str]] = []
        chapter_title = str(chapter_payload.get("chapter_title", "")).strip() or f"Chapter {chapter_number}"
        chapter_summary_parts: list[str] = []
        next_running_summary = previous_running_summary

        for section_index, section_payload in enumerate(chapter_sections, start=1):
            if isinstance(section_payload, dict):
                section_name = str(
                    section_payload.get("section-title", section_payload.get("section", f"part-{section_index}"))
                ).strip() or f"part-{section_index}"
                section_seed_text = str(section_payload.get("text", "")).strip()
            else:
                section_name = f"part-{section_index}"
                section_seed_text = str(section_payload).strip()

            section_chapter_payload = dict(chapter_payload)
            section_chapter_payload["chapter_texts"] = [{"section-title": section_name, "section": section_name, "text": section_seed_text}]
            section_chapter_payload["chapter_text"] = section_seed_text

            section_parameter_payload = dict(chapter_parameter_payload)
            section_parameter_payload["chapter_texts"] = [{"section-title": section_name, "section": section_name, "text": section_seed_text}]
            section_parameter_payload["chapter_text"] = section_seed_text

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
        chapter_generated_path = out_path / "ChapterGenerated.txt"
        chapter_summary_path = out_path / "ChapterSummary.txt"
        chapter_character_path = out_path / "ChapterCharacter.txt"

        write_text(chapter_generated_path, generated_text, encoding=encoding)
        write_text(chapter_summary_path, chapter_summary + "\n", encoding=encoding)
        character_text = render_character_text(next_characters)
        write_text(chapter_character_path, character_text, encoding=encoding)

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
        chapter_payload["chapter_texts"] = chapter_text_to_sections(chapter_text)
        chapter_payload["chapter_text"] = chapter_text
        chapter_payload["chatper_text"] = chapter_text
        outline_payload["running_summary"] = next_running_summary
        extend_outline_characters(outline_payload, next_characters)

        verbose_print(
            verbose,
            json_logs,
            f"Drafted chapter {chapter_number}: {relative_path_text(chapter_generated_path)}",
            "draft.chapter.done",
        )

    write_json(outline_path, outline_payload, encoding=encoding)
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
    book_path = Path(workspace_root) / book_name
    outline_path = book_path / "BookOutline.json"

    chapter_cfg = config.chapters
    published_path = Path(output_path) if output_path else (book_path / "BookPublished.txt")
    published_path.parent.mkdir(parents=True, exist_ok=True)

    chapter_numbers: list[int] = []
    chapter_titles: dict[int, str] = {}

    if outline_path.exists():
        try:
            outline_payload = load_json_file(outline_path, encoding=encoding)
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
                    f"BookOutline.json is not in expected shape. Falling back to chapter folders under: {relative_path_text(book_path / 'BookChapters')}",
                    "publish.outline.fallback",
                )
        except (ValueError, OSError):
            verbose_print(
                verbose,
                json_logs,
                f"BookOutline.json is empty/invalid. Falling back to chapter folders under: {relative_path_text(book_path / 'BookChapters')}",
                "publish.outline.fallback",
            )

    if not chapter_numbers:
        chapter_numbers = discover_chapter_numbers_from_workspace(book_path, config)

    if not chapter_numbers:
        raise ValueError(
            f"No chapters found to publish under: {book_path / 'BookChapters'}. "
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
        chapter_folder = chapter_cfg.chapterFolderPattern.replace("{n}", str(chapter_number))
        out_folder = chapter_cfg.chapterOutFolderPattern.replace("{n}", str(chapter_number))
        generated_path = book_path / "BookChapters" / chapter_folder / out_folder / "ChapterGenerated.txt"
        if not generated_path.exists():
            raise FileNotFoundError(f"Generated chapter content not found: {generated_path}")

        chapter_title = chapter_titles.get(chapter_number, "")
        heading = chapter_title or f"Chapter {chapter_number}"
        content = read_text(generated_path, encoding=encoding).strip()
        chunks.append(f"Chapter {chapter_number}\n\n{heading}\n\n{content}\n===========================\n\n")
        verbose_print(
            verbose,
            json_logs,
            f"Included chapter {chapter_number} from: {relative_path_text(generated_path)}",
            "publish.chapter.appended",
        )

    write_text(published_path, "\n\n".join(chunks).strip() + "\n", encoding=encoding)
    verbose_print(
        verbose,
        json_logs,
        f"Published manuscript written to: {relative_path_text(published_path)}",
        "publish.done",
    )
    return published_path
