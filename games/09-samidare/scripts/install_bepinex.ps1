param([switch]$CheckOnly)
# Install the ninth work's built release into the game directory.
#
# Modelled on games/07-otonari/scripts/install_bepinex.ps1: preflight every hash before writing
# anything, back up each file that changes, verify after writing, and roll back on failure. The
# ninth work never had an installer because it stayed disabled pending the user's real-machine
# test; this is the same contract the earlier works use, reading this project's build report.
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$seriesRoot = [IO.Path]::GetFullPath((Join-Path $project '../..'))
$registry = Get-Content -LiteralPath (Join-Path $seriesRoot 'series.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$registered = $registry.games.kibu9
if (!$registered -or [IO.Path]::GetFullPath((Join-Path $seriesRoot $registered.project)) -ne $project) {
    throw 'Unexpected kibu9 project registration'
}
$gameRoot = [IO.Path]::GetFullPath((Join-Path $seriesRoot $registered.installation))
if (!$CheckOnly -and (Get-Process GmodeArchivesPlus_kibu9 -ErrorAction SilentlyContinue)) {
    throw 'Exit the ninth game before installing.'
}

function FileHash([string]$path) { (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
function SafePath([string]$root, [string]$relative) {
    if (!$relative -or [IO.Path]::IsPathRooted($relative)) { throw 'Expected nonempty relative path' }
    $root = [IO.Path]::GetFullPath($root).TrimEnd('\')
    $path = [IO.Path]::GetFullPath((Join-Path $root $relative))
    if (!$path.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "Path outside root: $relative" }
    $ancestor = $path
    while ($ancestor) {
        if ((Test-Path -LiteralPath $ancestor) -and ((Get-Item -LiteralPath $ancestor).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Reparse point: $ancestor" }
        $ancestor = Split-Path -Parent $ancestor
    }
    return $path
}

$build = Get-Content -LiteralPath (Join-Path $project 'reports/build_latest.json') -Raw | ConvertFrom-Json
$manifest = Get-Content -LiteralPath (Join-Path $project 'work/manifest.json') -Raw | ConvertFrom-Json
if ($build.smoke) { throw 'The latest build is a smoke package, not a release' }
if (!$build.release_ready -or $build.lines -le 0) { throw 'Build did not pass release validation' }
if ($build.missing_required_plugins.Count -ne 0) { throw 'Build is missing a required plugin' }

$archive = [IO.Path]::GetFullPath((Join-Path $project $build.archive))
if (!$archive.StartsWith($project + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Archive outside this project' }
if (!(Test-Path -LiteralPath $archive)) { throw "Archive missing: $archive" }
if ((FileHash $archive) -ne $build.archive_sha256) { throw 'Archive checksum mismatch' }
$packageRoot = [IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $archive) 'package'))
if (!(Test-Path -LiteralPath $packageRoot)) { throw "Package directory missing: $packageRoot" }

$seriesConfig = Get-Content -LiteralPath (Join-Path $seriesRoot 'series.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($required in $seriesConfig.required_plugins.PSObject.Properties) {
    if (!$build.package_files.PSObject.Properties[$required.Value]) { throw "Missing mandatory plugin: $($required.Name)" }
}
if (!$build.package_files.PSObject.Properties['BepInEx/plugins/Kibu9ZhCN/Kibu9ZhCN.dll']) { throw 'Ninth-game translation plugin missing' }
if (!$build.package_files.PSObject.Properties['BepInEx/plugins/Kibu9ZhCN/translations.bin']) { throw 'Translation pack missing' }

# The 179 shipped game files must still be byte-identical: the patch may only add files.
$originals = @{}
foreach ($entry in $manifest.game_hashes.PSObject.Properties) {
    $originals[$entry.Name] = $entry.Value
    if ((FileHash (SafePath $gameRoot $entry.Name)) -ne $entry.Value) { throw "Original file changed: $($entry.Name)" }
}
$files = @($build.package_files.PSObject.Properties)
$targets = @{}
foreach ($entry in $files) {
    if ($originals.ContainsKey($entry.Name)) { throw "Package overwrites original: $($entry.Name)" }
    $targets[$entry.Name] = SafePath $gameRoot $entry.Name
    if ((FileHash (SafePath $packageRoot $entry.Name)) -ne $entry.Value) { throw "Package checksum mismatch: $($entry.Name)" }
}

if ($CheckOnly) {
    Write-Output "PASS: installation preflight; $($files.Count) payload files; $($originals.Count) original files; no files written."
    return
}
if (Get-Process GmodeArchivesPlus_kibu9 -ErrorAction SilentlyContinue) { throw 'The game started during preflight; installation cancelled' }

$backup = SafePath $project ('backups/install_' + $build.version + '_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$changes = [Collections.Generic.List[object]]::new()
try {
    foreach ($entry in $files) {
        $target = $targets[$entry.Name]
        $previous = $null
        if (Test-Path -LiteralPath $target) { $previous = FileHash $target }
        if ($previous -eq $entry.Value) { continue }
        if ($previous) {
            $copy = SafePath $backup $entry.Name
            New-Item -ItemType Directory -Path (Split-Path -Parent $copy) -Force | Out-Null
            Copy-Item -LiteralPath $target -Destination $copy
            if ((FileHash $copy) -ne $previous) { throw 'Backup checksum mismatch' }
        }
        $changes.Add([ordered]@{ path=$entry.Name; previous_sha256=$previous; installed_sha256=$entry.Value })
        # Log before the write so an interruption leaves a concrete recovery list.
        $changes | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backup 'changes.pending.json') -Encoding utf8
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath (SafePath $packageRoot $entry.Name) -Destination $target -Force
        if ((FileHash $target) -ne $entry.Value) { throw "Installed checksum mismatch: $($entry.Name)" }
    }
    $mismatches = 0
    foreach ($entry in $files) {
        if ((FileHash $targets[$entry.Name]) -ne $entry.Value) { $mismatches++ }
    }
    if ($mismatches -ne 0) { throw "Installed verification failed for $mismatches file(s)" }
    foreach ($entry in $manifest.game_hashes.PSObject.Properties) {
        if ((FileHash (SafePath $gameRoot $entry.Name)) -ne $entry.Value) { throw "Original file changed during install: $($entry.Name)" }
    }
} catch {
    $failure = $_
    for ($i = $changes.Count - 1; $i -ge 0; $i--) {
        $change = $changes[$i]
        $target = SafePath $gameRoot $change.path
        if ($change.previous_sha256) {
            Copy-Item -LiteralPath (SafePath $backup $change.path) -Destination $target -Force
        } elseif (Test-Path -LiteralPath $target) {
            Remove-Item -LiteralPath $target -Force
        }
    }
    [ordered]@{status='rolled_back'; error=[string]$failure; changes=$changes; backup=$backup} |
        ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $backup 'failure.json') -Encoding utf8
    throw $failure
}

$report = [ordered]@{
    schema = 1
    game = 'kibu9'
    version = $build.version
    installed_at = (Get-Date -Format o)
    destination = $gameRoot
    archive = $build.archive
    archive_sha256 = $build.archive_sha256
    installed_files = $files.Count
    hash_mismatches = 0
    original_game_unchanged = $true
    original_files_checked = $originals.Count
    runtime_tested = $false
    stage = 'installed_awaiting_user_test'
    backup = $backup.Substring($project.Length + 1).Replace('\', '/')
    backed_up_changed_files = $changes.Count
    lines = $build.lines
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $project 'reports/installation_latest.json') -Encoding utf8
Write-Output "Installed $($build.version); changed $($changes.Count) files; verified $($files.Count) payload and $($originals.Count) original files. Game not launched."
Write-Output "Backup: $backup"
