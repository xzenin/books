# Book Writing Software

## Introduction

This project is a CLI-driven book production pipeline that creates and manages structured workspaces under `.pkbook/_workspace`, then generates and refines content chapter-by-chapter.

It supports:

- Workspace initialization and maintenance
- Snapshot export/import and cloning
- GenAI-based layout generation
- Segment-first chapter drafting
- Final manuscript publishing

The core entrypoint is [book.py](book.py). Internally, generation flows live in [lib/writer/write.py](lib/writer/write.py), and workspace IO is abstracted through snapshot managers in [lib/io/manager.py](lib/io/manager.py).

## Workflow

The current workflow is segment-centric (no `chapter_texts` as a canonical model).

1. `init`
Creates the full workspace structure and base files.

2. `layout`
Generates `BookOutline.json`, chapter prompts, chapter parameters, segment prompts, and segment generated files.

3. `draft`
Consumes chapter context and writes chapter outputs (`ChapterGenerated.txt`, `ChapterSummary.txt`, `ChapterCharacter.txt`) chapter-by-chapter.

4. `publish`
Combines all chapter generated content into one `BookPublished.txt`.

### Data Flow (High Level)

1. `BookOutline.json` provides chapter-level plan.
2. Each chapter stores its structured context in `ChapterParameter.json` with `chapter_segments`.
3. Segment prompt generation uses [templates/segment_prompt.txt](templates/segment_prompt.txt) and [templates/segment.json](templates/segment.json).
4. Each segment output is written to `SegmentOut/SegmentGenerated.txt`.
5. `ChapterGenerated.txt` is updated incrementally by appending segment blocks, prefixed with `Segment Title: ...`.

### GenAI History Scoping

History is stored in `_history` directories (not `_genai`).

- Global: `.pkbook/_history`
- Book: `.pkbook/_workspace/<book_name>/_history`
- Chapter: `.pkbook/_workspace/<book_name>/BookChapters/Chapter<n>/_history`
- Segment: `.pkbook/_workspace/<book_name>/BookChapters/Chapter<n>/ChapterSegments/Segment<s>/_history`

## How To Use

### Prerequisites

- Python environment available (project often uses `.venv`)
- Required dependencies installed from [requirements.txt](requirements.txt)
- Configured `.pkbook/config.json` with provider credentials and mapping

### Command Syntax

Use:

```bash
python book.py [global-options] <command> [command-options]
```

Global options (must be before subcommand):

- `--workspace-root`
- `--config-path`
- `--encoding`
- `--verbose`
- `--json`
- `--debug`

### Common Commands

```bash
python book.py init --book-name Sita --chapter-count 6
python book.py list
python book.py layout --book-name Sita --gist "A historical Bengali epic"
python book.py draft --book-name Sita --gist "A historical Bengali epic"
python book.py publish --book-name Sita
python book.py read --book-name Sita
python book.py export --book-name Sita
python book.py import --book-name Sita
python book.py clone --source-book-name Sita --target-book-name SitaCopy
python book.py --help
```

### Recommended End-to-End Run

```bash
python book.py init --book-name demo --chapter-count 2 --verbose
python book.py layout --book-name demo --gist "A historical Bengali epic" --verbose
python book.py draft --book-name demo --verbose
python book.py publish --book-name demo --verbose
python book.py read --book-name demo
```

### Important Behaviors

- `--chapter-count` must be `>= 1`.
- `BookRunningSummary.txt` is appended per completed chapter during draft.
- `ChapterSummary.txt` is written after all segments of a chapter are processed.
- Segment output parsing accepts `segment_text` and `generated_text`.

## Next Steps

1. Add automated tests for critical flows:
	- segment prompt generation
	- `ChapterParameter.json` schema integrity
	- incremental append behavior for `ChapterGenerated.txt` and `BookRunningSummary.txt`

2. Add schema validation:
	- validate `BookOutline.json`, `ChapterParameter.json`, and segment payloads before write

3. Add recovery tooling:
	- command to repair/migrate older workspaces containing deprecated keys

4. Add observability improvements:
	- optional per-command trace artifact for provider responses and parse outcomes

5. Add docs examples for provider mapping strategy in `.pkbook/config.json`:
	- book/chapter/segment routing and expected fallback behavior

