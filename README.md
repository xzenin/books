# books

Book workspace utility for structure initialization, snapshot export/import, cloning, and dummy content writing.

## Main CLI

Use `book.py` as the single entrypoint.

### Defaults

- Workspace root: `.pkbook/_wokspace`
- Config template: `templates/init.json`
- Snapshot file (export/import): `<book-name>.json` when `--snapshot-path` is not provided

### Commands

```powershell
python book.py --book-name IndiaDelhi
python book.py init --book-name Sita
python book.py export --book-name Sita
python book.py import --book-name Sita
python book.py clone --source-book-name Sita --target-book-name SitaCopy
python book.py write --book-name Sita
```

### Custom paths

```powershell
python book.py init --book-name Ramayan --workspace-root .\.pkbook\_wokspace --config-path .\templates\init.json
python book.py export --book-name Ramayan --snapshot-path snapshots\ramayan.json
python book.py import --book-name Ramayan --snapshot-path snapshots\ramayan.json
```

### Help

```powershell
python book.py --help
```