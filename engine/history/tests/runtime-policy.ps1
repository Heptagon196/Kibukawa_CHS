$ErrorActionPreference = 'Stop'
$series = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$out = Join-Path $series 'out/history/policy-tests'
New-Item -ItemType Directory -Force -Path $out | Out-Null
$core = Join-Path $series '../BepInEx/core'
Get-ChildItem -LiteralPath $core -Filter '*.dll' | Copy-Item -Destination $out -Force
$exe = Join-Path $out 'RuntimePolicyTests.exe'
& 'C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe' /nologo ("/r:" + (Join-Path $core '0Harmony.dll')) ("/out:" + $exe) (Join-Path $PSScriptRoot '../src/RuntimePolicy.cs') (Join-Path $PSScriptRoot '../src/HistoryBuffer.cs') (Join-Path $PSScriptRoot 'RuntimePolicyTests.cs')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $exe
exit $LASTEXITCODE
