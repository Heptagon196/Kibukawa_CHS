$ErrorActionPreference='Stop'
$gamePath=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Add-Type -Path @((Join-Path $gamePath '../../engine/adapters/gmode-v2/src/MenuMemory.cs'),(Join-Path $PSScriptRoot 'DirectChoiceMemoryTests.cs'),(Join-Path $gamePath '../../engine/adapters/gmode-20050817-direct/src/DirectChoiceMemory.cs'))
$assembly=Get-Content -Raw (Join-Path $gamePath 'research/kibu10-assembly.json') | ConvertFrom-Json
[ChoiceMemoryTests]::Run($assembly.methods.'System.Boolean CanvasEx::Game_adv()'.il,$assembly.methods.'System.Boolean CanvasEx::Game_command()'.il)
