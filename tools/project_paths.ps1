param([Parameter(Mandatory=$true)][string]$Project)
$seriesRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$config = Get-Content -LiteralPath (Join-Path $seriesRoot 'series.json') -Raw | ConvertFrom-Json
if ($config.schema -ne 1) { throw 'Unsupported series configuration schema' }
$found = @($config.games.PSObject.Properties | Where-Object {
    [IO.Path]::GetFullPath((Join-Path $seriesRoot $_.Value.project)) -eq [IO.Path]::GetFullPath($Project)
})
if ($found.Count -ne 1 -or !$found[0].Value.enabled) { throw 'Project is missing, ambiguous or disabled in series.json' }
$entry = $found[0].Value
foreach ($value in @($entry.project, $entry.installation)) {
    if (!$value -or [IO.Path]::IsPathRooted($value)) { throw 'series.json paths must be relative' }
}
[pscustomobject]@{ Series=$seriesRoot; Game=[IO.Path]::GetFullPath((Join-Path $seriesRoot $entry.installation)); Id=$found[0].Name }
