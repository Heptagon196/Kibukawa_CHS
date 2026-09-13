param([Parameter(Mandatory)][string]$PluginDll, [Parameter(Mandatory)][string]$GameDll, [string]$ReportPath)
$ErrorActionPreference = 'Stop'
Add-Type -Path (Join-Path $PSScriptRoot '../../../bin/ilspy/tools/net6.0/any/Mono.Cecil.dll')
$assembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly([IO.Path]::GetFullPath($PluginDll))
$game = [Mono.Cecil.AssemblyDefinition]::ReadAssembly([IO.Path]::GetFullPath($GameDll))
$evidence = [Collections.Generic.List[string]]::new()
function Fail([string]$message) { throw $message }
try {
    if ($assembly.Name.Name -ne 'Kibu9ZhCN') { Fail 'Wrong output assembly' }
    $plugin = $assembly.MainModule.GetType('Kibu9ZhCN.Plugin')
    if (!$plugin) { Fail 'Ninth-game entry point missing' }
    if ($plugin.BaseType.FullName -ne 'Kibukawa.Engine.Gmode20050117.CanvasRuntime') { Fail "Wrong runtime base: $($plugin.BaseType.FullName)" }
    $attribute = @($plugin.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInPlugin' })
    $process = @($plugin.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInProcess' })
    if ($attribute.Count -ne 1 -or $attribute[0].ConstructorArguments[0].Value -ne 'local.kibu9.zhcn') { Fail 'Wrong plugin ID' }
    if ($process.Count -ne 1 -or $process[0].ConstructorArguments[0].Value -ne 'kibu9.exe') { Fail 'Wrong process filter' }
    if ($assembly.MainModule.AssemblyReferences.Name -contains 'Kibu1ZhCN') { Fail 'Must not reference the first-game plugin assembly' }
    $evidence.Add('plugin identity, process filter and runtime base verified')

    # Harmony hook signatures must match what Harmony resolves by name at runtime.
    $runtime = $assembly.MainModule.GetType('Kibukawa.Engine.Gmode20050117.CanvasRuntime')
    if (!$runtime) { Fail 'Shared runtime base missing from the plugin' }
    $hooks = @{
        'BeforeStock'     = @('System.Object', 'System.String&')
        'BeforeDraw'      = @('System.Object', 'System.Char[]', 'System.Int32', 'System.Int32')
        'AfterLoad'       = @('System.Object')
        'AfterLine'       = @('System.Object')
        'BeforeBunsyou'   = @('System.Object')
        'BeforeName'      = @('System.Object')
        'BeforeChoice'    = @('System.Object')
        'AfterStringRead' = @('System.Object', 'System.String&')
    }
    foreach ($name in $hooks.Keys) {
        $method = @($runtime.Methods | Where-Object { $_.Name -eq $name })
        if ($method.Count -ne 1) { Fail "Hook $name missing or ambiguous" }
        if (!$method[0].IsStatic) { Fail "Hook $name must be static" }
        $actual = @($method[0].Parameters | ForEach-Object { $_.ParameterType.FullName })
        $expected = $hooks[$name]
        if ($actual.Count -ne $expected.Count) { Fail "Hook $name arity mismatch: $($actual -join ',')" }
        for ($i = 0; $i -lt $expected.Count; $i++) {
            if ($actual[$i] -ne $expected[$i]) { Fail "Hook $name parameter $i is $($actual[$i]), expected $($expected[$i])" }
        }
        $evidence.Add("hook $name($($expected -join ',')) resolved")
    }

    # Reflection contract against the shipped game assembly.
    $canvas = $game.MainModule.GetType('CanvasEx')
    if (!$canvas) { Fail 'CanvasEx missing from the game assembly' }
    $instance = @('Bun_moji','Bun_iro','Bun_speed','Bun_alpha','Bun_jikan','Bun_nagasa','BunsyouNagasaMax','DanNoKazu',
                  'NowStockMojiDan','NowStockMojiKeta','NowPrintingDan','NowPrintingKeta','SyoriMojiCount')
    $statics = @('FWidth','FHeight','FAscent')
    foreach ($name in $instance) {
        $field = @($canvas.Fields | Where-Object { $_.Name -eq $name -and !$_.IsStatic })
        if ($field.Count -ne 1) { Fail "CanvasEx instance field $name missing" }
        $evidence.Add("CanvasEx.$name : $($field[0].FieldType.Name)")
    }
    foreach ($name in $statics) {
        $field = @($canvas.Fields | Where-Object { $_.Name -eq $name -and $_.IsStatic })
        if ($field.Count -ne 1) { Fail "CanvasEx static field $name missing" }
        $evidence.Add("CanvasEx.$name (static) : $($field[0].FieldType.Name)")
    }
    foreach ($spec in @(@('BunsyouStock', 1), @('LoadScenario', 1), @('LoadScenarioEx', 1))) {
        $method = @($canvas.Methods | Where-Object { $_.Name -eq $spec[0] -and $_.Parameters.Count -eq $spec[1] -and $_.Parameters[0].ParameterType.FullName -eq 'System.String' })
        if ($method.Count -ne 1) { Fail "CanvasEx::$($spec[0])(System.String) not found exactly once" }
        $evidence.Add("CanvasEx::$($spec[0])(System.String) bound")
    }
    # The text entry points the runtime patches: nameplate, menu label and the shared
    # string reader whose result both of them store.
    foreach ($name in @('NAMAE_SETTEI','SENTAKUSI','BUNSYOU')) {
        $method = @($canvas.Methods | Where-Object { $_.Name -eq $name -and $_.Parameters.Count -eq 0 })
        if ($method.Count -ne 1) { Fail "CanvasEx::$name() not found exactly once" }
        $evidence.Add("CanvasEx::$name() bound")
    }
    $reader = @($canvas.Methods | Where-Object { $_.Name -eq 'StringRead' -and $_.Parameters.Count -eq 0 -and $_.ReturnType.FullName -eq 'System.String' })
    if ($reader.Count -ne 1) { Fail 'CanvasEx::StringRead() not found exactly once' }
    $evidence.Add('CanvasEx::StringRead() bound')
    # Ruby creation returns the advanced cell counter; suppressing it zeros rubi_info_kazu.
    $rubi = @($canvas.Methods | Where-Object { $_.Name -eq 'CreateRubiTexture' -and $_.Parameters.Count -eq 2 -and $_.ReturnType.FullName -eq 'System.Int32' })
    if ($rubi.Count -ne 1) { Fail 'CanvasEx::CreateRubiTexture(String,Int32) returning int not found exactly once' }
    if ($rubi[0].Parameters[0].ParameterType.FullName -ne 'System.String' -or $rubi[0].Parameters[1].ParameterType.FullName -ne 'System.Int32') { Fail 'CreateRubiTexture parameter types changed' }
    $evidence.Add('CanvasEx::CreateRubiTexture(String,Int32) -> System.Int32 bound')
    if (@($canvas.Fields | Where-Object { $_.Name -eq 'RubiCreateCounter' -and !$_.IsStatic }).Count -ne 1) { Fail 'CanvasEx::RubiCreateCounter missing' }
    $evidence.Add('CanvasEx.RubiCreateCounter bound')
    $graphics = $game.MainModule.GetType('Socotra.UI.StGraphics')
    if (!$graphics) { Fail 'Socotra.UI.StGraphics missing' }
    # The runtime patches exactly these line terminators; a rename would silently
    # stop line-level substitution, so bind them explicitly.
    foreach ($name in @('BUNSYOU_SLASH','BUNSYOU_SEMI_COLON','BUNSYOU_PERIOD','BUNSYOU_ASTARISK')) {
        $terminator = @($canvas.Methods | Where-Object { $_.Name -eq $name -and $_.Parameters.Count -eq 0 })
        if ($terminator.Count -ne 1) { Fail "CanvasEx::$name() not found exactly once" }
        $evidence.Add("CanvasEx::$name() bound")
    }
    # The one in-line command that recolours the characters after it. The runtime counts
    # it to stock each colour run of a translated line where its colour takes effect, so
    # a rename would silently drop the emphasis on every clue word the script highlights.
    $colour = @($canvas.Methods | Where-Object { $_.Name -eq 'BUNSYOU_IRO' -and $_.Parameters.Count -eq 0 })
    if ($colour.Count -ne 1) { Fail 'CanvasEx::BUNSYOU_IRO() not found exactly once' }
    $evidence.Add('CanvasEx::BUNSYOU_IRO() bound')
    $draw = @($graphics.Methods | Where-Object { $_.Name -eq 'DrawCharImpl' -and $_.Parameters.Count -eq 3 })
    if ($draw.Count -ne 1) { Fail 'StGraphics::DrawCharImpl(char[],int,int) not found exactly once' }
    if ($draw[0].Parameters[0].ParameterType.FullName -ne 'System.Char[]') { Fail 'DrawCharImpl first parameter is not char[]' }
    $evidence.Add('StGraphics::DrawCharImpl(char[],int,int) bound')
    $origin = @($graphics.Fields | Where-Object { $_.Name -eq 'drawOrigin' })
    if ($origin.Count -ne 1) { Fail 'StGraphics::drawOrigin missing' }
    $evidence.Add("StGraphics.drawOrigin : $($origin[0].FieldType.FullName)")

    # Unity UI text is patched through the game's own localization table.
    $localize = $game.MainModule.GetType('Steezy.Localize.Localization')
    if (!$localize) { Fail 'Steezy.Localize.Localization missing' }
    $get = @($localize.Methods | Where-Object { $_.Name -eq 'Get' -and $_.Parameters.Count -eq 1 -and $_.Parameters[0].ParameterType.FullName -eq 'System.String' -and $_.ReturnType.FullName -eq 'System.String' })
    if ($get.Count -ne 1) { Fail 'Localization::Get(System.String) not found exactly once' }
    $evidence.Add('Steezy.Localize.Localization::Get(System.String) bound')
    # The soft-key array the runtime edits in place.
    $command = @($canvas.Fields | Where-Object { $_.Name -eq 'command' -and $_.IsStatic })
    if ($command.Count -ne 1 -or $command[0].FieldType.FullName -ne 'System.String[]') { Fail 'CanvasEx::command static string[] missing' }
    $evidence.Add('CanvasEx.command (static string[]) bound')

    # The choice-memory transpiler rewrites exactly these guards; if the shipped IL
    # changes shape the plugin would throw at load, so verify the shape here instead.
    foreach ($name in @('komando_modori','NowCommand','NowChobunCommand','CommandCursorPos','CommandTop','SentakuStock','Script','Pos')) {
        if (@($canvas.Fields | Where-Object { $_.Name -eq $name }).Count -lt 1) { Fail "CanvasEx::$name missing for choice memory" }
    }
    $evidence.Add('choice memory fields bound')
    function CountChoiceGuards([string]$methodName, [bool]$recording, [int]$window) {
        $method = @($canvas.Methods | Where-Object { $_.Name -eq $methodName -and $_.Parameters.Count -eq 0 })[0]
        if (!$method -or !$method.HasBody) { Fail "$methodName has no body" }
        $il = @($method.Body.Instructions)
        $guards = 0
        $keys = 0
        for ($i = 0; $i + 3 -lt $il.Count; $i++) {
            if ($il[$i].OpCode.Code -ne 'Ldfld') { continue }
            if ($il[$i].Operand -eq $null -or $il[$i].Operand.Name -ne 'komando_modori') { continue }
            if ($il[$i + 1].OpCode.Code -ne 'Ldc_I4_M1') { continue }
            if ($il[$i + 2].OpCode.Code -ne 'Bne_Un' -and $il[$i + 2].OpCode.Code -ne 'Bne_Un_S') { continue }
            if ($il[$i + 3].OpCode.Code -ne 'Ldc_I4_0') { continue }
            $table = $false
            for ($j = $i + 4; $j -lt [Math]::Min($i + $window, $il.Count); $j++) {
                if ($il[$j].OpCode.Code -eq 'Ldfld' -and $il[$j].Operand -ne $null -and $il[$j].Operand.Name -eq 'Sentaku_kioku_id') { $table = $true }
            }
            if (!$table) { Fail "$methodName guard at $i does not precede the native table" }
            $guards++
            for ($j = $i + 4; $j -lt [Math]::Min($i + $window, $il.Count); $j++) {
                if ($il[$j].OpCode.Code -eq 'Ldfld' -and $il[$j].Operand -ne $null -and $il[$j].Operand.Name -eq 'Pos') { $keys++ }
            }
        }
        return @($guards, $keys)
    }
    $advance = CountChoiceGuards 'Game_adv' $false 41
    if ($advance[0] -ne 2 -or $advance[1] -ne 2) { Fail "Game_adv choice guards changed: $($advance -join '/')" }
    $evidence.Add("Game_adv choice memory guards: $($advance[0]) guards, $($advance[1]) identity reads")
    $command = CountChoiceGuards 'Game_command' $true 70
    if ($command[0] -ne 1 -or $command[1] -ne 2) { Fail "Game_command choice guards changed: $($command -join '/')" }
    $evidence.Add("Game_command choice memory guards: $($command[0]) guards, $($command[1]) identity reads")

    if ($ReportPath) {
        $report = [ordered]@{ plugin_sha256=(Get-FileHash -LiteralPath $PluginDll -Algorithm SHA256).Hash.ToLowerInvariant()
                              game_assembly_sha256=(Get-FileHash -LiteralPath $GameDll -Algorithm SHA256).Hash.ToLowerInvariant()
                              evidence=$evidence; runtime_tested=$false }
        [IO.File]::WriteAllText([IO.Path]::GetFullPath($ReportPath), ($report | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
    }
    Write-Output "PASS: ninth-game runtime identity, Harmony hooks and $($evidence.Count) reflection bindings verified offline."
} finally { $assembly.Dispose(); $game.Dispose() }
