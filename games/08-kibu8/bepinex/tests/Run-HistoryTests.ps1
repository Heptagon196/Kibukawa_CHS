$ErrorActionPreference = 'Stop'
$gamePath = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$seriesPath = (Resolve-Path (Join-Path $gamePath '../..')).Path
$testOut = Join-Path $gamePath 'bepinex/build/history-tests'
New-Item -ItemType Directory -Path $testOut -Force | Out-Null
$compiler = 'C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe'
$localTest = Join-Path $testOut 'History8Tests.exe'
& $compiler /nologo ("/out:" + $localTest) (Join-Path $PSScriptRoot 'History8Tests.cs') (Join-Path $seriesPath 'engine/adapters/gmode-20050817/src/HistoryCapture.cs') (Join-Path $seriesPath 'engine/adapters/gmode-v2/src/HistoryState.cs') (Join-Path $seriesPath 'engine/history/src/HistoryBuffer.cs') (Join-Path $seriesPath 'engine/history/src/RuntimePolicy.cs')
if ($LASTEXITCODE -ne 0) { throw 'History8 test compile failed' }
& $localTest
if ($LASTEXITCODE -ne 0) { throw 'History8 test failed' }
$sharedTest = Join-Path $testOut 'HistoryTests.exe'
& $compiler /nologo ("/out:" + $sharedTest) (Join-Path $seriesPath 'engine/history/tests/HistoryTests.cs') (Join-Path $seriesPath 'engine/history/src/HistoryBuffer.cs') (Join-Path $seriesPath 'engine/history/src/ColoredHistoryLayout.cs')
if ($LASTEXITCODE -ne 0) { throw 'Shared history test compile failed' }
& $sharedTest
if ($LASTEXITCODE -ne 0) { throw 'Shared history test failed' }
