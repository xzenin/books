# books

Book workspace utility for structure initialization, listing, snapshot export/import, cloning, and content writing.

## Main CLI

Use `book.py` as the single entrypoint.

Global options such as `--workspace-root`, `--config-path`, and `--encoding` must be placed before the subcommand.

### Defaults

- Workspace root: `.pkbook/_wokspace`
- Config template: `templates/init.json`
- Snapshot file (init/export/import): `snapshots/<book-name>.json` when `--snapshot-path` is not provided

### Commands

```powershell
python book.py --book-name IndiaDelhi
python book.py init --book-name Sita
python book.py list
python book.py export --book-name Sita
python book.py import --book-name Sita
python book.py clone --source-book-name Sita --target-book-name SitaCopy
python book.py write --book-name Sita --gist "A historical Bengali epic"
python book.py write --book-name Sita --mode dummy
```

`python book.py --book-name IndiaDelhi` uses the implicit `init` behavior.

`python book.py list` prints tab-separated `book_name` and `chapter_count` columns.

### Custom paths

```powershell
python book.py --workspace-root .\.pkbook\_wokspace --config-path .\templates\init.json init --book-name Ramayan
python book.py --workspace-root .\.pkbook\_wokspace list
python book.py export --book-name Ramayan --snapshot-path snapshots\ramayan.json
python book.py import --book-name Ramayan --snapshot-path snapshots\ramayan.json
python book.py --workspace-root .\.pkbook\_wokspace write --book-name Ramayan --gist "A literary family drama"
```

### Help

```powershell
python book.py --help
```