# How to run init.ps1

This guide explains how to run the PowerShell initializer that creates a full book folder and file structure.

## Files used

- init.ps1: Script that creates folders and files
- templates\init.json: JSON configuration that defines the structure

## Prerequisites

- Windows PowerShell or PowerShell 7
- Run commands from the books workspace root (the folder that contains init.ps1)

## Basic command

```powershell
.\init.ps1 -BookName "Majar"
```

This uses defaults for optional parameters:
- WorkspaceRoot: .pkbook\_wokspace folder inside the current repo
- ConfigPath: templates\init.json in the repo root

BookName is mandatory.

## Common usage

### 1) Create a different book name

```powershell
.\init.ps1 -BookName "Sita"
```

### 2) Use a custom workspace root

```powershell
.\init.ps1 -WorkspaceRoot "D:\lab\organization\books\.pkbook\_wokspace" -BookName "Ramayana"
```

### 3) Use a custom JSON config file

```powershell
.\init.ps1 -ConfigPath ".\templates\init.json" -BookName "Majar"
```

## Full example

```powershell
.\init.ps1 -WorkspaceRoot ".\.pkbook\_wokspace" -BookName "MyNewBook" -ConfigPath ".\templates\init.json"
```

## Mandatory vs optional parameters

- Mandatory: -BookName
- Optional: -WorkspaceRoot, -ConfigPath

## Important note on parameter name

Use -BookName (correct)
Do not use --BooName (incorrect)

If you run with an unknown argument, PowerShell may treat it as a positional value and create unexpected folders.

## What gets created

- Book root folder inside .pkbook\_wokspace\<BookName>
- Root files from templates\init.json
- BookChapters\Chapter1 to BookChapters\Chapter20
- Per-chapter parameter/references/prompt files
- Per-chapter output files inside ChapterNOut

## Re-running behavior

The script uses -Force with New-Item:
- Existing folders are kept
- Existing files are recreated if needed
- Running the script again is safe for structure setup
