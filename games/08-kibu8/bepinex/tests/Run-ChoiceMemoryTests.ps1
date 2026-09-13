$ErrorActionPreference='Stop'
$gamePath=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Add-Type -Path @((Join-Path $gamePath '../../engine/adapters/gmode-v2/src/MenuMemory.cs'),(Join-Path $gamePath '../../engine/adapters/gmode-v2/src/PageMemory.cs'),(Join-Path $PSScriptRoot 'ChoiceMemoryTests.cs'),(Join-Path $gamePath '../../engine/adapters/gmode-20050817/src/NativeChoiceMemory.cs'),(Join-Path $gamePath '../../engine/adapters/gmode-20050817/src/NativeMenuPosition.cs'),(Join-Path $gamePath '../../engine/adapters/gmode-20050817/src/NativePagination.cs'),(Join-Path $gamePath 'bepinex/src/NativePaginationData.cs'))
$assembly=Get-Content -Raw (Join-Path $gamePath 'research/kibu8-assembly.json') | ConvertFrom-Json
[ChoiceMemoryTests]::Run($assembly.methods.'System.Boolean CanvasEx/<Game_adv>d__362::MoveNext()'.il,$assembly.methods.'System.Boolean CanvasEx/<Game_command>d__334::MoveNext()'.il)

[ChoiceMemoryTests]::RunMenu($assembly.methods.'System.Void CanvasEx::PaintCommand(Socotra.UI.StGraphics)'.il)
