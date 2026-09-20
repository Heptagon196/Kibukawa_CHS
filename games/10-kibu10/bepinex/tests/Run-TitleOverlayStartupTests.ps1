$ErrorActionPreference='Stop'
$project=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Add-Type -Path @((Join-Path $PSScriptRoot 'TitleOverlayStartupTests.cs'),(Join-Path $project 'bepinex/images/TitleMenuOverlay.cs'))
$folder=Join-Path $project 'out/image-package/package/BepInEx/plugins/KibukawaImageReplacements'
[TitleOverlayStartupTests]::Run($folder)
Write-Output 'PASS: no pre-screen factory call; lazy Chinese title menu creation, repeated painting and disposal'
