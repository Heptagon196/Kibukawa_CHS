param([ValidateSet('extract','build','verify')][string]$Mode, [string]$InputDll, [string]$JsonPath, [string]$OutputDll, [switch]$Utf8, [switch]$AllStrings)
$ErrorActionPreference = 'Stop'
$paths = & (Join-Path $PSScriptRoot '../../../tools/project_paths.ps1') -Project (Join-Path $PSScriptRoot '..')
function Assert-WorkspaceOutput([string]$value) {
    if (!$value) { return }
    $workspace = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..')) + [IO.Path]::DirectorySeparatorChar
    $target = [IO.Path]::GetFullPath($value)
    if (!$target.StartsWith($workspace, [StringComparison]::OrdinalIgnoreCase)) { throw "Output must remain inside workspace: $target" }
    # Resolve existing parent links too; do not allow a junction to redirect a write.
    $parent = Get-Item -LiteralPath ([IO.Path]::GetDirectoryName($target))
    while ($parent -and $parent.FullName.StartsWith($workspace.TrimEnd('\'), [StringComparison]::OrdinalIgnoreCase)) {
        if ($parent.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Output parent is a reparse point' }
        $parent = $parent.Parent
    }
}
if ($Mode -eq 'extract') { Assert-WorkspaceOutput $JsonPath }
Assert-WorkspaceOutput $OutputDll
Add-Type -Path (Join-Path $paths.Series 'bin/ilspy/tools/net6.0/any/Mono.Cecil.dll')
function AllTypes($types) { foreach ($t in $types) { $t; AllTypes $t.NestedTypes } }
if ($Mode -eq 'verify') {
    $a = [System.Reflection.Assembly]::LoadFile([IO.Path]::GetFullPath($InputDll))
    $t = $a.GetType('USEncoder.ToEncoding', $true)
    $m = $t.GetMethod('ToUnicode')
    [byte[]]$bytes = [byte[]](239,187,191) + [Text.Encoding]::UTF8.GetBytes('中文测试')
    $arguments = [object[]]::new(1)
    $arguments[0] = $bytes
    $actual = $m.Invoke($null, $arguments)
    if ($actual -cne '中文测试') { throw "UTF-8 decoder check failed: $actual" }
    $arguments[0] = [byte[]](0x82,0xa0)
    $actual = $m.Invoke($null, $arguments)
    if ($actual -cne 'あ') { throw 'Original SJIS decoder check failed' }
    Write-Output 'UTF-8 and original SJIS decoder checks passed'
    exit 0
}
$resolver = [Mono.Cecil.DefaultAssemblyResolver]::new()
$resolver.AddSearchDirectory([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($InputDll)))
$resolver.AddSearchDirectory([IO.Path]::GetFullPath((Join-Path $paths.Game 'kibu1_Data/Managed')))
$rp = [Mono.Cecil.ReaderParameters]::new()
$rp.AssemblyResolver = $resolver
$asm = [Mono.Cecil.AssemblyDefinition]::ReadAssembly([IO.Path]::GetFullPath($InputDll), $rp)
try {
    $module = $asm.MainModule
    $types = @(AllTypes $module.Types)
    if ($Mode -eq 'extract') {
        $rows = @(
            foreach ($t in $types) { foreach ($m in $t.Methods) {
                if (!$m.HasBody) { continue }
                for ($i=0; $i -lt $m.Body.Instructions.Count; $i++) {
                    $ins = $m.Body.Instructions[$i]
                    if ($ins.OpCode.Code -eq [Mono.Cecil.Cil.Code]::Ldstr -and ($AllStrings -or [string]$ins.Operand -match '[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]')) {
                        [ordered]@{ token=$m.MetadataToken.ToInt32(); instruction=$i; method=$m.FullName; source_text=[string]$ins.Operand }
                    }
                }
            } }
        )
        $codecType = $types | Where-Object FullName -eq 'USEncoder.ToUnicode'
        $cctor = $codecType.Methods | Where-Object Name -eq '.cctor'
        $rva = $cctor.Body.Instructions | Where-Object { $_.OpCode.Code -eq [Mono.Cecil.Cil.Code]::Ldtoken } | Select-Object -First 1
        $codec = $rva.Operand.Resolve().InitialValue
        if ($codec.Length -ne 131074) { throw 'Unexpected SJIS lookup table size' }
        $result = [ordered]@{ strings=$rows; codec_base64=[Convert]::ToBase64String($codec) }
        [IO.File]::WriteAllText([IO.Path]::GetFullPath($JsonPath), ($result | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
        Write-Output "Extracted $($rows.Count) assembly string occurrences"
    } else {
        $patches = Get-Content -LiteralPath $JsonPath -Raw -Encoding utf8 | ConvertFrom-Json
        foreach ($p in $patches) {
            $m = $module.LookupToken([int]$p.token)
            $ins = $m.Body.Instructions[[int]$p.instruction]
            if ($ins.OpCode.Code -ne [Mono.Cecil.Cil.Code]::Ldstr -or [string]$ins.Operand -cne $p.source_text) { throw 'Assembly source string mismatch' }
            $ins.Operand = [string]$p.translated_text
        }
        if ($Utf8) {
            $t = $types | Where-Object FullName -eq 'USEncoder.ToEncoding'
            $m = $t.Methods | Where-Object Name -eq 'ToUnicode'
            $runtime = $types | Where-Object FullName -eq 'SocotraRuntime'
            $refs = @($runtime.Methods | ForEach-Object { if ($_.HasBody) { $_.Body.Instructions } })
            $getter = ($refs | Where-Object { $_.Operand -is [Mono.Cecil.MethodReference] -and $_.Operand.FullName -eq 'System.Text.Encoding System.Text.Encoding::get_UTF8()' } | Select-Object -First 1).Operand
            $getstring = ($refs | Where-Object { $_.Operand -is [Mono.Cecil.MethodReference] -and $_.Operand.FullName -eq 'System.String System.Text.Encoding::GetString(System.Byte[],System.Int32,System.Int32)' } | Select-Object -First 1).Operand
            if (!$getter -or !$getstring) { throw 'UTF8 method references not found' }
            $il = $m.Body.GetILProcessor()
            $first = $m.Body.Instructions[0]
            $ops = [Mono.Cecil.Cil.OpCodes]
            $prefix = [Collections.Generic.List[Mono.Cecil.Cil.Instruction]]::new()
            $prefix.Add($il.Create($ops::Ldarg_0)); $prefix.Add($il.Create($ops::Ldlen)); $prefix.Add($il.Create($ops::Conv_I4))
            $prefix.Add($il.Create($ops::Ldc_I4_3)); $prefix.Add($il.Create($ops::Blt, $first))
            for ($i=0; $i -lt 3; $i++) {
                $prefix.Add($il.Create($ops::Ldarg_0)); $prefix.Add($il.Create($ops::Ldc_I4, [int]$i)); $prefix.Add($il.Create($ops::Ldelem_U1))
                $prefix.Add($il.Create($ops::Ldc_I4, [int]@(239,187,191)[$i])); $prefix.Add($il.Create($ops::Bne_Un, $first))
            }
            $prefix.Add($il.Create($ops::Call, $getter)); $prefix.Add($il.Create($ops::Ldarg_0)); $prefix.Add($il.Create($ops::Ldc_I4_3))
            $prefix.Add($il.Create($ops::Ldarg_0)); $prefix.Add($il.Create($ops::Ldlen)); $prefix.Add($il.Create($ops::Conv_I4))
            $prefix.Add($il.Create($ops::Ldc_I4_3)); $prefix.Add($il.Create($ops::Sub)); $prefix.Add($il.Create($ops::Callvirt, $getstring)); $prefix.Add($il.Create($ops::Ret))
            foreach ($ins in $prefix) { $il.InsertBefore($first, $ins) }
        }
        $asm.Write([IO.Path]::GetFullPath($OutputDll))
        Write-Output "Built assembly copy: $OutputDll"
    }
} finally { $asm.Dispose(); $resolver.Dispose() }
