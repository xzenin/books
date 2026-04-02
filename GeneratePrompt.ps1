<#
.SYNOPSIS
Generates sample content for all template files in a book workspace.

.DESCRIPTION
Reads the structure from init.json, ensures folders/files exist, then writes sample
content based on naming conventions. JSON files are written with sample JSON and
text files are appended with sample text using the provided user input.

.PARAMETER BookName
Mandatory. Name of the target book folder under WorkspaceRoot.

.PARAMETER UserInput
Theme/topic used to generate sample content. If omitted, the script prompts for input.

.PARAMETER WorkspaceRoot
Optional. Root folder where the book folder is created. Default: .\_workspace

.PARAMETER ConfigPath
Optional. Path to init.json template config. Default: .\init.json

.EXAMPLE
.\GeneratePrompt.ps1 -BookName "DemoBook" -UserInput "Courage and Duty"

.EXAMPLE
.\GeneratePrompt.ps1 -BookName "DemoBook"
Prompts for UserInput interactively.

.EXAMPLE
.\GeneratePrompt.ps1 -BookName "DemoBook" -WorkspaceRoot ".\_workspace" -ConfigPath ".\init.json" -UserInput "Leadership"
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = (Join-Path $PSScriptRoot "_workspace"),

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$BookName,

    [string]$ConfigPath = (Join-Path $PSScriptRoot "init.json"),

    [string]$UserInput
)

# 1) Read folder/file structure JSON from init.json.
if (-not (Test-Path -Path $ConfigPath)) {
    throw "Config file not found: $ConfigPath"
}

if ([string]::IsNullOrWhiteSpace($UserInput)) {
    $UserInput = Read-Host "Enter the theme/topic to generate sample content"
}

if ([string]::IsNullOrWhiteSpace($UserInput)) {
    throw "User input cannot be empty."
}

$jsonStructure = Get-Content -Path $ConfigPath -Raw

# 2) Parse JSON into a PowerShell object.
$config = $jsonStructure | ConvertFrom-Json

function Ensure-File {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    $dir = Split-Path -Path $Path -Parent
    if (-not (Test-Path -Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }

    if (-not (Test-Path -Path $Path)) {
        New-Item -ItemType File -Path $Path -Force | Out-Null
    }
}

function Write-SettingsJson {
    param([string]$Path, [string]$BookName, [string]$UserInput)
    $obj = @{
        bookName = $BookName
        theme = $UserInput
        language = "en"
        tone = "Narrative"
        createdAt = (Get-Date).ToString("s")
    }
    Set-Content -Path $Path -Value ($obj | ConvertTo-Json -Depth 5) -Encoding UTF8
}

function Write-BookOutlineJson {
    param([string]$Path, [string]$BookName, [string]$UserInput)
    $obj = @{
        title = $BookName
        concept = $UserInput
        outline = @(
            "Introduction to $UserInput",
            "Rising conflict around $UserInput",
            "Resolution and conclusion"
        )
    }
    Set-Content -Path $Path -Value ($obj | ConvertTo-Json -Depth 5) -Encoding UTF8
}

function Write-BookSummaryJson {
    param([string]$Path, [string]$BookName, [string]$UserInput)
    $obj = @{
        title = $BookName
        summary = "This book explores $UserInput through progressive chapters."
    }
    Set-Content -Path $Path -Value ($obj | ConvertTo-Json -Depth 5) -Encoding UTF8
}

function Write-AllCharactersJson {
    param([string]$Path, [string]$UserInput)
    $obj = @{
        characters = @(
            @{ name = "Lead"; role = "Protagonist"; relationToTheme = $UserInput },
            @{ name = "Guide"; role = "Mentor"; relationToTheme = "Supports the journey" }
        )
    }
    Set-Content -Path $Path -Value ($obj | ConvertTo-Json -Depth 6) -Encoding UTF8
}

function Write-AllSettingsJson {
    param([string]$Path, [string]$UserInput)
    $obj = @{
        world = "Sample world"
        backdrop = "Built around $UserInput"
        timeline = "Ancient to modern transition"
    }
    Set-Content -Path $Path -Value ($obj | ConvertTo-Json -Depth 5) -Encoding UTF8
}

function Write-BookReferencesJson {
    param([string]$Path, [string]$UserInput)
    $obj = @{
        references = @(
            "Primary source for $UserInput",
            "Secondary context and notes"
        )
    }
    Set-Content -Path $Path -Value ($obj | ConvertTo-Json -Depth 5) -Encoding UTF8
}

function Write-BookPromptTxt {
    param([string]$Path, [string]$BookName, [string]$UserInput)
    Add-Content -Path $Path -Value "Create a cohesive narrative for '$BookName' focused on '$UserInput'."
}

function Write-BookForewordTxt {
    param([string]$Path, [string]$BookName, [string]$UserInput)
    Add-Content -Path $Path -Value "Foreword: '$BookName' introduces the journey of $UserInput."
}

function Write-ChapterParameterJson {
    param([string]$Path, [int]$ChapterNumber, [string]$UserInput)
    $obj = @{
        chapter = $ChapterNumber
        objective = "Advance the narrative around $UserInput"
        targetWords = 1200
    }
    Set-Content -Path $Path -Value ($obj | ConvertTo-Json -Depth 5) -Encoding UTF8
}

function Write-ChapterReferencesTxt {
    param([string]$Path, [int]$ChapterNumber, [string]$UserInput)
    Add-Content -Path $Path -Value "Chapter $ChapterNumber references for ${UserInput}: add source notes here."
}

function Write-ChapterPromptTxt {
    param([string]$Path, [int]$ChapterNumber, [string]$BookName, [string]$UserInput)
    Add-Content -Path $Path -Value "Write Chapter $ChapterNumber of '$BookName' centered on '$UserInput' with continuity."
}

function Write-ChapterSummaryTxt {
    param([string]$Path, [int]$ChapterNumber, [string]$UserInput)
    Add-Content -Path $Path -Value "Summary: Chapter $ChapterNumber develops the theme '$UserInput'."
}

function Write-ChapterCharactersTxt {
    param([string]$Path, [int]$ChapterNumber, [string]$UserInput)
    Add-Content -Path $Path -Value "Characters in Chapter $ChapterNumber affected by '$UserInput': Lead, Guide."
}

function Write-ChapterGeneratedTxt {
    param([string]$Path, [int]$ChapterNumber, [string]$BookName, [string]$UserInput)
    Add-Content -Path $Path -Value "Generated draft for Chapter $ChapterNumber of '$BookName' on '$UserInput'."
}

function Write-ChapterRunningSummaryTxt {
    param([string]$Path, [int]$ChapterNumber, [string]$UserInput)
    Add-Content -Path $Path -Value "Running summary up to Chapter ${ChapterNumber}: key progress on '$UserInput'."
}

function Write-RootFileContent {
    param([string]$FileName, [string]$FilePath, [string]$BookName, [string]$UserInput)

    switch ($FileName) {
        "Settings.json" { Write-SettingsJson -Path $FilePath -BookName $BookName -UserInput $UserInput; break }
        "BookOutline.json" { Write-BookOutlineJson -Path $FilePath -BookName $BookName -UserInput $UserInput; break }
        "BookSummary.json" { Write-BookSummaryJson -Path $FilePath -BookName $BookName -UserInput $UserInput; break }
        "AllCharacters.json" { Write-AllCharactersJson -Path $FilePath -UserInput $UserInput; break }
        "AllSettings.json" { Write-AllSettingsJson -Path $FilePath -UserInput $UserInput; break }
        "BookReferences.json" { Write-BookReferencesJson -Path $FilePath -UserInput $UserInput; break }
        "BookPrompt.txt" { Write-BookPromptTxt -Path $FilePath -BookName $BookName -UserInput $UserInput; break }
        "BookForeword.txt" { Write-BookForewordTxt -Path $FilePath -BookName $BookName -UserInput $UserInput; break }
        default { Add-Content -Path $FilePath -Value "Sample content for $FileName using '$UserInput'." }
    }
}

function Write-ChapterFileContent {
    param([string]$FileName, [string]$FilePath, [int]$ChapterNumber, [string]$BookName, [string]$UserInput)

    switch -Regex ($FileName) {
        '^Chapter\d+Parameter\.json$' { Write-ChapterParameterJson -Path $FilePath -ChapterNumber $ChapterNumber -UserInput $UserInput; break }
        '^Chapter\d+References\.txt$' { Write-ChapterReferencesTxt -Path $FilePath -ChapterNumber $ChapterNumber -UserInput $UserInput; break }
        '^Chapter\d+Prompt\.txt$' { Write-ChapterPromptTxt -Path $FilePath -ChapterNumber $ChapterNumber -BookName $BookName -UserInput $UserInput; break }
        '^Chapter\d+Summary\.txt$' { Write-ChapterSummaryTxt -Path $FilePath -ChapterNumber $ChapterNumber -UserInput $UserInput; break }
        '^Chapter\d+Characters\.txt$' { Write-ChapterCharactersTxt -Path $FilePath -ChapterNumber $ChapterNumber -UserInput $UserInput; break }
        '^Chapter\d+Generated\.txt$' { Write-ChapterGeneratedTxt -Path $FilePath -ChapterNumber $ChapterNumber -BookName $BookName -UserInput $UserInput; break }
        '^Chapter\d+RunningSummary\.txt$|^ChapterRunningSummary\.txt$' { Write-ChapterRunningSummaryTxt -Path $FilePath -ChapterNumber $ChapterNumber -UserInput $UserInput; break }
        default { Add-Content -Path $FilePath -Value "Sample chapter content for $FileName using '$UserInput'." }
    }
}

# 3) Create folders and files by looping over parsed JSON data and then write sample content.
$bookPath = Join-Path $WorkspaceRoot $BookName
$chaptersRoot = Join-Path $bookPath "BookChapters"

New-Item -ItemType Directory -Path $bookPath -Force | Out-Null
New-Item -ItemType Directory -Path $chaptersRoot -Force | Out-Null

foreach ($fileName in $config.rootFiles) {
    $filePath = Join-Path $bookPath $fileName
    Ensure-File -Path $filePath
    Write-RootFileContent -FileName $fileName -FilePath $filePath -BookName $BookName -UserInput $UserInput
}

for ($n = [int]$config.chapters.start; $n -le [int]$config.chapters.end; $n++) {
    $chapterFolderName = $config.chapters.chapterFolderPattern.Replace("{n}", [string]$n)
    $chapterPath = Join-Path $chaptersRoot $chapterFolderName
    New-Item -ItemType Directory -Path $chapterPath -Force | Out-Null

    foreach ($chapterFilePattern in $config.chapters.chapterFiles) {
        $chapterFileName = $chapterFilePattern.Replace("{n}", [string]$n)
        $chapterFilePath = Join-Path $chapterPath $chapterFileName
        Ensure-File -Path $chapterFilePath
        Write-ChapterFileContent -FileName $chapterFileName -FilePath $chapterFilePath -ChapterNumber $n -BookName $BookName -UserInput $UserInput
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
        Ensure-File -Path $outFilePath
        Write-ChapterFileContent -FileName $outFileName -FilePath $outFilePath -ChapterNumber $n -BookName $BookName -UserInput $UserInput
    }
}

Write-Output "Structure and sample content generated at: $bookPath"
