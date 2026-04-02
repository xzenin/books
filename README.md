# books

Book workspace utility for structure initialization, listing, snapshot export/import, cloning, and content layout generation.

## Main CLI

Use `book.py` as the single entrypoint.

Global options such as `--workspace-root`, `--config-path`, and `--encoding` must be placed before the subcommand.

`--verbose` prints progress details for major CLI, snapshot, layout, and GenAI workflow steps.

`--json` switches verbose events to machine-readable JSON lines.

`--version` reads application metadata from `.pkbook/config.json`.

### Defaults

- Workspace root: `.pkbook/_wokspace`
- Config template: `templates/init.json`
- Snapshot file (init/export/import): `snapshots/<book-name>.json` when `--snapshot-path` is not provided

### Commands

```python
python book.py --book-name IndiaDelhi
python book.py init --book-name Sita
python book.py list
python book.py export --book-name Sita
python book.py import --book-name Sita
python book.py clone --source-book-name Sita --target-book-name SitaCopy
python book.py layout --book-name Sita --gist "A historical Bengali epic"
python book.py layout --book-name Sita --mode dummy
python book.py --verbose list
python book.py --verbose layout --book-name Sita --gist "A historical Bengali epic"
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

### Layout Command

`layout` supports two modes:

- `--mode genai` (default): Uses GenAI to generate novel outline and chapter JSON content.
- `--mode dummy`: Writes placeholder/sample content using the legacy dummy flow.

If the target book is not initialized yet, `layout` now auto-initializes the workspace first and creates `Settings.json` before generating content.

Examples:

```python
python book.py layout --book-name Sita --gist "A historical Bengali epic"
python book.py layout --book-name Sita --mode dummy
python book.py --workspace-root .\.pkbook\_wokspace layout --book-name Sita --mode dummy
```

### Important Argument Order

Global options must appear before the subcommand.

Correct:

```python
python book.py --workspace-root .\.pkbook\_wokspace layout --book-name Sita --mode dummy
```

Incorrect:

```python
python book.py layout --book-name Sita --mode dummy --workspace-root .\.pkbook\_wokspace
```


### Help

```python
python book.py --help
```

