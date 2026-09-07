param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$paths = & (Join-Path $workspace '../../tools/project_paths.ps1') -Project $workspace
if ($paths.Id -ne 'kibu4') { throw 'This installer is only for kibu4' }
$gameRoot = $paths.Game
if (!$CheckOnly -and (Get-Process kibu4 -ErrorAction SilentlyContinue)) { throw 'Exit kibu4 before installing.' }
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
$build = Get-Content -LiteralPath (Join-Path $workspace 'reports/bepinex_latest.json') -Raw | ConvertFrom-Json
$manifest = Get-Content -LiteralPath (Join-Path $workspace 'work/manifest.json') -Raw | ConvertFrom-Json
if (!$build.hooks_ready -or !$build.validation.hooks.hook_signatures_verified -or !$build.validation.dialogue.textConserved) { throw 'Build did not pass runtime validation' }
if ($build.validation.dialogue.widthOverflows -ne 0 -or $build.validation.dialogue.unreadScrolledGlyphs -ne 0) { throw 'Build contains text layout failures' }
if ((FileHash (Join-Path $workspace 'work/cache.json')) -ne $build.translation_sha256) { throw 'Translations changed since build' }
$packageRoot = [IO.Path]::GetFullPath((Join-Path $build.output 'package'))
if (!$packageRoot.StartsWith($workspace + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Package outside this project' }
if (!$build.zip.StartsWith($workspace + '\', [StringComparison]::OrdinalIgnoreCase) -or (FileHash $build.zip) -ne $build.zip_sha256) { throw 'ZIP path/checksum mismatch' }
foreach ($entry in $build.source_hashes.PSObject.Properties) {
    if ((FileHash (SafePath $paths.Series $entry.Name)) -ne $entry.Value) { throw "Source changed since build: $($entry.Name)" }
}
$originals = @{}
foreach ($entry in $manifest.game_hashes.PSObject.Properties) {
    $originals[$entry.Name] = $entry.Value
    if ((FileHash (SafePath $gameRoot $entry.Name)) -ne $entry.Value) { throw "Original file changed: $($entry.Name)" }
}
$files = @($build.package_files.PSObject.Properties)
if ($files.Name -notcontains 'BepInEx/plugins/Kibu4ZhCN/Kibu4ZhCN.dll') { throw 'Fourth-game translation plugin missing' }
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
if (Get-Process kibu4 -ErrorAction SilentlyContinue) { throw 'kibu4 started during preflight; installation cancelled' }
$backup = SafePath $workspace ('installations/update_' + $build.plugin_version + '_' + (Get-Date -Format 'yyyyMMdd_HHmmss_ffff'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$latest = Join-Path $workspace 'reports/installation_latest.json'
if (Test-Path -LiteralPath $latest) { Copy-Item -LiteralPath $latest -Destination (Join-Path $backup 'previous_installation.json') }
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
        $change = [ordered]@{ path=$entry.Name; previous_sha256=$previous; installed_sha256=$entry.Value }
        $changes.Add($change)
        # Log before the write so an interruption has a concrete recovery list.
        $changes | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backup 'changes.pending.json') -Encoding utf8
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        Copy-Item -LiteralPath (SafePath $packageRoot $entry.Name) -Destination $target -Force
        if ((FileHash $target) -ne $entry.Value) { throw "Installed checksum mismatch: $($entry.Name)" }
    }
    foreach ($entry in $files) {
        if ((FileHash $targets[$entry.Name]) -ne $entry.Value) { throw "Installed verification failed: $($entry.Name)" }
    }
    foreach ($entry in $manifest.game_hashes.PSObject.Properties) {
        if ((FileHash (SafePath $gameRoot $entry.Name)) -ne $entry.Value) { throw "Original file changed during install: $($entry.Name)" }
    }
} catch {
    $failure = $_
    for ($i=$changes.Count-1; $i -ge 0; $i--) {
        $change = $changes[$i]
        $target = SafePath $gameRoot $change.path
        if ($change.previous_sha256) {
            Copy-Item -LiteralPath (SafePath $backup $change.path) -Destination $target -Force
        } elseif (Test-Path -LiteralPath $target) {
            Remove-Item -LiteralPath $target -Force
        }
    }
    [ordered]@{status='rolled_back'; error=[string]$failure; changes=$changes; backup=$backup} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $backup 'failure.json') -Encoding utf8
    throw $failure
}
$report = [ordered]@{
    status='installed'; plugin_version=$build.plugin_version; installed_at=(Get-Date -Format o)
    game_root=$gameRoot; package_zip=$build.zip; package_sha256=$build.zip_sha256; backup=$backup
    files=$build.package_files; changes=@($changes.ToArray()); original_game_files_verified=$true; original_game_file_count=$originals.Count
    visual_verification='pending user'; game_launched=$false; automated_screenshots_enabled=$false
    script_slots=$build.script_slots; pixel_dialogue_font=$build.pixel_dialogue_font; help_pages=$build.help_pages; validation=$build.validation
}
$report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath (Join-Path $backup 'installation_report.json') -Encoding utf8
$report | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $latest -Encoding utf8
Write-Output "Installed $($build.plugin_version); changed $($changes.Count) files; verified $($originals.Count) original files. Game not launched."
Write-Output "Backup: $backup"
