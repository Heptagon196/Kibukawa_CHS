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
        'AfterLine'           = @('System.Object')
        'AfterLoad'           = @('System.Object')
        'AfterDrawnCharacter' = @('System.Object', 'System.Int32', 'System.Int32')
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
    foreach ($name in @('BUNSYOU', 'KeyFlush')) {
        $method = @($canvas.Methods | Where-Object { $_.Name -eq $name -and $_.Parameters.Count -eq 0 })
        if ($method.Count -ne 1) { Fail "CanvasEx::$name() not found exactly once" }
        $evidence.Add("CanvasEx::$name() bound")
    }
    # The utterance terminators (buffer clears) and script loaders the history anchors on.
    foreach ($name in @('BUNSYOU_PERIOD','BUNSYOU_ASTARISK')) {
        $method = @($canvas.Methods | Where-Object { $_.Name -eq $name -and $_.Parameters.Count -eq 0 })
        if ($method.Count -ne 1) { Fail "CanvasEx::$name() not found exactly once" }
        $evidence.Add("CanvasEx::$name() bound")
    }
    foreach ($name in @('LoadScenario','LoadScenarioEx')) {
        $method = @($canvas.Methods | Where-Object { $_.Name -eq $name -and $_.Parameters.Count -eq 1 -and $_.Parameters[0].ParameterType.FullName -eq 'System.String' })
        if ($method.Count -ne 1) { Fail "CanvasEx::$name(System.String) not found exactly once" }
        $evidence.Add("CanvasEx::$name(System.String) bound")
    }
    $draw = @($canvas.Methods | Where-Object { $_.Name -eq 'DrawAdvString' -and $_.Parameters.Count -eq 5 })
    if ($draw.Count -ne 1) { Fail 'CanvasEx::DrawAdvString(StGraphics,int,int,int,int) not found exactly once' }
    if ($draw[0].Parameters[1].ParameterType.FullName -ne 'System.Int32') { Fail 'DrawAdvString second parameter is not int' }
    $evidence.Add('CanvasEx::DrawAdvString(StGraphics,int,int,int,int) bound')

    if ($ReportPath) {
        $report = [ordered]@{ plugin_sha256=(Get-FileHash -LiteralPath $PluginDll -Algorithm SHA256).Hash.ToLowerInvariant()
                              game_assembly_sha256=(Get-FileHash -LiteralPath $GameDll -Algorithm SHA256).Hash.ToLowerInvariant()
                              evidence=$evidence; runtime_tested=$false }
        [IO.File]::WriteAllText([IO.Path]::GetFullPath($ReportPath), ($report | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    }
    Write-Output "PASS: ninth-game history identity, hooks and $($evidence.Count) reflection bindings verified offline."
} finally { $assembly.Dispose(); $game.Dispose() }
