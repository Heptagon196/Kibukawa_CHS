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
        'BeforeAdvDraw'   = @('System.Object', 'System.Int32', 'System.Int32', 'System.Int32&', 'System.Int32&', 'System.Boolean&')
        'RestoreAdvDraw'  = @('System.Boolean')
        'BeforeNameplateDraw' = @('System.Boolean&')
        'BeforeNameplatePosition' = @('System.Object', 'System.Int32&', 'System.Int32&', 'System.Boolean&')
        'AfterClearText' = @('System.Object')
        'RestoreNameplateDraw' = @('System.Boolean')
        'BeforeChoiceCenter' = @('System.Object', 'System.Object', 'System.Int32', 'System.Int32', 'System.Int32')
        'BeforeChoiceLeft' = @('System.Object', 'System.Object', 'System.Int32', 'System.Int32', 'System.Int32', 'System.Int32')
        'AfterLoad'       = @('System.Object')
        'AfterLine'       = @('System.Object')
        'BeforeBunsyou'   = @('System.Object')
        'BeforeF7'        = @('System.Object')
        'BeforeColon'     = @('System.Object')
        'BeforeName'      = @('System.Object')
        'BeforeChoice'    = @('System.Object')
        'AfterStringRead' = @('System.Object', 'System.String&')
        'BeforeCanvasUi'  = @('System.String&')
        'BeforeSaveNames' = @('System.Object', 'Kibukawa.Engine.Gmode20050117.CanvasRuntime/NameSaveState&')
        'AfterSaveNames'  = @('System.Object', 'Kibukawa.Engine.Gmode20050117.CanvasRuntime/NameSaveState')
        'AfterSaveNamesError' = @('System.Object', 'Kibukawa.Engine.Gmode20050117.CanvasRuntime/NameSaveState', 'System.Exception')
        'AfterLoadNames'  = @('System.Object')
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
    $canvasUiHook = @($runtime.Methods | Where-Object { $_.Name -eq 'BeforeCanvasUi' })[0]
    $callsTryUi = @($canvasUiHook.Body.Instructions | Where-Object {
        $_.Operand -ne $null -and $_.Operand.Name -eq 'TryUi'
    }).Count -eq 1
    if (!$callsTryUi) { Fail 'BeforeCanvasUi no longer calls RuntimePack.TryUi exactly once' }
    $installHooks = @($runtime.Methods | Where-Object { $_.Name -eq 'InstallHooks' -and $_.Parameters.Count -eq 0 })
    if ($installHooks.Count -ne 1) { Fail 'CanvasRuntime::InstallHooks() missing or ambiguous' }
    $installStrings = @($installHooks[0].Body.Instructions | Where-Object { $_.OpCode.Code -eq 'Ldstr' } | ForEach-Object { [string]$_.Operand })
    foreach ($name in @('Ds_sub','Ds_sub2')) {
        if (@($installStrings | Where-Object { $_ -eq $name }).Count -ne 1) {
            Fail "CanvasRuntime::InstallHooks does not patch $name exactly once"
        }
    }
    if (@($installStrings | Where-Object { $_ -eq 'BeforeCanvasUi' }).Count -ne 2) {
        Fail 'CanvasRuntime::InstallHooks does not attach BeforeCanvasUi to both display helpers'
    }
    foreach ($name in @('BUNSYOU_COLON','BeforeColon')) {
        if (@($installStrings | Where-Object { $_ -eq $name }).Count -ne 1) {
            Fail "CanvasRuntime::InstallHooks does not bind $name exactly once"
        }
    }
    $evidence.Add('BeforeCanvasUi calls RuntimePack.TryUi and is attached to Ds_sub plus Ds_sub2')
    $evidence.Add('BUNSYOU_COLON is guarded by BeforeColon exactly once')

    # Reflection contract against the shipped game assembly.
    $canvas = $game.MainModule.GetType('CanvasEx')
    if (!$canvas) { Fail 'CanvasEx missing from the game assembly' }
    $instance = @('Bun_moji','Bun_iro','Bun_speed','Bun_alpha','Bun_jikan','Bun_nagasa','BunsyouNagasaMax','DanNoKazu',
                  'NowStockMojiDan','NowStockMojiKeta','NowPrintingDan','NowPrintingKeta','SyoriMojiCount','MojiHani_tate','MojiHani_yoko',
                  'MainTask','SubTask','NowFadeChu','SysCursor_enable','OsippanasiKinsi',
                  'Sentaku_nafuda','Namae_nafuda','model')
    $statics = @('FWidth','FHeight','FAscent','FDocomo','Width')
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
    foreach ($name in @('NAMAE_SETTEI','SENTAKUSI','BUNSYOU','BUNSYOU_COLON','ClearBunBuffer')) {
        $method = @($canvas.Methods | Where-Object { $_.Name -eq $name -and $_.Parameters.Count -eq 0 })
        if ($method.Count -ne 1) { Fail "CanvasEx::$name() not found exactly once" }
        $evidence.Add("CanvasEx::$name() bound")
    }
    $reader = @($canvas.Methods | Where-Object { $_.Name -eq 'StringRead' -and $_.Parameters.Count -eq 0 -and $_.ReturnType.FullName -eq 'System.String' })
    if ($reader.Count -ne 1) { Fail 'CanvasEx::StringRead() not found exactly once' }
    $evidence.Add('CanvasEx::StringRead() bound')
    # Native save data stores the persistent name array through its CP932 string
    # codec. The runtime swaps only pack-proven nameplate values around these two
    # zero-argument entry points.
    $saveData = @($canvas.Methods | Where-Object { $_.Name -eq 'SaveData' -and $_.Parameters.Count -eq 0 -and $_.ReturnType.FullName -eq 'System.Boolean' })
    $loadData = @($canvas.Methods | Where-Object { $_.Name -eq 'LoadData' -and $_.Parameters.Count -eq 0 -and $_.ReturnType.FullName -eq 'System.Void' })
    if ($saveData.Count -ne 1) { Fail 'CanvasEx::SaveData() -> Boolean not found exactly once' }
    if ($loadData.Count -ne 1) { Fail 'CanvasEx::LoadData() -> Void not found exactly once' }
    foreach ($spec in @(@($saveData[0], 'StringToBytesAndAdd'), @($loadData[0], 'ReadString'))) {
        $method = $spec[0]
        $codec = $spec[1]
        $hasNames = @($method.Body.Instructions | Where-Object { $_.Operand -ne $null -and $_.Operand.Name -eq 'Namae_nafuda' }).Count -gt 0
        $hasCodec = @($method.Body.Instructions | Where-Object { $_.Operand -ne $null -and $_.Operand.Name -eq $codec }).Count -gt 0
        if (!$hasNames -or !$hasCodec) { Fail "CanvasEx::$($method.Name) no longer serializes Namae_nafuda through $codec" }
        $evidence.Add("CanvasEx::$($method.Name) persists Namae_nafuda through $codec")
    }
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
    # IRO starts a colour override; after ruby is closed, F7 restores the base colour.
    # Both boundaries must be patched or translated emphasis leaks into adjacent text.
    foreach ($name in @('BUNSYOU_IRO','BUNSYOU_F7')) {
        $colour = @($canvas.Methods | Where-Object { $_.Name -eq $name -and $_.Parameters.Count -eq 0 })
        if ($colour.Count -ne 1) { Fail "CanvasEx::$name() not found exactly once" }
        $evidence.Add("CanvasEx::$name() bound")
    }
    $draw = @($graphics.Methods | Where-Object { $_.Name -eq 'DrawCharImpl' -and $_.Parameters.Count -eq 3 })
    if ($draw.Count -ne 1) { Fail 'StGraphics::DrawCharImpl(char[],int,int) not found exactly once' }
    if ($draw[0].Parameters[0].ParameterType.FullName -ne 'System.Char[]') { Fail 'DrawCharImpl first parameter is not char[]' }
    $evidence.Add('StGraphics::DrawCharImpl(char[],int,int) bound')
    $advDraw = @($canvas.Methods | Where-Object { $_.Name -eq 'DrawAdvString' -and $_.Parameters.Count -eq 5 })
    if ($advDraw.Count -ne 1 -or $advDraw[0].Parameters[0].ParameterType.FullName -ne 'Socotra.UI.StGraphics') { Fail 'CanvasEx::DrawAdvString(StGraphics,int,int,int,int) not found exactly once' }
    $evidence.Add('CanvasEx::DrawAdvString(StGraphics,int,int,int,int) bound')
    $nameDraw = @($canvas.Methods | Where-Object { $_.Name -eq 'DrawAdvNafuda' })
    if ($nameDraw.Count -ne 1 -or $nameDraw[0].Parameters.Count -ne 3 -or $nameDraw[0].Parameters[0].ParameterType.FullName -ne 'Socotra.UI.StGraphics') { Fail 'CanvasEx::DrawAdvNafuda(StGraphics,int,int) not found exactly once' }
    $evidence.Add('CanvasEx::DrawAdvNafuda(StGraphics,int,int) bound')
    $choiceCenter = @($canvas.Methods | Where-Object { $_.Name -eq 'DrawAdvCommandCenter' -and $_.Parameters.Count -eq 4 })
    if ($choiceCenter.Count -ne 1 -or $choiceCenter[0].Parameters[0].ParameterType.FullName -ne 'Socotra.UI.StGraphics') { Fail 'CanvasEx::DrawAdvCommandCenter(StGraphics,int,int,int) not found exactly once' }
    $evidence.Add('CanvasEx::DrawAdvCommandCenter(StGraphics,int,int,int) bound')
    $choiceLeft = @($canvas.Methods | Where-Object { $_.Name -eq 'DrawAdvCommand' -and $_.Parameters.Count -eq 5 })
    if ($choiceLeft.Count -ne 1 -or $choiceLeft[0].Parameters[0].ParameterType.FullName -ne 'Socotra.UI.StGraphics') { Fail 'CanvasEx::DrawAdvCommand(StGraphics,int,int,int,int) not found exactly once' }
    $evidence.Add('CanvasEx::DrawAdvCommand(StGraphics,int,int,int,int) bound')
    $setColor = @($canvas.Methods | Where-Object { $_.Name -eq 'SetColor' -and $_.Parameters.Count -eq 2 -and $_.Parameters[0].ParameterType.FullName -eq 'Socotra.UI.StGraphics' -and $_.Parameters[1].ParameterType.FullName -eq 'System.Int32' })
    if ($setColor.Count -ne 1) { Fail 'CanvasEx::SetColor(StGraphics,int) not found exactly once' }
    $evidence.Add('CanvasEx::SetColor(StGraphics,int) bound')
    $drawString = @($graphics.Methods | Where-Object { $_.Name -eq 'DrawString' -and $_.Parameters.Count -eq 3 -and $_.Parameters[0].ParameterType.FullName -eq 'System.String' })
    if ($drawString.Count -ne 1) { Fail 'StGraphics::DrawString(String,int,int) not found exactly once' }
    $evidence.Add('StGraphics::DrawString(String,int,int) bound')
    # Loading and legacy-service status lines enter these CanvasEx helpers as one
    # string. Both helpers measure that argument before slicing it into one-character
    # DrawString calls, so the runtime prefix must bind this exact entry point.
    $displayTypes = @('Socotra.UI.StGraphics','System.String','System.Int32','System.Int32')
    foreach ($name in @('Ds_sub','Ds_sub2')) {
        $methods = @($canvas.Methods | Where-Object { $_.Name -eq $name })
        if ($methods.Count -ne 1) { Fail "CanvasEx::$name missing or ambiguous" }
        $method = $methods[0]
        $actual = @($method.Parameters | ForEach-Object { $_.ParameterType.FullName })
        if ($method.ReturnType.FullName -ne 'System.Void' -or $actual.Count -ne $displayTypes.Count) {
            Fail "CanvasEx::$name has the wrong return type or arity"
        }
        for ($i = 0; $i -lt $displayTypes.Count; $i++) {
            if ($actual[$i] -ne $displayTypes[$i]) {
                Fail "CanvasEx::$name parameter $i is $($actual[$i]), expected $($displayTypes[$i])"
            }
        }
        $il = @($method.Body.Instructions)
        $length = @($il | Where-Object { $_.Operand -ne $null -and $_.Operand.FullName -eq 'System.Int32 System.String::get_Length()' })
        $substring = @($il | Where-Object { $_.Operand -ne $null -and $_.Operand.FullName -eq 'System.String Socotra.StString::Substring(System.String,System.Int32,System.Int32)' })
        if ($length.Count -lt 1 -or $substring.Count -lt 1) { Fail "CanvasEx::$name no longer measures and splits its input text" }
        $evidence.Add("CanvasEx::$name(StGraphics,String,Int32,Int32) measures then splits the complete UI line")
    }
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
