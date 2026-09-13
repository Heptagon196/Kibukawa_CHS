$ErrorActionPreference = 'Stop'
$gamePath = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$seriesPath = (Resolve-Path (Join-Path $gamePath '../..')).Path
Add-Type -Path @(
    (Join-Path $seriesPath 'engine/adapters/gmode-v2/src/TextGeometry.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-v2/src/TextBreaks.cs'),
    (Join-Path $PSScriptRoot 'RuntimeStubs.cs'),
    (Join-Path $PSScriptRoot 'PuzzleNotebookTests.cs'),
    (Join-Path $gamePath 'bepinex/src/PuzzleNotebook.cs'),
    (Join-Path $PSScriptRoot 'RuntimeTests.cs'),
    (Join-Path $PSScriptRoot 'NativeDialogueLayoutTests.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-20050817/src/NativeDialogueLayout.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-20050817/src/CanvasRuntime.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-20050817/src/RuntimeLayout.cs'),
    (Join-Path $gamePath 'bepinex/src/Plugin.cs'),
    (Join-Path $gamePath 'bepinex/src/UiLocalizationData.cs'),
    (Join-Path $gamePath 'bepinex/src/ScriptIdentityData.cs'),
    (Join-Path $seriesPath 'engine/core/TranslationCatalog.cs'),
    (Join-Path $seriesPath 'engine/core/TranslationPackReader.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-20050817/RuntimePack.cs')
)
[RuntimeTests]::Run($gamePath)

[PuzzleNotebookTests]::Run()
