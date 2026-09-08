$ErrorActionPreference = 'Stop'
$series = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
Add-Type -Path (Join-Path $series 'bin/ilspy/tools/net6.0/any/Mono.Cecil.dll')
$config = Get-Content -LiteralPath (Join-Path $series 'series.json') -Raw -Encoding UTF8 | ConvertFrom-Json
function Method($type, $name, $signature) {
    $found = @($type.Methods | Where-Object { $_.Name -eq $name -and ($_.Parameters.ParameterType.FullName -join ',') -eq $signature })
    if ($found.Count -ne 1 -or !$found[0].HasBody) { throw "Missing method $($type.FullName).$name($signature)" }
}
foreach ($entry in $config.games.PSObject.Properties) {
    if (!$entry.Value.enabled) { continue }
    $game = [IO.Path]::GetFullPath((Join-Path $series $entry.Value.installation))
    $asm = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $game "$($entry.Name)_Data/Managed/Assembly-CSharp.dll"))
    try {
        $canvases = @($asm.MainModule.Types | Where-Object { $_.FullName -in @('CanvasEx','appli1.CanvasEx','appli2.CanvasEx') })
        if (!$canvases.Count) { throw 'No canvas' }
        foreach ($canvas in $canvases) {
            Method $canvas 'Script' ''
            Method $canvas 'ExeText' 'System.String,System.Int32'
            Method $canvas 'ProcessEvent' 'System.Int32,System.Int32'
            Method $canvas 'ClearKey' ''
            foreach ($name in @('Scene','Cmd','Key','KeyS','TextPos','TextLen','isPressSkipButton')) {
                if (!($canvas.Fields | Where-Object Name -eq $name)) { throw "Missing $name" }
            }
            foreach ($name in @('Key','KeyS','TextPos','TextLen')) {
                if (($canvas.Fields | Where-Object Name -eq $name).FieldType.FullName -ne 'System.SByte[]') { throw "Unexpected field type $name" }
            }
            # Verify captured text is emitted by the native text/speaker commands.
            $script = $canvas.NestedTypes | Where-Object Name -like '*Script*'
            if (!(($script.Methods | Where-Object Name -eq 'MoveNext').Body.Instructions | Where-Object { $_.Operand.Name -eq 'ExeText' })) { throw 'No script text calls' }
        }
        $display = $asm.MainModule.GetType('Socotra.UI.StDisplay')
        if (($display.Fields | Where-Object Name -eq 'KEY_SOFT1').Constant -ne 21) { throw 'Left softkey event code changed' }
        if (($display.Fields | Where-Object Name -eq 'KEY_UP').Constant -ne 17 -or ($display.Fields | Where-Object Name -eq 'KEY_DOWN').Constant -ne 19) { throw 'Direction key codes changed' }
        foreach ($name in @('currentFrame','softKey1Label','keypadState')) {
            if (!($display.Fields | Where-Object Name -eq $name)) { throw "Missing visible UI field $name" }
        }
        foreach ($canvas in $canvases) {
            foreach ($name in @('Truth','command','TextC','scColor')) {
                if (!($canvas.Fields | Where-Object Name -eq $name)) { throw "Missing history field $name" }
            }
        }
        Method ($asm.MainModule.GetType('AppliArchive')) 'Update' ''
        Write-Output "PASS $($entry.Name): $($canvases.Count) canvas adapters, text/input fields, left softkey and pause hooks"
    } finally { $asm.Dispose() }
}
