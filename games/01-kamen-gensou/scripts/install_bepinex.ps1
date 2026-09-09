param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$paths = & (Join-Path $workspace '../../tools/project_paths.ps1') -Project $workspace
$gameRoot = $paths.Game
if (!$CheckOnly -and (Get-Process kibu1 -ErrorAction SilentlyContinue)) { throw 'Exit kibu1 before installing the update.' }
$build = Get-Content -LiteralPath (Join-Path $workspace 'reports/bepinex_latest.json') -Raw | ConvertFrom-Json
$manifest = Get-Content -LiteralPath (Join-Path $workspace 'work/manifest.json') -Raw | ConvertFrom-Json
function FileHash($path) { return (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() }
function SafePath($root, $relative) {
    $path = [IO.Path]::GetFullPath((Join-Path $root $relative))
    if (!$path.StartsWith($root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "Path outside root: $relative" }
    $ancestor = $path
    while ($ancestor -and $ancestor -ne $root) {
        if ((Test-Path -LiteralPath $ancestor) -and ((Get-Item -LiteralPath $ancestor).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Reparse point: $ancestor" }
        $ancestor = Split-Path -Parent $ancestor
    }
    return $path
}
$packageRoot = [IO.Path]::GetFullPath((Join-Path $build.output 'package'))
if (!$packageRoot.StartsWith($workspace + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Package outside workspace' }
if ((FileHash $build.zip) -ne $build.zip_sha256) { throw 'ZIP checksum mismatch' }
if ((FileHash (Join-Path $workspace 'work/cache.json')) -ne $build.reproducibility.translation_sha256) { throw 'Translations changed since build' }
$seriesRoot = [IO.Path]::GetFullPath((Join-Path $workspace '../..'))
foreach ($item in $build.reproducibility.source_hashes.PSObject.Properties) {
    if ((FileHash (SafePath $seriesRoot $item.Name)) -ne $item.Value) { throw "Build source changed: $($item.Name)" }
}
$originals = @{}
foreach ($item in $manifest.game_hashes.PSObject.Properties) {
    $originals[$item.Name.Replace('\','/')] = $item.Value
    if ((FileHash (Join-Path $gameRoot $item.Name)) -ne $item.Value) { throw "Original file changed: $($item.Name)" }
}
foreach ($item in $build.package_files.PSObject.Properties) {
    $null = SafePath $gameRoot $item.Name
    if ($originals.ContainsKey($item.Name.Replace('\','/'))) { throw "Package contains original game file: $($item.Name)" }
    if ((FileHash (SafePath $packageRoot $item.Name)) -ne $item.Value) { throw "Package checksum mismatch: $($item.Name)" }
}
if ($CheckOnly) { Write-Output "Install preflight passed; no files written: $gameRoot"; return }
$backup = Join-Path $workspace ('installations/update_' + $build.plugin_version + '_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
$latest = Join-Path $workspace 'reports/installation_latest.json'
$obsolete = @()
if (Test-Path -LiteralPath $latest) {
    $previousReport = Get-Content -LiteralPath $latest -Raw | ConvertFrom-Json
    foreach ($item in $previousReport.files.PSObject.Properties) {
        if ($build.package_files.PSObject.Properties.Name -contains $item.Name) { continue }
        if (!$item.Name.StartsWith('BepInEx/plugins/Kibu1ZhCN/') -and !$item.Name.StartsWith('BepInEx/licenses/')) { continue }
        $target = SafePath $gameRoot $item.Name
        if (Test-Path -LiteralPath $target) {
            if ((FileHash $target) -ne $item.Value) { throw "Obsolete plugin file was modified: $($item.Name)" }
            $obsolete += $item
        }
    }
}
New-Item -ItemType Directory -Path $backup -Force | Out-Null
if (Test-Path -LiteralPath $latest) { Copy-Item -LiteralPath $latest -Destination (Join-Path $backup 'previous_installation.json') }
$changes = @()
foreach ($item in $build.package_files.PSObject.Properties) {
    $target = SafePath $gameRoot $item.Name
    $previous = $null
    if (Test-Path -LiteralPath $target) { $previous = FileHash $target }
    if ($previous -eq $item.Value) { continue }
    if ($previous) {
        $copy = SafePath $backup $item.Name
        New-Item -ItemType Directory -Path (Split-Path $copy -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $target -Destination $copy
    }
    New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
    Copy-Item -LiteralPath (SafePath $packageRoot $item.Name) -Destination $target -Force
    $changes += [ordered]@{ path=$item.Name; previous_sha256=$previous; installed_sha256=$item.Value }
}
foreach ($item in $obsolete) {
    $target = SafePath $gameRoot $item.Name
    $copy = SafePath $backup $item.Name
    New-Item -ItemType Directory -Path (Split-Path $copy -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $target -Destination $copy
    Remove-Item -LiteralPath $target
    $changes += [ordered]@{ path=$item.Name; previous_sha256=$item.Value; installed_sha256=$null; action='removed obsolete plugin file' }
}
foreach ($item in $build.package_files.PSObject.Properties) {
    if ((FileHash (Join-Path $gameRoot $item.Name)) -ne $item.Value) { throw "Installed checksum mismatch: $($item.Name)" }
}
foreach ($item in $manifest.game_hashes.PSObject.Properties) {
    if ((FileHash (Join-Path $gameRoot $item.Name)) -ne $item.Value) { throw "Original file changed: $($item.Name)" }
}
$report = [ordered]@{
    status='installed'; plugin_version=$build.plugin_version; installed_at=(Get-Date -Format o)
    game_root=$gameRoot; package_zip=$build.zip; package_sha256=$build.zip_sha256; backup=$backup
    files=$build.package_files; changes=$changes; removed_files=@($obsolete.Name); original_game_files_verified=$true; original_game_file_count=$originals.Count
    visual_verification='pending user'; game_launched=$false; automated_screenshots_enabled=$false
    dialogue_width=$build.dialogue_width; pixel_dialogue_font=$build.pixel_dialogue_font; help_pages=$build.help_pages
    dialogue_reflow=$build.dialogue_reflow; text_layout=$build.text_layout
}
$report | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath (Join-Path $backup 'installation_report.json') -Encoding utf8
$report | ConvertTo-Json -Depth 15 | Set-Content -LiteralPath $latest -Encoding utf8
Write-Output "Installed $($build.plugin_version); changed $($changes.Count) files; verified $($originals.Count) original files; game not launched."
Write-Output "Backup: $backup"
