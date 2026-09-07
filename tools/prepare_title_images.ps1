$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$series = Get-Content -LiteralPath (Join-Path $root 'series.json') -Raw | ConvertFrom-Json
$sizes = @{ kibu1=@(180,76); kibu2=@(240,151); kibu3=@(220,128); kibu4=@(220,107); kibu5=@(239,105) }
foreach ($game in $sizes.Keys) {
    if (!$series.games.$game) { continue }
    $dir = Join-Path (Join-Path $root $series.games.$game.project) 'images/title-zh'
    $source = [Drawing.Image]::FromFile((Join-Path $dir 'title-master.png'))
    $size = $sizes[$game]
    $bitmap = [Drawing.Bitmap]::new($size[0], $size[1], [Drawing.Imaging.PixelFormat]::Format24bppRgb)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.PixelOffsetMode = [Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.Clear([Drawing.Color]::Black)
        $graphics.DrawImage($source, [Drawing.Rectangle]::new(0,0,$size[0],$size[1]))
        $bitmap.Save((Join-Path $dir 'title.png'), [Drawing.Imaging.ImageFormat]::Png)
        Write-Output "$game $($size[0])x$($size[1])"
    } finally { $graphics.Dispose(); $bitmap.Dispose(); $source.Dispose() }
}
