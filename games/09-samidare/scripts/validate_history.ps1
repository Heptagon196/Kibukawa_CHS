param([Parameter(Mandatory)][string]$PluginDll, [Parameter(Mandatory)][string]$GameDll, [string]$ReportPath)
$ErrorActionPreference = 'Stop'
Add-Type -Path (Join-Path $PSScriptRoot '../../../bin/ilspy/tools/net6.0/any/Mono.Cecil.dll')
$assembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly([IO.Path]::GetFullPath($PluginDll))
$game = [Mono.Cecil.AssemblyDefinition]::ReadAssembly([IO.Path]::GetFullPath($GameDll))
$evidence = [Collections.Generic.List[string]]::new()
function Fail([string]$message) { throw $message }
# BepInDependency's constructor signature does not always resolve without a full
# assembly resolver, so read the raw attribute blob for its GUID argument.
function AttributeText($attribute) {
    $blob = $attribute.GetBlob()
    return (-join ($blob | ForEach-Object { if ($_ -ge 32 -and $_ -lt 127) { [char]$_ } else { [char]0 } }))
}
try {
    if ($assembly.Name.Name -ne 'KibukawaHistory') { Fail 'Wrong history assembly name' }
    $plugin = $assembly.MainModule.GetType('Kibu9ZhCN.HistoryPlugin')
    if (!$plugin) { Fail 'History entry point missing' }
    if ($plugin.BaseType.FullName -ne 'KibukawaHistory.Gmode20050117HistoryRuntime') { Fail "Wrong history base: $($plugin.BaseType.FullName)" }
    $attribute = @($plugin.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInPlugin' })
    if ($attribute.Count -ne 1 -or $attribute[0].ConstructorArguments[0].Value -ne 'local.kibukawa.history') { Fail 'Wrong history plugin ID' }
    $dependency = @($plugin.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInDependency' })
    if ($dependency.Count -ne 1) { Fail 'History must declare exactly one BepInDependency' }
    if ((AttributeText $dependency[0]) -notmatch 'local\.kibu9\.zhcn') { Fail 'History must depend on the ninth-game text plugin' }
    $evidence.Add('history plugin identity and hard dependency verified')

    # Hook signatures resolved by name at runtime; a rename would silently drop capture.
    $runtime = $assembly.MainModule.GetType('KibukawaHistory.Gmode20050117HistoryRuntime')
    if (!$runtime) { Fail 'Ninth-game history runtime missing' }
    $hooks = @{
        'BeforeGame'          = @('System.Object', 'System.Boolean&')
        'AfterText'           = @('System.Object')
        'AfterBufferCleared'  = @('System.Object')
        'AfterLoad'           = @('System.Object')
        'AfterDrawnCharacter' = @('System.Object', 'System.Int32', 'System.Int32')
        'BeforeCanvasInput'   = @('System.Object', 'System.Int32', 'System.Int32')
        'BeforeUnityInput'    = @()
    }
    foreach ($name in $hooks.Keys) {
        $method = @($runtime.Methods | Where-Object { $_.Name -eq $name })
        if ($method.Count -ne 1) { Fail "History hook $name missing or ambiguous" }
        if (!$method[0].IsStatic) { Fail "History hook $name must be static" }
        $actual = @($method[0].Parameters | ForEach-Object { $_.ParameterType.FullName })
        $expected = $hooks[$name]
        if ($actual.Count -ne $expected.Count) { Fail "History hook $name arity mismatch" }
        for ($i = 0; $i -lt $expected.Count; $i++) {
            if ($actual[$i] -ne $expected[$i]) { Fail "History hook $name parameter $i is $($actual[$i])" }
        }
        $evidence.Add("history hook $name($($expected -join ',')) resolved")
    }

    $canvas = $game.MainModule.GetType('CanvasEx')
    if (!$canvas) { Fail 'CanvasEx missing from the game assembly' }
    foreach ($name in @('Bun_moji','Bun_iro','Bun_nagasa','NowNamae','Namae_nafuda','Namae_color','ColorTable','MainTask')) {
        $field = @($canvas.Fields | Where-Object { $_.Name -eq $name -and !$_.IsStatic })
        if ($field.Count -ne 1) { Fail "CanvasEx::$name missing" }
        $evidence.Add("CanvasEx.$name : $($field[0].FieldType.Name)")
    }
    $tracks = @($canvas.Fields | Where-Object { $_.Name -eq 'phraseTrack' -and $_.IsStatic })
    if ($tracks.Count -ne 1) { Fail 'CanvasEx::phraseTrack must be static' }
    $evidence.Add('CanvasEx.phraseTrack (static) bound')
    # Game() is the frame entry the pause skips; it must return bool.
    $gameMethod = @($canvas.Methods | Where-Object { $_.Name -eq 'Game' -and $_.Parameters.Count -eq 0 -and $_.ReturnType.FullName -eq 'System.Boolean' })
    if ($gameMethod.Count -ne 1) { Fail 'CanvasEx::Game() returning bool not found exactly once' }
    $evidence.Add('CanvasEx::Game() -> System.Boolean bound')
    foreach ($name in @('BUNSYOU', 'KeyFlush', 'ClearBunBuffer')) {
        $method = @($canvas.Methods | Where-Object { $_.Name -eq $name -and $_.Parameters.Count -eq 0 })
        if ($method.Count -ne 1) { Fail "CanvasEx::$name() not found exactly once" }
        $evidence.Add("CanvasEx::$name() bound")
    }
    # PERIOD and ASTERISK are multi-frame state machines. The history boundary must
    # be their one-shot ClearBunBuffer call, never either handler's postfix.
    $clearCallers = @()
    foreach ($method in $canvas.Methods | Where-Object { $_.HasBody }) {
        $calls = @($method.Body.Instructions | Where-Object {
            ($_.OpCode.Code -eq 'Call' -or $_.OpCode.Code -eq 'Callvirt') -and
            $_.Operand -ne $null -and $_.Operand.Name -eq 'ClearBunBuffer'
        })
        for ($i = 0; $i -lt $calls.Count; $i++) { $clearCallers += $method.Name }
    }
    $expectedClearCallers = @('BUNSYOU_ASTARISK','BUNSYOU_ASTARISK','BUNSYOU_PERIOD')
    if ((@($clearCallers | Sort-Object) -join ',') -ne (@($expectedClearCallers | Sort-Object) -join ',')) {
        Fail "Unexpected ClearBunBuffer callers: $($clearCallers -join ',')"
    }
    $init = @($runtime.Methods | Where-Object { $_.Name -eq 'InitializeHistory' })[0]
    $hookStrings = @($init.Body.Instructions | Where-Object { $_.OpCode.Code -eq 'Ldstr' } | ForEach-Object { [string]$_.Operand })
    if ($hookStrings -notcontains 'ClearBunBuffer') { Fail 'History runtime does not patch ClearBunBuffer' }
    if ($hookStrings -contains 'BUNSYOU_PERIOD' -or $hookStrings -contains 'BUNSYOU_ASTARISK') {
        Fail 'History runtime still patches a multi-frame text terminator'
    }
    $evidence.Add('ClearBunBuffer is the exclusive one-shot history boundary')
    foreach ($name in @('LoadScenario','LoadScenarioEx')) {
        $method = @($canvas.Methods | Where-Object { $_.Name -eq $name -and $_.Parameters.Count -eq 1 -and $_.Parameters[0].ParameterType.FullName -eq 'System.String' })
        if ($method.Count -ne 1) { Fail "CanvasEx::$name(System.String) not found exactly once" }
        $evidence.Add("CanvasEx::$name(System.String) bound")
    }
    $draw = @($canvas.Methods | Where-Object { $_.Name -eq 'DrawAdvString' -and $_.Parameters.Count -eq 5 })
    if ($draw.Count -ne 1) { Fail 'CanvasEx::DrawAdvString(StGraphics,int,int,int,int) not found exactly once' }
    if ($draw[0].Parameters[1].ParameterType.FullName -ne 'System.Int32') { Fail 'DrawAdvString second parameter is not int' }
    $evidence.Add('CanvasEx::DrawAdvString(StGraphics,int,int,int,int) bound')

    $stock = @($canvas.Methods | Where-Object { $_.Name -eq 'BunsyouStock' -and $_.Parameters.Count -eq 1 })[0]
    $directBodyRgb = $false
    for ($i = 0; $i -lt $stock.Body.Instructions.Count; $i++) {
        $instruction = $stock.Body.Instructions[$i]
        if ($instruction.OpCode.Code -ne 'Ldfld' -or $instruction.Operand.Name -ne 'Bun_iro') { continue }
        $window = @($stock.Body.Instructions[$i..([Math]::Min($i + 12, $stock.Body.Instructions.Count - 1))])
        $hasRgb = @($window | Where-Object { $_.Operand -ne $null -and $_.Operand.Name -eq 'NowMojiColor' }).Count -gt 0
        $storesInt = @($window | Where-Object { $_.OpCode.Code -eq 'Stelem_I4' }).Count -gt 0
        if ($hasRgb -and $storesInt) { $directBodyRgb = $true; break }
    }
    if (!$directBodyRgb) { Fail 'BunsyouStock no longer writes final NowMojiColor RGB directly into Bun_iro' }
    $evidence.Add('Bun_iro stores final body RGB; Namae_color remains a palette index')

    $command = @($canvas.Fields | Where-Object { $_.Name -eq 'command' -and $_.IsStatic -and $_.FieldType.FullName -eq 'System.String[]' })
    if ($command.Count -ne 1) { Fail 'CanvasEx::command static string[] missing' }
    $display = $game.MainModule.GetType('Socotra.UI.StDisplay')
    if (!$display) { Fail 'Socotra.UI.StDisplay missing' }
    foreach ($name in @('currentFrame','softKey1Label','keypadState')) {
        if (@($display.Fields | Where-Object { $_.Name -eq $name }).Count -ne 1) { Fail "StDisplay::$name missing" }
    }
    $base = $canvas.BaseType.Resolve()
    $processEvent = @($base.Methods | Where-Object {
        $_.Name -eq 'ProcessEvent' -and $_.Parameters.Count -eq 2 -and
        $_.Parameters[0].ParameterType.FullName -eq 'System.Int32' -and
        $_.Parameters[1].ParameterType.FullName -eq 'System.Int32'
    })
    if ($processEvent.Count -ne 1) { Fail 'CanvasEx base ProcessEvent(Int32,Int32) missing' }
    $evidence.Add('native SOFT1 event 21 fields and ProcessEvent route bound')

    if ($ReportPath) {
        $report = [ordered]@{ plugin_sha256=(Get-FileHash -LiteralPath $PluginDll -Algorithm SHA256).Hash.ToLowerInvariant()
                              game_assembly_sha256=(Get-FileHash -LiteralPath $GameDll -Algorithm SHA256).Hash.ToLowerInvariant()
                              evidence=$evidence; runtime_tested=$false }
        [IO.File]::WriteAllText([IO.Path]::GetFullPath($ReportPath), ($report | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    }
    Write-Output "PASS: ninth-game history identity, hooks and $($evidence.Count) reflection bindings verified offline."
} finally { $assembly.Dispose(); $game.Dispose() }
