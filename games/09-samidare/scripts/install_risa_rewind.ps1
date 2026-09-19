$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$reportPath = Join-Path $projectRoot 'reports/risa-rewind-latest.json'
$report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
if (Get-Process kibu9,GmodeArchivesPlus_kibu9 -ErrorAction SilentlyContinue) {
    throw 'Game is running; close it before installing the rewound save.'
}
function HashFile([string]$path) {
    (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}
$target = [IO.Path]::GetFullPath($report.target)
$staged = [IO.Path]::GetFullPath($report.staged)
$backup = [IO.Path]::GetFullPath($report.backup)
$currentHash = HashFile $target
if ($currentHash -ne $report.source_sha256 -and $currentHash -ne $report.staged_sha256) {
    throw 'Live SaveData changed after preparation'
}
if ((HashFile $backup) -ne $report.source_sha256) { throw 'Save backup hash mismatch' }
if ((HashFile $staged) -ne $report.staged_sha256) { throw 'Staged rewind hash mismatch' }
if ($currentHash -eq $report.source_sha256) {
    $temporary = $target + '.risa-rewind.tmp'
    Copy-Item -LiteralPath $staged -Destination $temporary -Force
    Move-Item -LiteralPath $temporary -Destination $target -Force
}
if ((HashFile $target) -ne $report.staged_sha256) { throw 'Installed rewind hash mismatch' }
$report.installed = $true
$report | Add-Member -NotePropertyName installed_at -NotePropertyValue (Get-Date).ToString('s') -Force
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding utf8
Write-Output ('Installed save rewind to '+$report.entry+'; backup: '+$backup)
