param([Parameter(Mandatory)][string]$PluginDll)
$ErrorActionPreference = 'Stop'
Add-Type -Path (Join-Path $PSScriptRoot '../../../bin/ilspy/tools/net6.0/any/Mono.Cecil.dll')
$assembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly([IO.Path]::GetFullPath($PluginDll))
try {
    if ($assembly.Name.Name -ne 'Kibu7Bootstrap') { throw 'Wrong output assembly' }
    $type = $assembly.MainModule.GetType('Kibu7ZhCN.BootstrapPlugin')
    if (!$type) { throw 'Seventh-game entry point missing' }
    $plugin = @($type.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInPlugin' })
    $process = @($type.CustomAttributes | Where-Object { $_.AttributeType.FullName -eq 'BepInEx.BepInProcess' })
    if ($plugin.Count -ne 1 -or $plugin[0].ConstructorArguments[0].Value -ne 'local.kibu7.bootstrap') { throw 'Wrong plugin ID' }
    if ($plugin[0].ConstructorArguments[2].Value -ne '0.1.0') { throw 'Wrong plugin version' }
    if ($process.Count -ne 1 -or $process[0].ConstructorArguments[0].Value -ne 'kibu7.exe') { throw 'Wrong process filter' }
    if ($assembly.MainModule.AssemblyReferences.Name -contains 'Kibu1ZhCN') { throw 'Must not depend on the first-game plugin' }
    foreach ($name in @('Kibu1ZhCN.TranslationCatalog','Kibu1ZhCN.TranslationPackReader','Kibu1ZhCN.BitmapFontAtlas','Kibu1ZhCN.LegacyFontRenderer','Kibu1ZhCN.MenuSelectionMemory')) {
        if (!$assembly.MainModule.GetType($name)) { throw "Shared source did not compile: $name" }
    }
    Write-Output 'PASS: seventh-game plugin identity, process filter, and shared sources verified offline.'
} finally { $assembly.Dispose() }
