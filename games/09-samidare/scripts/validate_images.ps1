param(
    [Parameter(Mandatory=$true)][string]$PluginDll,
    [Parameter(Mandatory=$true)][string]$GameDll,
    [Parameter(Mandatory=$true)][string]$ReportPath
)
$ErrorActionPreference='Stop'
$seriesPath=(Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
Add-Type -Path (Join-Path $seriesPath 'bin/ilspy/tools/net6.0/any/Mono.Cecil.dll')
function Fail([string]$message) { throw $message }
$plugin=[Mono.Cecil.AssemblyDefinition]::ReadAssembly([IO.Path]::GetFullPath($PluginDll))
$game=[Mono.Cecil.AssemblyDefinition]::ReadAssembly([IO.Path]::GetFullPath($GameDll))
try {
    $type=$plugin.MainModule.Types | Where-Object FullName -eq 'Kibu9ZhCN.Images.ImageReplacementPlugin'
    if($null -eq $type) { Fail 'Image replacement plugin type missing' }
    $process=@($type.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInProcess' })
    if($process.Count -ne 1 -or $process[0].ConstructorArguments[0].Value -ne 'kibu9.exe') { Fail 'Wrong image plugin process restriction' }
    $meta=@($type.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInPlugin' })
    if($meta.Count -ne 1 -or $meta[0].ConstructorArguments[0].Value -ne 'heptagon.kibukawa9.imagereplacements.zhcn' -or $meta[0].ConstructorArguments[2].Value -ne '1.0.1') { Fail 'Wrong image plugin identity/version' }

    $canvas=$game.MainModule.Types | Where-Object FullName -eq 'CanvasEx'
    if($null -eq $canvas) { Fail 'CanvasEx missing' }
    $load=$canvas.Methods | Where-Object FullName -eq 'Socotra.UI.Image CanvasEx::LoadGraphic(System.String)'
    $title=$canvas.Methods | Where-Object FullName -eq 'System.Void CanvasEx::Game_title()'
    $paint=$canvas.Methods | Where-Object FullName -eq 'System.Void CanvasEx::PaintTitle(Socotra.UI.StGraphics)'
    if($null -eq $load -or $load.IsStatic) { Fail 'LoadGraphic binding changed' }
    if($null -eq $title -or $title.IsStatic) { Fail 'Game_title binding changed' }
    if($null -eq $paint -or $paint.IsStatic) { Fail 'PaintTitle binding changed' }
    foreach($spec in @(@('Image_Haikei','Socotra.UI.Image',$true),@('Image_Kyara','Socotra.UI.Image[]',$true),@('HaikeiFileNameBackup','System.String',$false))) {
        $field=$canvas.Fields | Where-Object Name -eq $spec[0]
        if($null -eq $field -or $field.FieldType.FullName -ne $spec[1] -or $field.IsStatic -ne $spec[2]) { Fail "Invalid title field $($spec[0])" }
    }
    $body=$title.Body.Instructions | ForEach-Object ToString
    if(!($body -match 'resource:///title.gif')) { Fail 'Native title resource changed' }
    if(!($body -match 'menu00.gif') -or !($body -match 'menu01.gif')) { Fail 'Native title menu resources changed' }
    $draws=@()
    for($i=2;$i -lt $paint.Body.Instructions.Count;$i++) {
        $ins=$paint.Body.Instructions[$i]
        if($ins.Operand -and $ins.Operand.ToString() -eq 'System.Void Socotra.UI.StGraphics::DrawImage(Socotra.UI.Image,System.Int32,System.Int32)') {
            $x=$paint.Body.Instructions[$i-2];$y=$paint.Body.Instructions[$i-1]
            if($x.OpCode.Name -like 'ldc.i4*' -and [int]$x.Operand -eq 131) { $draws += [int]$y.Operand }
        }
    }
    if(($draws -join ',') -ne '137,171') { Fail "Native title menu coordinates changed: $($draws -join ',')" }
    $help=$game.MainModule.Types | Where-Object FullName -eq 'HowToPlayDialog'
    if($null -eq $help) { Fail 'HowToPlayDialog missing' }
    $guide=@($help.Fields | Where-Object { $_.Name -eq 'guideImage' -and $_.FieldType.FullName -eq 'UnityEngine.UI.Image' })
    $page=@($help.Fields | Where-Object { $_.Name -eq 'nowPage' -and $_.FieldType.FullName -eq 'System.Int32' })
    $change=@($help.Methods | Where-Object { $_.Name -eq 'ChangePage' -and $_.Parameters.Count -eq 1 -and $_.Parameters[0].ParameterType.FullName -eq 'System.Int32' })
    if($guide.Count -ne 1 -or $page.Count -ne 1 -or $change.Count -ne 1) { Fail 'HowToPlayDialog help-page binding changed' }
    $report=[ordered]@{
        plugin_sha256=(Get-FileHash -LiteralPath $PluginDll -Algorithm SHA256).Hash.ToLowerInvariant()
        game_assembly_sha256=(Get-FileHash -LiteralPath $GameDll -Algorithm SHA256).Hash.ToLowerInvariant()
        evidence=@('BepInPlugin/BepInProcess identity','CanvasEx.LoadGraphic(string)','CanvasEx.Game_title()','title image fields','resource:///title.gif','menu00/menu01 at (131,137)/(131,171)','HowToPlayDialog.guideImage','HowToPlayDialog.nowPage','HowToPlayDialog.ChangePage(int)')
        runtime_tested=$false
    }
    [IO.File]::WriteAllText([IO.Path]::GetFullPath($ReportPath),($report|ConvertTo-Json -Depth 5),[Text.UTF8Encoding]::new($false))
    Write-Output 'PASS: ninth-game image plugin identity, 6 title bindings and 3 help-page bindings verified offline.'
} finally { $plugin.Dispose(); $game.Dispose() }
