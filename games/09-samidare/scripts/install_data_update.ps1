param([Parameter(Mandatory=$true)][string]$Release)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$seriesRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot '../..'))
$releaseRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot ('out/' + $Release)))
$expectedReleaseParent = [IO.Path]::GetFullPath((Join-Path $projectRoot 'out')).TrimEnd('\') + '\'
if (!$releaseRoot.StartsWith($expectedReleaseParent)) { throw 'Release escaped project output directory' }
$registry = Get-Content -LiteralPath (Join-Path $seriesRoot 'series.json') -Raw | ConvertFrom-Json
$registered = $registry.games.kibu9
if ([IO.Path]::GetFullPath((Join-Path $seriesRoot $registered.project)) -ne $projectRoot) {
    throw 'Unexpected project registration'
}
$gameRoot = [IO.Path]::GetFullPath((Join-Path $seriesRoot $registered.installation)).TrimEnd('\')
if (Get-Process kibu9,GmodeArchivesPlus_kibu9 -ErrorAction SilentlyContinue) {
    throw 'Game is running; close it before installing.'
}
if (!(Test-Path -LiteralPath (Join-Path $gameRoot 'BepInEx/plugins/Kibu9ZhCN/Kibu9ZhCN.dll'))) {
    throw 'Existing ninth-game 0.1.22 runtime is required'
}
$manifest = Get-Content -LiteralPath (Join-Path $releaseRoot 'data-update.json') -Raw | ConvertFrom-Json
$packageRoot = Join-Path $releaseRoot 'package'
$allowed = @(
    'BepInEx/plugins/Kibu9ZhCN/translations.bin',
    'BepInEx/plugins/Kibu9ZhCN/translations.json',
    'BepInEx/plugins/Kibu9ZhCN/dialogue-layout.bin',
    'BepInEx/plugins/Kibu9ZhCN/fonts/dialogue-16.bin',
    'BepInEx/plugins/Kibu9ZhCN/fonts/dialogue-16.png'
)
function HashFile([string]$path) {
    (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
}
$planned = @()
foreach ($entry in $manifest.files.PSObject.Properties) {
    if ($entry.Name -notin $allowed) { throw 'Unexpected payload' }
    $source = [IO.Path]::GetFullPath((Join-Path $packageRoot $entry.Name))
    $target = [IO.Path]::GetFullPath((Join-Path $gameRoot $entry.Name))
    if (!$source.StartsWith([IO.Path]::GetFullPath($packageRoot).TrimEnd('\') + '\') -or
        !$target.StartsWith($gameRoot + '\')) { throw 'Path escaped root' }
    if ((HashFile $source) -ne $entry.Value) { throw 'Payload hash mismatch' }
    $previous = if (Test-Path -LiteralPath $target) { HashFile $target } else { $null }
    if ($previous -ne $entry.Value) {
        $planned += [pscustomobject]@{
            relative=$entry.Name; source=$source; target=$target
            previous=$previous; expected=$entry.Value
        }
    }
}
$backupRoot = Join-Path $projectRoot ('backups/data_install_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
foreach ($item in $planned) {
    if ($item.previous) {
        $backup = Join-Path $backupRoot $item.relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $backup) -Force | Out-Null
        Copy-Item -LiteralPath $item.target -Destination $backup
        if ((HashFile $backup) -ne $item.previous) { throw 'Backup hash mismatch' }
    }
}
$planned | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $backupRoot 'changes.json') -Encoding utf8
try {
    foreach ($item in $planned) {
        Copy-Item -LiteralPath $item.source -Destination $item.target -Force
        if ((HashFile $item.target) -ne $item.expected) { throw 'Installed hash mismatch' }
    }
} catch {
    foreach ($item in $planned) {
        if ($item.previous) {
            Copy-Item -LiteralPath (Join-Path $backupRoot $item.relative) -Destination $item.target -Force
        } elseif (Test-Path -LiteralPath $item.target) {
            Remove-Item -LiteralPath $item.target
        }
    }
    throw
}
$report = [ordered]@{
    revision=$manifest.revision; changedFiles=$planned.Count; game=$gameRoot
    backup=$backupRoot; verified=$true; groups=$manifest.groups
}
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $releaseRoot 'installed.json') -Encoding utf8
Write-Output "Installed $($manifest.revision): $($planned.Count) changed files. Backup: $backupRoot"
