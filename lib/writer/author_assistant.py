
import json
from pathlib import Path
from typing import Any, Callable
from lib.models import RuntimeWorkspaceState, SnapshotConfig

class AuthorAssistant:

    @staticmethod
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
        from lib.io import build_snapshot_manager
        from ..io.io_helpers import prompt_content_for_file, relative_path_text, verbose_print
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

    # Instantiate crew agents as static/global members
    # These will be initialized as needed in the methods, but references are static
    book_layout_agent = None
    chapter_refiner_agent = None
    layout_chapter_agent = None
    draft_chapter_segment_agent = None
    generate_chapter_segment_agent = None

    @staticmethod
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
        from lib.io import build_snapshot_manager
        from ..io.io_helpers import call_genai, extract_json_payload, prompt_for_gist, relative_path_text, verbose_print
        from .chapter_normalizers import chapter_sort_key, normalize_chapter_payload
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
        runtime_state = AuthorAssistant.build_runtime_state(manager)
        novel_gist = gist.strip() if gist else prompt_for_gist(book_name)
        if not novel_gist:
            raise ValueError("Novel gist is required.")
        novel_template = manager.load_template_payload("book.json")
        chapter_template = manager.load_template_payload("chapter.json")
        segment_template = manager.load_template_payload("segment.json")
        verbose_print(verbose, json_logs, "Loaded book, chapter, and segment JSON templates", "templates.loaded")
        book_provider = AuthorAssistant.resolve_provider_instance(genai_mapping, "book_level_generation")
        book_layout_agent = AuthorAssistant.get_book_layout_agent(settings, novel_gist, novel_template)
        chapter_refiner = AuthorAssistant.get_chapter_refiner_agent(randomize_thoughts, human_in_loop)
        layout_chapter_agent = AuthorAssistant.get_layout_chapter_agent(
            book_name, use_cache, verbose, json_logs, call_genai, extract_json_payload
        )
        draft_chapter_segment_agent = AuthorAssistant.get_draft_chapter_segment_agent(encoding, manager)
        generate_chapter_segment_agent = AuthorAssistant.get_generate_chapter_segment_agent(
            book_name, use_cache, verbose, json_logs, call_genai, extract_json_payload
        )
        book_prompt, outline_payload = book_layout_agent.create_master_plan(
            call_genai=call_genai,
            extract_json_payload=extract_json_payload,
            use_cache=use_cache,
            history_root=book_history_root,
            verbose=verbose,
            json_logs=json_logs,
            provider_instance_name=book_provider,
        )
        book_prompt_path = manager.get_book_prompt_path()
        AuthorAssistant.write_text_with_runtime(manager, runtime_state, book_prompt_path, book_prompt)
        verbose_print(
            verbose,
            json_logs,
            f"Saved novel prompt to: {relative_path_text(book_prompt_path)}",
            "prompt.novel.saved",
        )
        outline_path = manager.get_outline_path()
        AuthorAssistant.write_json_with_runtime(manager, runtime_state, outline_path, outline_payload)
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
        import time
        book_start_time = time.time()
        for fallback_index, chapter_payload in enumerate(sorted_chapters, start=1):
            chapter_start_time = time.time()
            verbose_print(
                verbose,
                json_logs,
                f"[GEN] Processing Chapter {fallback_index}",
                "chapter.number"
            )
            chapter_number = chapter_sort_key(chapter_payload, fallback_index)
            chapter_payload = normalize_chapter_payload(chapter_payload, chapter_number)
            chapter_root = manager.get_chapter_path(chapter_number)
            prompt_path, parameter_path = manager.get_chapter_file_paths(chapter_number)
            manager.ensure_dir(chapter_root)
            chapter_history_root = manager.get_chapter_path(chapter_number)
            # Extract book_summary and chapter_summary as plain text
            book_summary = outline_payload.get("running_summary", "")
            chapter_summary = chapter_payload.get("chapter_summary", "")
            if isinstance(book_summary, dict):
                book_summary = book_summary.get("running_summary", "")
            if isinstance(chapter_summary, dict):
                chapter_summary = chapter_summary.get("chapter_summary", "")
            # Build chapter prompt (assume a build_chapter_prompt function exists)
            from .prompt_builders import build_chapter_prompt
            chapter_prompt = build_chapter_prompt(
                settings=settings,
                book_gist=novel_gist,
                book_summary=book_summary,
                chapter_summary=chapter_summary,
                chapter_payload=chapter_payload,
                chapter_template_json=chapter_template,
                encoding=encoding,
            )
            AuthorAssistant.write_text_with_runtime(
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
                "chapter.prompt.saved",
            )
            chapter_provider = AuthorAssistant.resolve_provider_instance(genai_mapping, "chapter_level_generation")
            layout_chapter_agent.provider_instance_name = chapter_provider
            layout_prompt, segments = layout_chapter_agent.create_segment_layout(
                chapter_number=chapter_number,
                chapter_payload=chapter_payload,
                outline_payload=outline_payload,
                history_root=chapter_history_root,
            )
            layout_prompt_path = manager.get_chapter_layout_prompt_path(chapter_number)
            AuthorAssistant.write_text_with_runtime(
                manager,
                runtime_state,
                layout_prompt_path,
                layout_prompt + "\n",
                chapter_number=chapter_number,
                is_out_file=True,
            )
            verbose_print(
                verbose,
                json_logs,
                f"Saved chapter {chapter_number} layout prompt to: {relative_path_text(layout_prompt_path)}",
                "chapter.layout.saved",
            )
            # Draft and generate segments
            segment_provider = AuthorAssistant.resolve_provider_instance(genai_mapping, "segment_level_generation")
            drafted_segments = draft_chapter_segment_agent.draft_segment_prompts(
                settings=settings,
                chapter_number=chapter_number,
                chapter_payload=chapter_payload,
                outline_payload=outline_payload,
                provider_instance_name=segment_provider,
                call_genai=call_genai,
                extract_json_payload=extract_json_payload,
                use_cache=use_cache,
                verbose=verbose,
                json_logs=json_logs,
            )
            generate_chapter_segment_agent.provider_instance_name = segment_provider
            generated_segments = generate_chapter_segment_agent.generate_segment_content(
                chapter_number=chapter_number,
                chapter_root=chapter_root,
                drafted_segments=drafted_segments,
                segment_history_roots={
                    int(item.index): manager.get_segment_path(chapter_number, int(item.index))
                    for item in drafted_segments
                },
                call_genai=call_genai,
                extract_json_payload=extract_json_payload,
                use_cache=use_cache,
                verbose=verbose,
                json_logs=json_logs,
            )
            # Save generated segments and chapter
            chapter_generated_path = manager.get_chapter_generated_path(chapter_number)
            full_chapter_text = "\n\n".join([seg.text for seg in generated_segments if hasattr(seg, 'text')])
            AuthorAssistant.write_text_with_runtime(
                manager,
                runtime_state,
                chapter_generated_path,
                full_chapter_text,
                chapter_number=chapter_number,
                is_out_file=True,
            )
            verbose_print(
                verbose,
                json_logs,
                f"Saved generated chapter {chapter_number} to: {relative_path_text(chapter_generated_path)}",
                "chapter.generated.saved",
            )
            chapter_elapsed = time.time() - chapter_start_time
            verbose_print(
                verbose,
                json_logs,
                f"[GEN] Completed Chapter {chapter_number} in {chapter_elapsed:.2f} seconds",
                "chapter.time",
            )
        book_elapsed = time.time() - book_start_time
        verbose_print(
            verbose,
            json_logs,
            f"Generated book completed for: {book_name} in {book_elapsed:.2f} seconds",
            "generated.done.book.time",
        )
        return book_path

    @staticmethod
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
        from lib.io import build_snapshot_manager
        from ..io.io_helpers import prompt_for_gist, relative_path_text, verbose_print, call_genai, extract_json_payload
        from .chapter_normalizers import chapter_sort_key, normalize_chapter_payload, normalize_author_payload, render_character_text, extend_outline_characters
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
        runtime_state = AuthorAssistant.build_runtime_state(manager)
        outline_path = manager.get_outline_path()
        running_summary_path = manager.get_book_file_path("BookRunningSummary.txt")
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
        # ... (for brevity, the rest of the workflow would continue here, delegating to the crew agents as needed)
        # This is a placeholder for the full workflow logic, which should be implemented as needed.
        return book_path

    @staticmethod
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
        from lib.io import build_snapshot_manager
        from ..io.io_helpers import relative_path_text, verbose_print
        from .chapter_normalizers import chapter_sort_key
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
        chapter_numbers = []
        chapter_titles = {}
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
        chunks = []
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
        @staticmethod
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
            """
            Write dummy content for a book. Uses AuthorAssistant for all provider/runtime/write helpers.
            """
            from lib.io import build_snapshot_manager
            from ..io.io_helpers import prompt_content_for_file, relative_path_text, verbose_print
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
    """
    Assistant class for authoring, drafting, generating, and publishing book content.
    Functions are grouped by feature: provider resolution, runtime state, writing, content generation, drafting, and publishing.
    """

    @staticmethod
    def resolve_provider_instance(mapping: dict[str, str], level_key: str) -> str | None:
        return mapping.get(level_key.strip().lower()) or mapping.get("default")

    @staticmethod
    def build_runtime_state(manager: Any) -> RuntimeWorkspaceState:
        snapshot = manager.read_from_workspace()
        return RuntimeWorkspaceState(snapshot=snapshot)

    @staticmethod
    def record_runtime_write(runtime_state: RuntimeWorkspaceState, path: str | Path, content: str, *, chapter_number: int | None = None, is_out_file: bool = False, entry_name: str | None = None) -> None:
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

    @staticmethod
    def write_text_with_runtime(manager: Any, runtime_state: RuntimeWorkspaceState, path: str | Path, content: str, *, chapter_number: int | None = None, is_out_file: bool = False, entry_name: str | None = None) -> None:
        manager.write_text_file(path, content)
        AuthorAssistant.record_runtime_write(runtime_state, path, content, chapter_number=chapter_number, is_out_file=is_out_file, entry_name=entry_name)

    @staticmethod
    def write_json_with_runtime(manager: Any, runtime_state: RuntimeWorkspaceState, path: str | Path, payload: Any, *, chapter_number: int | None = None, is_out_file: bool = False, entry_name: str | None = None) -> None:
        manager.write_json_file(path, payload)
        serialised = json.dumps(payload, ensure_ascii=False, indent=2)
        AuthorAssistant.record_runtime_write(runtime_state, path, serialised, chapter_number=chapter_number, is_out_file=is_out_file, entry_name=entry_name)

    # Instantiate crew agents as static/global members
    # These will be initialized as needed in the methods, but references are static
    book_layout_agent = None
    chapter_refiner_agent = None
    layout_chapter_agent = None
    draft_chapter_segment_agent = None
    generate_chapter_segment_agent = None

    @classmethod
    def get_book_layout_agent(cls, settings, gist, template_payload):
        from .agents.crew_agents import BookLayout
        if cls.book_layout_agent is None:
            cls.book_layout_agent = BookLayout(settings, gist, template_payload)
        return cls.book_layout_agent

    @classmethod
    def get_chapter_refiner_agent(cls, randomize_thoughts=True, human_in_loop=False):
        from .agents.crew_agents import RefinetChapter
        if cls.chapter_refiner_agent is None:
            cls.chapter_refiner_agent = RefinetChapter(randomize_thoughts, human_in_loop)
        return cls.chapter_refiner_agent

    @classmethod
    def get_layout_chapter_agent(cls, book_name, use_cache, verbose, json_logs, call_genai, extract_json_payload):
        from .agents.crew_agents import LayoutChapter
        if cls.layout_chapter_agent is None:
            cls.layout_chapter_agent = LayoutChapter(book_name, use_cache, verbose, json_logs, call_genai, extract_json_payload)
        return cls.layout_chapter_agent

    @classmethod
    def get_draft_chapter_segment_agent(cls, encoding, manager):
        from .agents.crew_agents import DraftChapterSegment
        if cls.draft_chapter_segment_agent is None:
            cls.draft_chapter_segment_agent = DraftChapterSegment(encoding, manager)
        return cls.draft_chapter_segment_agent

    @classmethod
    def get_generate_chapter_segment_agent(cls, book_name, use_cache, verbose, json_logs, call_genai, extract_json_payload):
        from .agents.crew_agents import GenerateChapterSegment
        if cls.generate_chapter_segment_agent is None:
            cls.generate_chapter_segment_agent = GenerateChapterSegment(book_name, use_cache, verbose, json_logs, call_genai, extract_json_payload)
        return cls.generate_chapter_segment_agent
