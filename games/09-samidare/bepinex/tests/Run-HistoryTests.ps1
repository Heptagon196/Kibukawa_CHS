$ErrorActionPreference = 'Stop'
$gamePath = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$seriesPath = (Resolve-Path (Join-Path $gamePath '../..')).Path
Add-Type -Path @(
    (Join-Path $seriesPath 'engine/history/src/HistoryBuffer.cs'),
    (Join-Path $seriesPath 'engine/history/src/ColoredHistoryLayout.cs'),
    (Join-Path $seriesPath 'engine/history/src/RuntimePolicy.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-v2/src/HistoryView.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-v2/src/HistoryState.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-v2/src/HistoryAudioMute.cs'),
    (Join-Path $PSScriptRoot 'HistoryStubs.cs'),
    (Join-Path $seriesPath 'engine/adapters/gmode-20050117/src/HistoryRuntime.cs'),
    (Join-Path $PSScriptRoot 'HistoryTests.cs')
)
[Kibu9ZenTests.HistoryTests]::Run($gamePath)
