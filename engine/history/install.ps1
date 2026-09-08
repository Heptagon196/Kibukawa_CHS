param([string[]]$Games = @('kibu1','kibu2','kibu3','kibu4','kibu5'))
$ErrorActionPreference = 'Stop'
$series = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$config = Get-Content -LiteralPath (Join-Path $series 'series.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$manifest = Get-Content -LiteralPath (Join-Path $series 'out/history/manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$report = @()
foreach ($id in $Games) {
    if ($id -notin @('kibu1','kibu2','kibu3','kibu4','kibu5')) { throw "Unsupported game $id" }
    $entry = $config.games.$id
    if (!$entry -or !$entry.enabled) { throw "Game not enabled: $id" }
    $game = [IO.Path]::GetFullPath((Join-Path $series $entry.installation))
    if (!(Test-Path -LiteralPath (Join-Path $game "$id.exe")) -or !(Test-Path -LiteralPath (Join-Path $game 'BepInEx/core/BepInEx.dll'))) { throw "Game or BepInEx missing: $game" }
    $running = [bool](Get-Process -Name $id -ErrorAction SilentlyContinue)
    if ($running) { throw "Exit $id before replacing its native library." }
    $changes = @()
    foreach ($item in $manifest.files.$id.PSObject.Properties) {
        if ($item.Name -notin @('KibukawaHistory.dll')) { throw 'Unexpected payload path' }
        $source = Join-Path $series "out/history/$id/$($item.Name)"
        $expected = $item.Value
        if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw "Build checksum mismatch: $source" }
        $target = [IO.Path]::GetFullPath((Join-Path $game "BepInEx/plugins/KibukawaHistory/$($item.Name)"))
        if (!$target.StartsWith($game + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Target outside game' }
        $previous = $null
        if (Test-Path -LiteralPath $target) {
            $previous = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
            if ($previous -ne $expected) {
                $backup = Join-Path $series "out/history/backups/$id/$previous/$($item.Name)"
                New-Item -ItemType Directory -Path (Split-Path $backup -Parent) -Force | Out-Null
                Copy-Item -LiteralPath $target -Destination $backup -Force
            }
        }
        if ($previous -ne $expected) {
            New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
            Copy-Item -LiteralPath $source -Destination $target -Force
        }
        if ((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) { throw "Installed checksum mismatch: $target" }
        $changes += [ordered]@{path=$target; sha256=$expected; previous_sha256=$previous}
    }
    foreach ($relative in @('BepInEx/config/local.kibukawa.history.cfg','BepInEx/plugins/KibukawaHistory/native/KibukawaHistory.SDL3.dll','BepInEx/plugins/KibukawaHistory/native/SDL-LICENSE.txt')) {
        $obsolete = [IO.Path]::GetFullPath((Join-Path $game $relative))
        if (!$obsolete.StartsWith($game + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Cleanup outside game' }
        if (Test-Path -LiteralPath $obsolete) {
            $hash = (Get-FileHash -LiteralPath $obsolete).Hash
            $backup = Join-Path $series "out/history/backups/$id/$hash/$([IO.Path]::GetFileName($obsolete))"
            New-Item -ItemType Directory -Path (Split-Path $backup -Parent) -Force | Out-Null
            Copy-Item -LiteralPath $obsolete -Destination $backup -Force
            Remove-Item -LiteralPath $obsolete
        }
    }
    $report += [ordered]@{game=$id; version=$manifest.version; files=$changes; old_config_removed=$true}
    Write-Output "Installed $id history $($manifest.version); plugin checksum verified; obsolete native input files removed."
}
$report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $series 'out/history/installation.json') -Encoding UTF8
