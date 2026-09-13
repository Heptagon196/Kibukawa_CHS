param([string]$RendererPath=(Join-Path $PSScriptRoot '../../../../engine/adapters/gmode-v2/src/LegacyFontRenderer.cs'))
$ErrorActionPreference='Stop'
# Compile the shipping implementation with recording Unity doubles in a fresh process.
Add-Type -Path @((Join-Path $PSScriptRoot 'FontGeometryTests.cs'),$RendererPath,(Join-Path $PSScriptRoot '../../../../engine/adapters/gmode-20050817/src/RuntimeLayout.cs'))
[FontGeometryTests]::Run()
