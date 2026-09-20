$ErrorActionPreference='Stop'
$series=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$testBuild=Join-Path $PSScriptRoot 'build'
New-Item -ItemType Directory -Force $testBuild | Out-Null
$stubs=Get-Content -Raw (Join-Path $series 'games/08-kibu8/bepinex/tests/RuntimeStubs.cs')
$stubs=$stubs.Replace('public static BitmapFontAtlas Small;', 'public static BitmapFontAtlas Small,Primary;').Replace('Small=small;', 'Small=small;Primary=f;')
$stubs=$stubs.Replace('public void Patch(MethodBase a,HarmonyMethod b,HarmonyMethod c,object d,HarmonyMethod e,object f=null)', 'public void Patch(MethodBase a,HarmonyMethod prefix=null,HarmonyMethod postfix=null,object transpiler=null,HarmonyMethod finalizer=null,object f=null)')
$stubs=$stubs.Replace('public void UnpatchSelf() {}', 'public void UnpatchSelf() {} public void Unpatch(MethodBase original,MethodInfo patch) {}')
$stubs+="`nnamespace Kibukawa.Engine.Gmode20050817Direct { internal static class DirectChoiceMemory { internal static void Install(HarmonyLib.Harmony h,System.Type t) {} } }"
$stubs+="`nnamespace Kibu10ZhCN { internal static class UiLocalization { internal static void Initialize(System.Action<string> logger=null) {} internal static void RegisterDisplayTranslation(string source,string target) {} internal static void Update() {} internal static void Dispose() {} } internal static class UiLocalizationData { internal static readonly System.Collections.Generic.Dictionary<string,string> Exact=new System.Collections.Generic.Dictionary<string,string>(); internal static readonly System.Collections.Generic.Dictionary<string,string> Keys=new System.Collections.Generic.Dictionary<string,string>(); } internal static class ScriptIdentityData { internal static readonly System.Collections.Generic.Dictionary<string,string> Names=new System.Collections.Generic.Dictionary<string,string>(); } }"
$stubPath=Join-Path $testBuild 'RuntimeStubs.generated.cs'
[IO.File]::WriteAllText($stubPath,$stubs,[Text.UTF8Encoding]::new($false))
$sources=@(
'engine/core/TranslationCatalog.cs','engine/core/TranslationPackReader.cs',
'engine/adapters/gmode-20050817/RuntimePack.cs',
'engine/adapters/gmode-20050817/src/RuntimeLayout.cs',
'engine/adapters/gmode-20050817/src/NativeDialogueLayout.cs',
'engine/adapters/gmode-20050817/src/CanvasRuntime.cs',
'engine/adapters/gmode-20050817-direct/src/DirectCanvasRuntime.cs',
'engine/adapters/gmode-20050817-direct/src/DirectTextLayout.cs',
'games/10-kibu10/bepinex/build/generated/DirectLexicon.cs',
'engine/adapters/gmode-v2/src/TextBreaks.cs','engine/adapters/gmode-v2/src/TextGeometry.cs',
'games/10-kibu10/bepinex/src/Plugin.cs',
'games/10-kibu10/bepinex/tests/DirectRuntimeTests.cs') | ForEach-Object { Join-Path $series $_ }
Add-Type -Path ($sources+@($stubPath))
[DirectHarness]::Run()
