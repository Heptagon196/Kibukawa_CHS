param([string]$Action = 'status', [Parameter(ValueFromRemainingArguments=$true)][string[]]$Remaining)
$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $python)) { throw 'Run setup.cmd first.' }
$pwshCommand = Get-Command pwsh -ErrorAction SilentlyContinue
if (!$pwshCommand) {
    $runtime = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime.json') -Raw | ConvertFrom-Json
    if (!(Test-Path -LiteralPath $runtime.pwsh)) { throw 'Install PowerShell 7 or update runtime.json.' }
    $env:PATH = [IO.Path]::GetDirectoryName($runtime.pwsh) + ';' + $env:PATH
}
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
if ($Action -eq 'bepinex') { $Action = 'build' }
& $python (Join-Path $PSScriptRoot 'tools/series.py') $Action @Remaining
exit $LASTEXITCODE
