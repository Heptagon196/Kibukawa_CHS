$ErrorActionPreference='Stop'
$gamePath=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$seriesPath=(Resolve-Path (Join-Path $gamePath '../..')).Path
Add-Type -Path (Join-Path $gamePath 'bepinex/images/TitleMenuLayout.cs')
function Check($condition,$message) { if(!$condition) { throw $message } }
Check ([Kibu8ZhCN.Images.TitleMenuLayout]::NormalChannel(255,0,0) -eq 0) 'Red highlight must disappear in normal state'
Check ([Kibu8ZhCN.Images.TitleMenuLayout]::NormalChannel(255,255,255) -eq 170) 'Normal lettering must retain visible gray'
Check ([Kibu8ZhCN.Images.TitleMenuLayout]::NormalChannel(200,120,90) -eq 60) 'Antialias conversion must exclude colored glow'
foreach($selection in 0,1,2) {
    Check ([Kibu8ZhCN.Images.TitleMenuLayout]::CanDraw(3,$selection)) 'Each title choice must render'
    Check (![Kibu8ZhCN.Images.TitleMenuLayout]::CanDraw(1,$selection)) 'Loading title state must remain untouched'
    Check (![Kibu8ZhCN.Images.TitleMenuLayout]::CanDraw(11,$selection)) 'Options screen must remain untouched'
}
Check (![Kibu8ZhCN.Images.TitleMenuLayout]::CanDraw(3,-1)) 'Invalid selection must remain untouched'
Check (![Kibu8ZhCN.Images.TitleMenuLayout]::CanDraw(3,3)) 'Invalid selection must remain untouched'
$assembly=Get-Content -Raw -LiteralPath (Join-Path $gamePath 'research/kibu8-assembly.json') | ConvertFrom-Json
$il=$assembly.methods.'System.Void CanvasEx::PaintTitle(Socotra.UI.StGraphics)'.il
Check ($il[1] -eq 'ldfld System.Int32 CanvasEx::MainTask' -and $il[2] -eq 'ldc.i4.1 ' -and $il[4] -eq 'ret ') 'Native title loading guard changed'
Check ($il[7] -eq 'ldc.i4.s 11' -and $il[11] -eq 'call System.Void CanvasEx::PaintMenu(Socotra.UI.StGraphics)' -and $il[12] -eq 'ret ') 'Native options delegation changed'
Check ($il -contains 'ldfld System.Int32 CanvasEx::CommandCursorPos') 'Native selection field changed'
Check ($il -contains 'ldsfld Socotra.UI.Image[] CanvasEx::Image_Kyara') 'Native selected sprite array changed'
$colorIl=$assembly.methods.'System.Void Socotra.UI.StGraphics::SetColor(System.Int32)'.il
Check ($colorIl.Count -eq 5 -and $colorIl[3] -eq 'stfld UnityEngine.Color Socotra.UI.StGraphics::currentColor') 'Color restoration must cover all SetColor side effects'
$drawIl=$assembly.methods.'System.Void Socotra.UI.StGraphics::DrawImage(Socotra.UI.Image,System.Int32,System.Int32)'.il
Check (!($drawIl -contains 'ldfld UnityEngine.Color Socotra.UI.StGraphics::currentColor')) 'Sprite drawing must not be tinted by FillRect color'
foreach($index in 0,1,2) {
    $row=[Kibu8ZhCN.Images.TitleMenuLayout]::Row($index)
    Check ($il -contains "ldc.i4 $row") 'Menu row must match the verified native PaintTitle method'
    Check ($row -ge 145 -and ($row+17) -le 212) 'Highlight must stay inside cleared menu band'
}
Check ([Kibu8ZhCN.Images.TitleMenuLayout]::Left -eq 65) 'Menu must be centered on the 240-pixel title'
Add-Type -Path (Join-Path $seriesPath 'bin/ilspy/tools/net6.0/any/Mono.Cecil.dll')
$gameRoot=[IO.Path]::GetFullPath((Join-Path $seriesPath '../../GmodeArchivesPlus_kibu8'))
$native=[Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $gameRoot 'kibu8_Data/Managed/Assembly-CSharp.dll'))
try {
    $canvas=$native.MainModule.Types | Where-Object FullName -eq 'CanvasEx'
    $graphics=$native.MainModule.Types | Where-Object FullName -eq 'Socotra.UI.StGraphics'
    Check ($null -ne $canvas -and $null -ne $graphics) 'Real game rendering types must exist'
    foreach($name in 'MainTask','CommandCursorPos') {
        $field=$canvas.Fields | Where-Object Name -eq $name
        Check ($null -ne $field -and !$field.IsStatic -and $field.FieldType.FullName -eq 'System.Int32') "Invalid instance field $name"
    }
    foreach($spec in @(@('Image_Haikei','Socotra.UI.Image'),@('Image_Kyara','Socotra.UI.Image[]'))) {
        $field=$canvas.Fields | Where-Object Name -eq $spec[0]
        Check ($null -ne $field -and $field.IsStatic -and $field.FieldType.FullName -eq $spec[1]) "Invalid static image field $($spec[0])"
    }
    $field=$graphics.Fields | Where-Object Name -eq 'currentColor'
    Check ($null -ne $field -and !$field.IsStatic -and $field.FieldType.FullName -eq 'UnityEngine.Color') 'Invalid saved color field'
    foreach($signature in @('System.Void Socotra.UI.StGraphics::DrawImage(Socotra.UI.Image,System.Int32,System.Int32)', 'System.Void Socotra.UI.StGraphics::FillRect(System.Int32,System.Int32,System.Int32,System.Int32)', 'System.Void Socotra.UI.StGraphics::SetColor(System.Int32)')) {
        $method=$graphics.Methods | Where-Object FullName -eq $signature
        Check ($null -ne $method -and !$method.IsStatic) "Invalid graphics binding $signature"
    }
    $paint=$canvas.Methods | Where-Object FullName -eq 'System.Void CanvasEx::PaintTitle(Socotra.UI.StGraphics)'
    Check ($null -ne $paint -and !$paint.IsStatic) 'Invalid PaintTitle postfix binding'
    $coordinates=@()
    for($i=2;$i -lt $paint.Body.Instructions.Count;$i++) {
        $instruction=$paint.Body.Instructions[$i]
        if($instruction.Operand -and $instruction.Operand.ToString() -eq 'System.Void Socotra.UI.StGraphics::DrawImage(Socotra.UI.Image,System.Int32,System.Int32)') {
            $x=$paint.Body.Instructions[$i-2];$y=$paint.Body.Instructions[$i-1]
            if($x.OpCode.Name -eq 'ldc.i4.s' -and [int]$x.Operand -eq 62) {
                $coordinates+= [int]$y.Operand
                Check (62 -ge 0 -and (62+109) -le 240 -and [int]$y.Operand -ge 145 -and ([int]$y.Operand+17) -le 212) 'Clear band must cover every native highlight'
            }
        }
    }
    Check (($coordinates -join ',') -eq '151,171,192') 'Real native title highlight coordinates changed'
} finally { $native.Dispose() }
Write-Output 'PASS: title menu state guards, native rows, centered sprites and red-glow removal'
# Every old menu pixel is overwritten in the owned title texture, not alpha-blended.
foreach($y in 0..239) { foreach($x in 0..239) {
    $clear=[Kibu8ZhCN.Images.TitleMenuLayout]::ClearBackgroundPixel($x,$y)
    Check ($clear -eq ($y -ge 145 -and $y -lt 212)) 'Title/copyright boundary or menu clearing incomplete'
} }
Write-Output 'PASS: entire menu pixel band cleared; title and copyright pixels preserved'
