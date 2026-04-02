<#
.SYNOPSIS
Creates a complete book folder/file scaffold from a JSON definition.

.DESCRIPTION
Reads structure rules from init.json (or a custom config path) and creates
the target book root, chapter folders, and files.

.PARAMETER BookName
Mandatory. Name of the book root folder to create under WorkspaceRoot.

.PARAMETER WorkspaceRoot
Optional. Base directory where the book folder is created.
Default: <script_folder>\_workspace

.PARAMETER ConfigPath
Optional. Path to JSON configuration file.
Default: <script_folder>\init.json

.EXAMPLE
.\init.ps1 -BookName "Majar"

.EXAMPLE
.\init.ps1 -BookName "Sita" -WorkspaceRoot ".\_workspace"

.EXAMPLE
.\init.ps1 -BookName "Ramayana" -ConfigPath ".\init.json"

.NOTES
Use -BookName (correct parameter name).
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = (Join-Path $PSScriptRoot "_workspace"),

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$BookName,

    [string]$ConfigPath = (Join-Path $PSScriptRoot "init.json")
)

# 1) Read folder/file structure JSON from init.json.
if (-not (Test-Path -Path $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

$jsonStructure = Get-Content -Path $ConfigPath -Raw

# 2) Parse JSON into a PowerShell object.
$config = $jsonStructure | ConvertFrom-Json

# 3) Create folders and files by looping over parsed JSON data.
$bookPath = Join-Path $WorkspaceRoot $BookName
$chaptersRoot = Join-Path $bookPath "BookChapters"

New-Item -ItemType Directory -Path $bookPath -Force | Out-Null
New-Item -ItemType Directory -Path $chaptersRoot -Force | Out-Null

foreach ($fileName in $config.rootFiles) {
    $filePath = Join-Path $bookPath $fileName
    New-Item -ItemType File -Path $filePath -Force | Out-Null
}

for ($n = [int]$config.chapters.start; $n -le [int]$config.chapters.end; $n++) {
    $chapterFolderName = $config.chapters.chapterFolderPattern.Replace("{n}", [string]$n)
    $chapterPath = Join-Path $chaptersRoot $chapterFolderName
    New-Item -ItemType Directory -Path $chapterPath -Force | Out-Null

    foreach ($chapterFilePattern in $config.chapters.chapterFiles) {
        $chapterFileName = $chapterFilePattern.Replace("{n}", [string]$n)
        $chapterFilePath = Join-Path $chapterPath $chapterFileName
        New-Item -ItemType File -Path $chapterFilePath -Force | Out-Null
    }

    $outFolderName = $config.chapters.chapterOutFolderPattern.Replace("{n}", [string]$n)
    $outPath = Join-Path $chapterPath $outFolderName
    New-Item -ItemType Directory -Path $outPath -Force | Out-Null

    foreach ($outFilePattern in $config.chapters.chapterOutFiles) {
        $outFileName = $outFilePattern.Replace("{n}", [string]$n)

        # Keep Chapter1 running summary name aligned with your current pattern.
        if ($n -eq 1 -and $outFileName -eq "Chapter1RunningSummary.txt") {
            $outFileName = $config.chapters.chapter1RunningSummaryFile
        }

        $outFilePath = Join-Path $outPath $outFileName
        New-Item -ItemType File -Path $outFilePath -Force | Out-Null
    }
}

Write-Output "Structure created at: $bookPath"
