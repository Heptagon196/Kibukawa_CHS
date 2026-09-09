$ErrorActionPreference = 'Stop'
$workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$seriesRoot = [IO.Path]::GetFullPath((Join-Path $workspace '../..'))
$entry = (Get-Content -LiteralPath (Join-Path $seriesRoot 'series.json') -Raw | ConvertFrom-Json).games.kibu3
if ([IO.Path]::IsPathRooted($entry.installation) -or [IO.Path]::IsPathRooted($entry.project)) { throw 'Expected relative series paths' }
if ([IO.Path]::GetFullPath((Join-Path $seriesRoot $entry.project)) -ne $workspace) { throw 'Third-game project path mismatch' }
# Read-only compatibility validation must run before enabling the project.
$paths = @{ Series=$seriesRoot; Game=[IO.Path]::GetFullPath((Join-Path $seriesRoot $entry.installation)) }
$game = $paths.Game
Add-Type -Path (Join-Path $paths.Series 'bin/ilspy/tools/net6.0/any/Mono.Cecil.dll')
$expectedAssemblyHash = '6ec1d39ea7e55699c4d6a435b1124593ee8c379301c8ec1e6ef7b3a939636114'
if ((Get-FileHash -LiteralPath (Join-Path $game 'kibu3_Data/Managed/Assembly-CSharp.dll') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedAssemblyHash) { throw 'Third-game original assembly fingerprint mismatch' }
$assembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $game 'kibu3_Data/Managed/Assembly-CSharp.dll'))
$ui = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $game 'kibu3_Data/Managed/UnityEngine.UI.dll'))
$plugin = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $workspace 'bepinex/build/plugin/Kibu3ZhCN.dll'))
$pack = Get-Content -LiteralPath (Join-Path $workspace 'bepinex/build/plugin/translations.json') -Raw | ConvertFrom-Json
function Require-Type($module, $name) {
    $result = $module.GetType($name)
    if (!$result) { throw "Missing type: $name" }
    return $result
}
function Require-Method($type, $name, $signature) {
    $methods = @($type.Methods | Where-Object { $_.Name -eq $name -and (($_.Parameters.ParameterType.FullName -join ',') -eq $signature) })
    if ($methods.Count -ne 1 -or !$methods[0].HasBody) { throw "Missing/ambiguous method: $($type.FullName)::$name($signature)" }
}
$canvas = Require-Type $assembly.MainModule 'CanvasEx'
Require-Method $canvas 'Read' ''
Require-Method $canvas 'Script' ''
if (($canvas.Methods | Where-Object Name -eq 'Script').ReturnType.FullName -ne 'System.Collections.IEnumerator') { throw 'Script coroutine signature mismatch' }
Require-Method $canvas 'ExeText' 'System.String,System.Int32'
Require-Method $canvas 'Jump' 'System.Boolean,System.Int32'
$menuSelect = $canvas.Fields | Where-Object Name -eq 'Select'
if (!$menuSelect -or $menuSelect.FieldType.FullName -ne 'System.SByte[]') { throw 'Menu cursor field mismatch' }
$menuIterator = $canvas.NestedTypes | Where-Object Name -like '*Script*'
$menuMoveNext = $menuIterator.Methods | Where-Object Name -eq 'MoveNext'
$menuInitializers = 0
$menuIl = $menuMoveNext.Body.Instructions
for ($i=3; $i -lt $menuIl.Count-1; $i++) {
    if ($menuIl[$i].OpCode.Code.ToString() -eq 'Ldc_I4_0' -and $menuIl[$i-1].OpCode.Code.ToString() -eq 'Ldc_I4_1' -and $menuIl[$i-2].Operand.Name -eq 'Select' -and $menuIl[$i+1].OpCode.Code.ToString() -eq 'Stelem_I1') {
        if ($menuIl[$i-3].OpCode.Code.ToString() -notmatch '^Ldloc') { throw 'Menu owner load mismatch' }
        $menuInitializers++
    }
}
if ($menuInitializers -ne 2) { throw 'Expected exactly two original menu cursor initializers' }
$fields = @{ScCur='System.Int32'; Scenario='System.SByte'; ScSelect='System.SByte'; ScStr='System.String[]'; Cmd='System.Int32'; ScInt='System.Int32[]'; Truth='System.Boolean'; NameID='System.SByte'; TextLine='System.SByte'; Text='System.Char[][]'; TextC='System.SByte[][]'; TextLen='System.SByte[]'; TextPos='System.SByte[]'; TextColor='System.SByte[]'; PaintValue='System.Int32'; Name='System.String[]'; Flag='System.SByte[]'}
foreach ($name in $fields.Keys) {
    $field = $canvas.Fields | Where-Object Name -eq $name
    if (!$field -or $field.FieldType.FullName -ne $fields[$name]) { throw "Field mismatch: $name" }
}
$localize = Require-Type $assembly.MainModule 'Steezy.Localize.Localization'
Require-Method $localize 'Get' 'System.String'
$font = Require-Type $assembly.MainModule 'Socotra.UI.StFont'
Require-Method $font 'GenerateTextMesh' 'System.Char[]'
if (!( $font.Fields | Where-Object { $_.Name -eq 'font' -and $_.FieldType.FullName -eq 'UnityEngine.Font' })) { throw 'Missing StFont.font' }
$graphics = Require-Type $assembly.MainModule 'Socotra.UI.StGraphics'
Require-Method $graphics 'DrawCharImpl' 'System.Char[],System.Int32,System.Int32'
Require-Method $graphics 'RenderStart' ''
Require-Method $graphics 'RenderEnd' ''
foreach ($pair in @(@('renderTexture','UnityEngine.RenderTexture'),@('currentColor','UnityEngine.Color'))) {
    if (!( $graphics.Fields | Where-Object { $_.Name -eq $pair[0] -and $_.FieldType.FullName -eq $pair[1] })) { throw "Missing renderer member: $($pair[0])" }
}
if (!( $graphics.Fields | Where-Object { $_.Name -eq 'currentFont' -and $_.FieldType.FullName -eq 'Socotra.UI.StFont' })) { throw 'Missing StGraphics.currentFont' }
$textType = Require-Type $ui.MainModule 'UnityEngine.UI.Text'
$help = Require-Type $assembly.MainModule 'HowToPlayDialog'
Require-Method $help 'ChangePage' 'System.Int32'
if (!($help.Fields | Where-Object { $_.Name -eq 'guideImage' -and $_.FieldType.FullName -eq 'UnityEngine.UI.Image' })) { throw 'Missing HowToPlayDialog.guideImage' }
Require-Method $textType 'set_text' 'System.String'
Require-Method $textType 'set_font' 'UnityEngine.Font'
Require-Method $textType 'OnEnable' ''
foreach ($entry in $pack.literals) {
    $method = $assembly.MainModule.LookupToken([int]$entry.token)
    if (!$method.HasBody -or $method.FullName -ne $entry.method) { throw "Literal method mismatch: $($entry.index)" }
    $instruction = $method.Body.Instructions[[int]$entry.instruction]
    if ($instruction.OpCode.Code.ToString() -ne 'Ldstr' -or $instruction.Operand -cne $entry.source) { throw "Literal mismatch: $($entry.index)" }
}
$pluginType = Require-Type $plugin.MainModule 'Kibu1ZhCN.Plugin'
if (!( $pluginType.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInPlugin' })) { throw 'Missing BepInPlugin metadata' }
$process = $pluginType.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInProcess' }
if ($process.ConstructorArguments[0].Value -ne 'kibu3.exe') { throw 'Process filter mismatch' }
$metadata = $pluginType.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInPlugin' }
if ($metadata.ConstructorArguments[0].Value -ne 'local.kibu3.zhcn') { throw 'Plugin ID mismatch' }
if ($plugin.Name.Name -ne 'Kibu3ZhCN') { throw 'Plugin assembly mismatch' }
if ($metadata.ConstructorArguments[2].Value -ne '0.2.4') { throw 'Plugin version mismatch' }
$report = @{ hook_signatures_verified=$true; literal_ordinals_verified=$pack.literals.Count; plugin_metadata_verified=$true; game_runtime_tested=$false }
$report | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $workspace 'bepinex/build/hook_report.json') -Encoding utf8
Write-Output "PASS: runtime hook signatures and $($pack.literals.Count) original IL literal positions."
$assembly.Dispose(); $ui.Dispose(); $plugin.Dispose()
