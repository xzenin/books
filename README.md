# Book writing software

Book workspace utility for structure initialization, listing, snapshot export/import, cloning, layout generation, chapter drafting, and publish assembly.

GenAI conversation history can now be scoped dynamically per call. The writer workflow uses book-level history under `<workspace>/<bookname>/.pkbook/_genai/history` for novel layout calls and chapter-level history under `<workspace>/<bookname>/BookChapters/Chapter<n>/.pkbook/_genai/history` for chapter generation and drafting calls.

## Main CLI

Use `book.py` as the single entrypoint.

Global options such as `--workspace-root`, `--config-path`, and `--encoding` must be placed before the subcommand.

`--verbose` prints progress details for major CLI, snapshot, layout/draft/publish, and GenAI workflow steps.

`--json` switches verbose events to machine-readable JSON lines.

`--version` reads application metadata from `.pkbook/config.json`.

### Defaults

- Workspace root: `.pkbook/_workspace`
- Config template: `templates/init.json`
- Snapshot file (init/export/import): `snapshots/<book-name>.json` when `--snapshot-path` is not provided

### Commands

```python
python book.py --book-name IndiaDelhi
python book.py init --book-name Sita
python book.py init --book-name Sita --chapter-count 6
python book.py list
python book.py export --book-name Sita
python book.py import --book-name Sita
python book.py clone --source-book-name Sita --target-book-name SitaCopy
python book.py layout --book-name Sita --gist "A historical Bengali epic"
python book.py layout --book-name Sita --mode dummy
python book.py draft --book-name Sita --gist "A historical Bengali epic"
python book.py publish --book-name Sita
python book.py --verbose list
python book.py --verbose layout --book-name Sita --gist "A historical Bengali epic"
python book.py --verbose draft --book-name Sita
python book.py --verbose publish --book-name Sita
python book.py --verbose --json draft --book-name Sita
python book.py --verbose --json publish --book-name Sita
python book.py --verbose --json list
python book.py --version
```

`python book.py --book-name IndiaDelhi` uses the implicit `init` behavior.

`python book.py list` prints tab-separated `book_name` and `chapter_count` columns.

### What Each Command Does

- `init`: Creates the full workspace structure for a book under the workspace root.
- `list`: Lists all books in the workspace with chapter counts.
- `export`: Reads one book workspace and writes a snapshot JSON file.
- `import`: Restores one book workspace from a snapshot JSON file.
- `clone`: Copies one book workspace into another book name.
- `layout`: Generates or fills layout/content files for a book.
- `draft`: Writes chapter prose and chapter outputs from `BookOutline.json` and chapter parameter context.
- `publish`: Compiles all chapter generated text into one `BookPublished.txt` manuscript file.

### Layout Command

`layout` supports two modes:

- `--mode genai` (default): Uses GenAI to generate novel outline and chapter JSON content.
- `--mode dummy`: Writes placeholder/sample content using the legacy dummy flow.

If the target book is not initialized yet, `layout` auto-initializes the workspace first and creates `Settings.json` before generating content.

GenAI memory behavior during `layout`:

- Novel outline calls use the book folder as the history root.
- Chapter parameter calls use the corresponding chapter folder as the history root.

`--chapter-count` is supported on `layout` in both cases:

- First run (book not initialized): creates chapter folders using the provided count.
- Existing book (already initialized): updates chapter layout and `Settings.json` chapter count.

Examples:

```python
python book.py layout --book-name Sita --gist "A historical Bengali epic"
python book.py layout --book-name Sita --gist "A historical Bengali epic" --chapter-count 6
python book.py layout --book-name Sita --mode dummy
python book.py layout --book-name Sita --mode dummy --chapter-count 6
python book.py --workspace-root .\.pkbook\_workspace layout --book-name Sita --mode dummy
```

### Init Command

`init` also supports `--chapter-count` to control initial chapter folder creation.

Examples:

```python
python book.py init --book-name Sita
python book.py init --book-name Sita --chapter-count 6
```

### Draft Command

`draft` reads the generated outline and chapter parameter context, then writes chapter outputs chapter-by-chapter.

Inputs used per chapter:

- `<workspace>/<bookname>/BookOutline.json`
- `<workspace>/<bookname>/BookChapters/Chapter<chapter-counter>/ChapterParameter.json`

Outputs written per chapter:

- `<workspace>/<bookname>/BookChapters/Chapter<chapter-counter>/ChapterOut/ChapterGenerated.txt`
- `<workspace>/<bookname>/BookChapters/Chapter<chapter-counter>/ChapterOut/ChapterSummary.txt`
- `<workspace>/<bookname>/BookChapters/Chapter<chapter-counter>/ChapterOut/ChapterCharacter.txt`

Compatibility output (also written):

- `<workspace>/<bookname>/BookChapters/Chapter<chapter-counter>/ChapterOut/ChapterCharacter.txt`

Book outline updates:

- Updates `running_summary` in `<workspace>/<bookname>/BookOutline.json`
- Extends `all_characters` with newly proposed characters

Notes:

- `draft` auto-initializes if the book workspace does not exist.
- `draft` also supports `--chapter-count` for first-time initialization.
- `draft` supports `--no-cache` and `--gist` override.
- `draft` supports `--verbose` and `--json` for machine-readable progress logs.
- Each chapter drafting call uses that chapter folder as the GenAI history root, so long-term memory is isolated per chapter.

### GenAI History Override

The public GenAI helpers in `lib/genai.py` accept an optional `history_root` path before each call:

```python
from pathlib import Path
from lib.genai import chat

response = chat(
	"Create a chapter outline.",
	conversation_id="demo-outline",
	history_root=Path(".pkbook/_workspace/Sita"),
)
```

If you are working with a persistent client directly, call `set_history_root(...)` before `send(...)`, or pass `history_root=...` to `send(...)` for that call.

Examples:

```python
python book.py draft --book-name Sita
python book.py draft --book-name Sita --gist "A historical Bengali epic"
python book.py draft --book-name Sita --chapter-count 6 --verbose
python book.py --workspace-root .\.pkbook\_workspace draft --book-name Sita --no-cache
```

### Publish Command

`publish` reads chapter order from `<workspace>/<bookname>/BookOutline.json`, then appends chapter generated content from:

- `<workspace>/<bookname>/BookChapters/Chapter<chapter-counter>/ChapterOut/ChapterGenerated.txt`

and writes the compiled manuscript to:

- `<workspace>/<bookname>/BookPublished.txt`

Optional override:

- `--output-path` to write to a custom target file.

Examples:

```python
python book.py publish --book-name Sita
python book.py publish --book-name Sita --output-path .\snapshots\SitaPublished.txt
python book.py --verbose --json publish --book-name Sita
```

### Important Argument Order

Global options must appear before the subcommand.

Correct:

```python
python book.py --workspace-root .\.pkbook\_workspace layout --book-name Sita --mode dummy
```

Incorrect:

```python
python book.py layout --book-name Sita --mode dummy --workspace-root .\.pkbook\_workspace
```


### Help

```python
python book.py --help
```

