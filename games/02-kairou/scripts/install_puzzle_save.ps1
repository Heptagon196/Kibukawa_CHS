$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$paths = & (Join-Path $workspace '../../tools/project_paths.ps1') -Project $workspace
$target = [IO.Path]::GetFullPath((Join-Path $paths.Game 'save/SaveData2'))
$reportPath = Join-Path $workspace 'reports/puzzle-save-latest.json'
$report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
function Hash($path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
if ($report.target -ne $target -or $report.installed) { throw 'Prepared save target/state mismatch' }
foreach ($path in @($report.backup,$report.staged)) {
    $absolute = [IO.Path]::GetFullPath($path)
    if (!$absolute.StartsWith((Join-Path $workspace 'installations')+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Backup/stage outside installation records' }
}
foreach ($path in @($target,$report.backup,$report.staged)) {
    $ancestor = [IO.Path]::GetFullPath($path)
    while ($ancestor) {
        if ((Get-Item -LiteralPath $ancestor).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse point in save paths' }
        $ancestor = Split-Path -Parent $ancestor
    }
}
if (Get-Process kibu2 -ErrorAction SilentlyContinue) { throw 'Exit kibu2 before changing the save.' }
if ((Hash $target) -ne $report.source_sha256 -or (Hash $report.backup) -ne $report.source_sha256 -or (Hash $report.staged) -ne $report.staged_sha256) { throw 'Save changed or backup/stage checksum mismatch' }
$temporary = $target + '.kibu2-rewind.tmp'
if (Test-Path -LiteralPath $temporary) { throw 'Unexpected existing staged save beside target' }
[IO.File]::WriteAllBytes($temporary,[IO.File]::ReadAllBytes($report.staged))
if ((Hash $temporary) -ne $report.staged_sha256) { throw 'Temporary save checksum mismatch' }
Move-Item -LiteralPath $temporary -Destination $target -Force
if ((Hash $target) -ne $report.staged_sha256) { throw 'Installed save checksum mismatch; original backup preserved' }
$report.installed = $true
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding utf8
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path (Split-Path -Parent $report.backup) 'report.json') -Encoding utf8
Write-Output ('Installed test rewind to scn7:13927; original backup: '+$report.backup)
