$ErrorActionPreference = "Stop"

$desktopRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$releaseRoot = Join-Path $desktopRoot "src-tauri\target\release"
$sourceExe = Join-Path $releaseRoot "kibukawa-web-spinoffs.exe"
$portableRoot = Join-Path $desktopRoot "portable"
$stageRoot = Join-Path $portableRoot "Kibukawa-Web-Spinoffs-CHS-portable"
$zipPath = Join-Path $portableRoot "Kibukawa-Web-Spinoffs-CHS-v0.1.0-win64-portable.zip"

if (-not (Test-Path -LiteralPath $sourceExe -PathType Leaf)) {
    throw "Portable executable not found: $sourceExe"
}

$resolvedDesktop = [System.IO.Path]::GetFullPath($desktopRoot)
$resolvedStage = [System.IO.Path]::GetFullPath($stageRoot)
if (-not $resolvedStage.StartsWith($resolvedDesktop, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to package outside the desktop workspace: $resolvedStage"
}

if (Test-Path -LiteralPath $stageRoot) {
    Remove-Item -LiteralPath $stageRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null

Copy-Item -LiteralPath $sourceExe -Destination (Join-Path $stageRoot "Kibukawa-Web-Spinoffs-CHS.exe")
Copy-Item -LiteralPath (Join-Path $desktopRoot "PORTABLE-README.txt") -Destination $stageRoot
Copy-Item -LiteralPath (Join-Path $desktopRoot "THIRD-PARTY-NOTICES.txt") -Destination $stageRoot
Copy-Item -LiteralPath (Join-Path $desktopRoot "dist") -Destination (Join-Path $stageRoot "www") -Recurse

$licenseRoot = Join-Path $stageRoot "licenses"
$ruffleLicenseRoot = Join-Path $licenseRoot "ruffle"
New-Item -ItemType Directory -Path $ruffleLicenseRoot -Force | Out-Null

$webRoot = (Resolve-Path (Join-Path $desktopRoot "..")).Path
Copy-Item -LiteralPath (Join-Path $webRoot "saina-onsen\build\ruffle\LICENSE_APACHE") -Destination $ruffleLicenseRoot
Copy-Item -LiteralPath (Join-Path $webRoot "saina-onsen\build\ruffle\LICENSE_MIT") -Destination $ruffleLicenseRoot
Copy-Item -LiteralPath (Join-Path $webRoot "saina-onsen\build\OFL-NotoSansSC.txt") -Destination $licenseRoot

$wheelPath = Join-Path $webRoot "vendor\pyxel-2.9.6\pyxel-2.9.6-cp311-abi3-emscripten_5_0_3_wasm32.whl"
Add-Type -AssemblyName System.IO.Compression.FileSystem
$wheel = [System.IO.Compression.ZipFile]::OpenRead($wheelPath)
try {
    $entry = $wheel.GetEntry("pyxel/LICENSE")
    if ($null -eq $entry) { throw "Pyxel license not found in wheel" }
    [System.IO.Compression.ZipFileExtensions]::ExtractToFile(
        $entry,
        (Join-Path $licenseRoot "PYXEL-LICENSE.txt"),
        $true
    )
} finally {
    $wheel.Dispose()
}

if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -LiteralPath $stageRoot -DestinationPath $zipPath -CompressionLevel Optimal

$zip = Get-Item -LiteralPath $zipPath
Write-Host "Portable ZIP: $($zip.FullName) ($([Math]::Round($zip.Length / 1MB, 1)) MB)"
