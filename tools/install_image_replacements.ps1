param([ValidateSet('all','kibu1','kibu2','kibu3','kibu4','kibu5')][string]$Game='all',[switch]$CheckOnly)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$series=Get-Content -LiteralPath (Join-Path $root 'series.json') -Raw | ConvertFrom-Json
$out=Join-Path $root 'out/image-replacements-1.1.0'
$games=if($Game -eq 'all'){@($series.games.PSObject.Properties.Name)}else{@($Game)}
$plans=@()
foreach($id in $games){
    $dir=[IO.Path]::GetFullPath((Join-Path $root $series.games.$id.installation))
    $source=Join-Path $out "$id/package/BepInEx/plugins/KibukawaImageReplacements"
    $header=(Get-Content -LiteralPath (Join-Path $source 'image-replacements.tsv') -First 1).Split("`t")
    if($header.Count -ne 4 -or $header[0] -ne 'KIMG1' -or $header[1] -ne $id){throw "Invalid package for $id"}
    if(!(Test-Path -LiteralPath (Join-Path $dir "$id.exe")) -or !(Test-Path -LiteralPath (Join-Path $dir 'BepInEx/core/BepInEx.dll'))){throw "Missing game/framework: $dir"}
    if(Get-Process -Name $id -ErrorAction SilentlyContinue){throw "Exit $id before installing"}
    if((Get-FileHash -LiteralPath (Join-Path $dir "${id}_Data/Managed/Assembly-CSharp.dll")).Hash.ToLowerInvariant() -ne $header[2]){throw "$id assembly mismatch"}
    if((Get-FileHash -LiteralPath (Join-Path $dir "${id}_Data/StreamingAssets/scratchpad")).Hash.ToLowerInvariant() -ne $header[3]){throw "$id image archive mismatch"}
    & (Join-Path $out 'ManifestTests.exe') (Join-Path $source 'image-replacements.tsv')
    if($LASTEXITCODE -ne 0){throw "$id manifest/payload validation failed"}
    $destination=[IO.Path]::GetFullPath((Join-Path $dir 'BepInEx/plugins/KibukawaImageReplacements'))
    $plans+=[pscustomobject]@{Game=$id;Directory=$dir;Source=$source;Destination=$destination}
}
$report=@()
foreach($plan in $plans){
    if($CheckOnly){Write-Output "$($plan.Game) ready: $($plan.Destination)";continue}
    New-Item -ItemType Directory -Force -Path $plan.Destination | Out-Null
    foreach($file in Get-ChildItem -LiteralPath $plan.Source -Recurse -File){
        $relative=$file.FullName.Substring($plan.Source.Length+1)
        $destination=Join-Path $plan.Destination $relative
        New-Item -ItemType Directory -Force -Path ([IO.Path]::GetDirectoryName($destination)) | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
        if((Get-FileHash -LiteralPath $file.FullName).Hash -ne (Get-FileHash -LiteralPath $destination).Hash){throw "Installed checksum mismatch: $destination"}
    }
    $report+=[pscustomobject]@{game=$plan.Game;destination=$plan.Destination;installed=$true;runtime_visual_tested=$false}
    Write-Output "$($plan.Game) installed generic image replacement"
}
if(!$CheckOnly){$report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'installation-report.json') -Encoding utf8}
