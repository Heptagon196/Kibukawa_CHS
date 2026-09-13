$ErrorActionPreference='Stop'
$seriesPath=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
Add-Type -Path @((Join-Path $seriesPath 'engine/image-replacements/TextureReplacement.cs'),(Join-Path $seriesPath 'engine/image-replacements/TextureReplacementTests.cs'))
[TextureReplacementTests]::Main(@())
