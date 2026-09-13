param(
    [Parameter(Mandatory)][string]$PluginDll,
    [string]$GameAssembly = '',
    [string]$ReportPath = ''
)
$ErrorActionPreference = 'Stop'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
if (!$GameAssembly) {
    $GameAssembly = Join-Path $repo '../../GmodeArchivesPlus_kibu8/kibu8_Data/Managed/Assembly-CSharp.dll'
}
$GameAssembly = [IO.Path]::GetFullPath($GameAssembly)
$PluginDll = [IO.Path]::GetFullPath($PluginDll)
Add-Type -Path (Join-Path $repo 'bin/ilspy/tools/net6.0/any/Mono.Cecil.dll')
$game = $null
$pluginAssembly = $null
$evidence = [Collections.Generic.List[object]]::new()
function Require-Type([string]$Name) {
    $type = $game.MainModule.GetType($Name)
    if (!$type) { throw "Game type missing: $Name" }
    return $type
}
function Require-Method([string]$Owner, [string]$Name, [string]$ReturnType, [string[]]$Parameters, [bool]$Static = $false) {
    $type = Require-Type $Owner
    $matches = @($type.Methods | Where-Object {
        $_.Name -eq $Name -and $_.ReturnType.FullName -eq $ReturnType -and
        $_.IsStatic -eq $Static -and
        (@($_.Parameters | ForEach-Object { $_.ParameterType.FullName }) -join '|') -eq ($Parameters -join '|')
    })
    if ($matches.Count -ne 1 -or !$matches[0].HasBody) {
        throw "Game method signature/body mismatch: $Owner::$Name($($Parameters -join ',')) -> $ReturnType; static=$Static"
    }
    $evidence.Add([ordered]@{ kind='method'; signature=$matches[0].FullName; static=$Static; instructions=$matches[0].Body.Instructions.Count })
    return $matches[0]
}
function Require-Field([string]$Owner, [string]$Name, [string]$FieldType, [bool]$Static = $false) {
    $type = Require-Type $Owner
    $matches = @($type.Fields | Where-Object { $_.Name -eq $Name -and $_.FieldType.FullName -eq $FieldType -and $_.IsStatic -eq $Static })
    if ($matches.Count -ne 1) { throw "Game field mismatch: $Owner::$Name : $FieldType; static=$Static" }
    $evidence.Add([ordered]@{ kind='field'; signature=$matches[0].FullName; static=$Static })
}
try {
    $game = [Mono.Cecil.AssemblyDefinition]::ReadAssembly($GameAssembly)
    foreach ($name in @('BUNSYOU','BUNSYOU_ROLL','BUNSYOU_SCROLL','INFO')) {
        $null = Require-Method 'CanvasEx' $name 'System.Void' @()
    }
    $null = Require-Method 'CanvasEx' 'StringRead' 'System.String' @()
    foreach ($name in @('LoadScenario','LoadResScenario')) {
        $null = Require-Method 'CanvasEx' $name 'System.Boolean' @('System.String')
    }
    foreach ($name in @('DrawAdvString','DrawAdvStringRoll')) {
        $null = Require-Method 'CanvasEx' $name 'System.Void' @('Socotra.UI.StGraphics','System.Int32','System.Int32','System.Int32','System.Int32','System.Int32')
    }
    foreach ($page in @('PaintMenu','PaintDocomo','PaintADV','PaintList')) { $null = Require-Method 'CanvasEx' $page 'System.Void' @('Socotra.UI.StGraphics') }
    $null = Require-Method 'CanvasEx' 'DrawAdvCommand' 'System.Void' @('Socotra.UI.StGraphics','System.Int32','System.Int32','System.Int32','System.Int32')
    $null = Require-Method 'CanvasEx' 'DrawAdvCommandCenter' 'System.Void' @('Socotra.UI.StGraphics','System.Int32','System.Int32','System.Int32')
    $null = Require-Method 'CanvasEx' 'PaintMain_info' 'System.Collections.IEnumerator' @('Socotra.UI.StGraphics')
    $canvas = Require-Type 'CanvasEx'
    $shadow = Require-Method 'CanvasEx' 'Ds_sub' 'System.Void' @('Socotra.UI.StGraphics','System.String','System.Int32','System.Int32')
    if (!($shadow.Body.Instructions | Where-Object { $_.Operand -and $_.Operand.ToString() -like '*Socotra.StString::Substring*' })) {
        throw 'Ds_sub no longer uses the verified glyph-splitting path'
    }
    $infoMachines = @($canvas.NestedTypes | Where-Object { $_.Name -like '<PaintMain_info>d__*' })
    if ($infoMachines.Count -ne 1) { throw 'INFO state machine must resolve uniquely' }
    $infoMachine = $infoMachines[0].FullName
    $null = Require-Method $infoMachine 'MoveNext' 'System.Boolean' @()
    Require-Field $infoMachine '<>4__this' 'CanvasEx'
    Require-Field $infoMachine 'g' 'Socotra.UI.StGraphics'
    $null = Require-Method 'Socotra.UI.StGraphics' 'DrawCharImpl' 'System.Void' @('System.Char[]','System.Int32','System.Int32')
    $null = Require-Method 'Socotra.UI.StGraphics' 'DrawString' 'System.Void' @('System.String','System.Int32','System.Int32')
    foreach ($name in @('RenderStart','RenderEnd')) { $null = Require-Method 'Socotra.UI.StGraphics' $name 'System.Void' @() }
    foreach ($entry in @(
        @('currentFont','Socotra.UI.StFont'), @('renderTexture','UnityEngine.RenderTexture'),
        @('currentColor','UnityEngine.Color'), @('drawOrigin','UnityEngine.Vector2')
    )) { Require-Field 'Socotra.UI.StGraphics' $entry[0] $entry[1] }
    Require-Field 'Socotra.UI.StFont' 'font' 'UnityEngine.Font'
    $null = Require-Method 'Socotra.UI.StFont' 'get_Size' 'System.Single' @()
    $null = Require-Method 'Socotra.UI.StFont' 'get_Font' 'UnityEngine.Font' @()
    foreach ($name in @('FWidth','FHeight','FAscent','FDocomo')) { Require-Field 'CanvasEx' $name 'System.Int32' $true }
    foreach ($entry in @(
        @('Script','System.SByte[]'), @('Pos','System.Int32'), @('LabelIndex','System.Int32[]'),
        @('NowStockingGyou','System.Int32'), @('BunsyouGun_gyousuu','System.SByte'), @('BunsyouGun_max_mojisuu','System.SByte'),
        @('info_struct_moji','System.String'), @('info_struct_mojiretu','System.SByte[]'),
        @('info_struct_iro','System.SByte[]'), @('info_struct_zenkaku_suu','System.Int32')
    )) { Require-Field 'CanvasEx' $entry[0] $entry[1] }
    foreach ($prefix in @('bg_itigyougun_','rollitigyougun_')) {
        foreach ($entry in @(
            @('mojiretu','System.String[]'), @('zenkakusuu','System.SByte[]'), @('color','System.SByte[][]'),
            @('control','System.SByte[][]'), @('rubi_index','System.Int32[][]'), @('rubisuu','System.SByte[]')
        )) { Require-Field 'CanvasEx' ($prefix+$entry[0]) $entry[1] }
    }
    # Confirm the surprising SCROLL control destination against actual IL, not its field name.
    $scroll = Require-Method 'CanvasEx' 'BUNSYOU_SCROLL' 'System.Void' @()
    $scrollControl = @($scroll.Body.Instructions | Where-Object {
        $_.OpCode.Name -eq 'ldfld' -and $_.Operand -is [Mono.Cecil.FieldReference] -and
        $_.Operand.FullName -eq 'System.SByte[][] CanvasEx::bg_itigyougun_control'
    })
    if (!$scrollControl.Count) { throw 'SCROLL no longer reads bg_itigyougun_control; review its binding' }
    $pluginAssembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly($PluginDll)
    $entries = @($pluginAssembly.MainModule.Types | Where-Object {
        @($_.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInPlugin' }).Count -gt 0
    })
    if ($entries.Count -ne 1) { throw 'Expected exactly one BepInPlugin entry point' }
    $entry = $entries[0]
    $pluginAttrs = @($entry.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInPlugin' })
    $processAttrs = @($entry.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInProcess' })
    if ($pluginAttrs.Count -ne 1 -or $pluginAttrs[0].ConstructorArguments[0].Value -ne 'local.kibu8.zhcn') { throw 'Wrong runtime plugin ID' }
    if ($processAttrs.Count -ne 1 -or $processAttrs[0].ConstructorArguments[0].Value -ne 'kibu8.exe') { throw 'Wrong runtime process filter' }
    if ($entry.BaseType.FullName -ne 'Kibukawa.Engine.Gmode20050817.CanvasRuntime') { throw 'Entry point must use the 20050817 adapter' }
    if ($pluginAssembly.MainModule.GetType($entry.BaseType.FullName).BaseType.FullName -ne 'BepInEx.BaseUnityPlugin') { throw 'Adapter must extend BaseUnityPlugin' }
    if ($pluginAssembly.MainModule.AssemblyReferences.Name -contains 'Kibu1ZhCN') { throw 'Runtime must not depend on the first-game plugin assembly' }
    $report = [ordered]@{
        schema=1; status='pass'; validation='offline Cecil binding validation; not an in-game visual test';
        game_assembly=$GameAssembly; game_sha256=(Get-FileHash -LiteralPath $GameAssembly -Algorithm SHA256).Hash.ToLowerInvariant();
        plugin_dll=$PluginDll; plugin_sha256=(Get-FileHash -LiteralPath $PluginDll -Algorithm SHA256).Hash.ToLowerInvariant();
        entry_type=$entry.FullName; plugin_id=$pluginAttrs[0].ConstructorArguments[0].Value;
        process=$processAttrs[0].ConstructorArguments[0].Value; info_state_machine=$infoMachine; bindings=@($evidence.ToArray())
    }
    if ($ReportPath) {
        $reportFile=[IO.Path]::GetFullPath($ReportPath)
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($reportFile)) | Out-Null
        [IO.File]::WriteAllText($reportFile,($report|ConvertTo-Json -Depth 8),[Text.UTF8Encoding]::new($false))
    }
    Write-Output "PASS: eighth-game runtime identity and $($evidence.Count) real assembly bindings verified offline."
} finally {
    if ($pluginAssembly) { $pluginAssembly.Dispose() }
    if ($game) { $game.Dispose() }
}
