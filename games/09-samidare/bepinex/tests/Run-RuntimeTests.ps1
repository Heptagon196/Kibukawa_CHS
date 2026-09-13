param([string]$PackPath)
$ErrorActionPreference = 'Stop'
$gamePath = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$seriesPath = (Resolve-Path (Join-Path $gamePath '../..')).Path
if (-not $PackPath) {
    $PackPath = Join-Path $gamePath 'bepinex/build/pack/translations.bin'
}
Add-Type -Path @(
    (Join-Path $seriesPath 'engine/core/TranslationCatalog.cs'),
    (Join-Path $seriesPath 'engine/core/TranslationPackReader.cs'),
    (Join-Path $PSScriptRoot 'RuntimeStubs.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-v2/src/MenuMemory.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-20050117/RuntimePack.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-20050117/src/NativeChoiceMemory.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-20050117/src/CanvasRuntime.cs'),
    (Join-Path $PSScriptRoot 'RuntimeTests.cs')
)
[Kibu9ZenTests.RuntimeTests]::Run($PackPath)
