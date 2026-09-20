$ErrorActionPreference='Stop'
if($PSVersionTable.PSEdition -ne 'Desktop') {
    & "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath
    exit $LASTEXITCODE
}
$series=(Resolve-Path (Join-Path $PSScriptRoot '../../../..')).Path
$game=(Resolve-Path (Join-Path $series '../../GmodeArchivesPlus_kibu10')).Path
$managed=Join-Path $game 'kibu10_Data/Managed'
$core=Join-Path $game 'BepInEx/core'
$pluginPath=Join-Path $series 'games/10-kibu10/bepinex/build/plugin/Kibu10ZhCN.dll'

$resolver=[ResolveEventHandler]{
    param($sender,$eventArgs)
    $name=([Reflection.AssemblyName]$eventArgs.Name).Name+'.dll'
    foreach($folder in @($core,$managed,(Split-Path $pluginPath))) {
        $candidate=Join-Path $folder $name
        if(Test-Path -LiteralPath $candidate) { return [Reflection.Assembly]::LoadFrom($candidate) }
    }
    return $null
}
[AppDomain]::CurrentDomain.add_AssemblyResolve($resolver)
try {
    [void][Reflection.Assembly]::LoadFrom((Join-Path $core '0Harmony.dll'))
    $gameAssembly=[Reflection.Assembly]::LoadFrom((Join-Path $managed 'Assembly-CSharp.dll'))
    $plugin=[Reflection.Assembly]::LoadFrom($pluginPath)
    $canvas=$gameAssembly.GetType('CanvasEx',$true)
    $advance=$canvas.GetMethod('Game_adv',[Reflection.BindingFlags]'Instance,NonPublic,Public')
    $choice=$plugin.GetType('Kibukawa.Engine.Gmode20050817Direct.DirectChoiceMemory',$true)
    $runtime=$plugin.GetType('Kibukawa.Engine.Gmode20050817Direct.DirectCanvasRuntime',$true)
    $choiceFields=@{
        returnLabel='komando_modori'; normal='NowCommand'; longText='NowChobunCommand';
        position='Pos'; script='Script'; cursor='CommandCursorPos'; top='CommandTop'; stock='SentakuStock'
    }
    foreach($entry in $choiceFields.GetEnumerator()) {
        $choice.GetField($entry.Key,[Reflection.BindingFlags]'Static,NonPublic').SetValue(
            $null,[HarmonyLib.AccessTools]::Field($canvas,$entry.Value))
    }
    $choiceRewrite=$choice.GetMethod('Rewrite',[Reflection.BindingFlags]'Static,NonPublic')
    $recoveryRewrite=$runtime.GetMethod('RewriteAdvanceFailure',[Reflection.BindingFlags]'Static,NonPublic')
    $instructionReader=[HarmonyLib.PatchProcessor].GetMethods() | Where-Object {
        $_.Name -eq 'GetOriginalInstructions' -and $_.GetParameters().Count -eq 2 -and
        -not $_.GetParameters()[1].ParameterType.IsByRef
    }
    # Harmony may replay an already registered transpiler when another plugin
    # patches the same method. Re-read native IL for each real rebuild.
    for($attempt=0;$attempt -lt 2;$attempt++) {
        $generator=[HarmonyLib.PatchProcessor]::CreateILGenerator($advance)
        $readerArgs=New-Object object[] 2
        $readerArgs[0]=$advance
        $readerArgs[1]=$generator
        $original=$instructionReader.Invoke($null,$readerArgs)
        $choiceArgs=New-Object object[] 2
        $choiceArgs[0]=$original
        $choiceArgs[1]=$advance
        $afterChoice=$choiceRewrite.Invoke($null,$choiceArgs)
        $recoveryArgs=New-Object object[] 1
        $recoveryArgs[0]=$afterChoice
        [void]$recoveryRewrite.Invoke($null,$recoveryArgs)
    }
    Write-Output 'PASS: Game_adv choice, recovery and later plugin patches compose without aborting localization startup'
}
catch {
    Write-Error $_.Exception.ToString()
    throw
}
finally {
    [AppDomain]::CurrentDomain.remove_AssemblyResolve($resolver)
}
