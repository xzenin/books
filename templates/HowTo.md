# How to initialize a book workspace

This guide explains how to use `book.py` to create the book folder and file structure from `templates/init.json`.

## Files used

- `book.py`: Main CLI for init, export, import, clone, and write
- `templates/init.json`: JSON configuration that defines the structure

## Prerequisites

- Python environment for this repo
- Run commands from the books workspace root

## Basic command

```powershell
python .\book.py init --book-name "Majar"
```

This uses defaults for optional parameters:
- `--workspace-root`: `.pkbook\_wokspace` folder inside the repo
- `--config-path`: `templates\init.json`

## Common usage

### Create a different book name

```powershell
python .\book.py init --book-name "Sita"
```

### Use a custom workspace root

```powershell
python .\book.py --workspace-root "D:\lab\organization\books\.pkbook\_wokspace" init --book-name "Ramayana"
```

### Use a custom JSON config file

```powershell
python .\book.py --config-path ".\templates\init.json" init --book-name "Majar"
```

## Full example

```powershell
python .\book.py --workspace-root ".\.pkbook\_wokspace" --config-path ".\templates\init.json" init --book-name "MyNewBook"
```

## What gets created

- Book root folder inside `.pkbook\_wokspace\<BookName>`
- Root files from `templates/init.json`
- `BookChapters\Chapter1` to `BookChapters\Chapter20`
- Per-chapter files: `ChapterParameter.json` and `ChapterPrompt.txt`
- Per-chapter output files inside `ChapterOut`

## Re-running behavior

The initializer is safe to run again for structure setup:
- Existing folders are kept
- Missing files are recreated
- Existing files are not deleted by init
