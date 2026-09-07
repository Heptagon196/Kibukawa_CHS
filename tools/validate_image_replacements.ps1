param([string]$Game='all')
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Add-Type -Path (Join-Path $root 'bin/ilspy/tools/net6.0/any/Mono.Cecil.dll')
$series=Get-Content -LiteralPath (Join-Path $root 'series.json') -Raw | ConvertFrom-Json
$games=if($Game -eq 'all'){@($series.games.PSObject.Properties.Name)}else{@($Game)}
foreach($id in $games){
    $dir=[IO.Path]::GetFullPath((Join-Path $root $series.games.$id.installation))
    $assembly=[Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $dir "${id}_Data/Managed/Assembly-CSharp.dll"))
    $pluginPath=Join-Path $root "out/image-replacements-1.1.0/$id/package/BepInEx/plugins/KibukawaImageReplacements"
    $plugin=[Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $pluginPath 'KibukawaImageReplacements.dll'))
    try {
        $entries=(Get-Content -LiteralPath (Join-Path $pluginPath 'image-replacements.tsv')) | Select-Object -Skip 1
        foreach($line in $entries){
            $fields=$line.Split("`t");$type=$assembly.MainModule.GetType($fields[1])
            $read=@($type.Methods | Where-Object { $_.Name -eq 'ReadImg' -and ($_.Parameters.ParameterType.FullName -join ',') -eq 'System.Int32' })
            if($read.Count -ne 1 -or !$read[0].HasBody -or $read[0].ReturnType.FullName -ne 'Socotra.UI.Image'){throw "Invalid native image route: $id $line"}
        }
        $image=$assembly.MainModule.GetType('Socotra.UI.Image')
        foreach($signature in @('CreateImage:System.Int32,System.Int32','get_Texture:','set_Texture:UnityEngine.Texture','set_IsDisposable:System.Boolean','Dispose:')){
            $parts=$signature.Split(':');$methods=@($image.Methods | Where-Object {$_.Name -eq $parts[0] -and ($_.Parameters.ParameterType.FullName -join ',') -eq $parts[1]})
            if($methods.Count -ne 1){throw "Missing image lifecycle API: $signature"}
        }
        $bad=@($plugin.MainModule.Types.Methods | Where-Object HasBody | ForEach-Object {$_.Body.Instructions} | Where-Object { [string]$_.Operand -match 'MediaManager|MediaImage|UniGif|LoadImage' })
        if($bad.Count){throw 'Replacement plugin must not call the native byte-image decoder'}
        Write-Output "$id PASS: ReadImg routes, texture lifecycle, no encoded-image decoder hooks"
    } finally {$assembly.Dispose();$plugin.Dispose()}
}
