$ErrorActionPreference='Stop'
$series=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$game=Join-Path $series 'games/10-kibu10'
$sources=@('engine/core/TranslationCatalog.cs','engine/core/TranslationPackReader.cs',
'engine/adapters/gmode-20050817/src/NativeDialogueLayout.cs',
'engine/adapters/gmode-20050817-direct/src/DirectTextLayout.cs',
'games/10-kibu10/bepinex/build/generated/DirectLexicon.cs',
'engine/adapters/gmode-20050817/src/RuntimeLayout.cs',
'engine/adapters/gmode-v2/src/TextGeometry.cs',
'engine/adapters/gmode-v2/src/TextBreaks.cs',
'games/10-kibu10/bepinex/build/generated/RuntimePack.cs',
'games/10-kibu10/bepinex/src/ScriptIdentityData.cs',
'games/10-kibu10/bepinex/tests/DirectPackBindingTests.cs') | ForEach-Object {Join-Path $series $_}
Add-Type -Path $sources
$original=Join-Path $series '../../GmodeArchivesPlus_kibu10/kibu10_Data/Managed/Assembly-CSharp.dll'
[DirectPackBindingTests]::Run($game,$original)
