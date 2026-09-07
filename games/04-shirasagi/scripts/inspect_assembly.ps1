param([Parameter(Mandatory)][string]$InputDll, [Parameter(Mandatory)][string]$OutputJson)
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$output = [IO.Path]::GetFullPath($OutputJson)
if (!$output.StartsWith($project + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Output must be inside this project' }
$parent = Get-Item -LiteralPath ([IO.Path]::GetDirectoryName($output))
while ($parent) {
    if ($parent.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Output parent is a reparse point' }
    $parent = $parent.Parent
}
Add-Type -Path (Join-Path $project '../../bin/ilspy/tools/net6.0/any/Mono.Cecil.dll')
function AllTypes($types) { foreach ($t in $types) { $t; AllTypes $t.NestedTypes } }
function Digest([string]$text) { [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($text))).ToLowerInvariant() }
$assembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly([IO.Path]::GetFullPath($InputDll))
try {
    $types = @(AllTypes $assembly.MainModule.Types)
    $methods = [ordered]@{}
    $fields = [ordered]@{}
    $initializedFields = [ordered]@{}
    $strings = [Collections.Generic.List[object]]::new()
    foreach ($type in $types) {
        foreach ($field in $type.Fields) {
            $fields[$field.FullName] = [string]$field.Attributes
            if ($field.InitialValue.Length -gt 0) { $initializedFields[$field.FullName] = [Convert]::ToBase64String($field.InitialValue) }
        }
        foreach ($method in $type.Methods) {
            if (!$method.HasBody) { continue }
            $instructions = $method.Body.Instructions
            $lines = @(
                foreach ($ins in $instructions) {
                    $operand = $ins.Operand
                    if ($operand -is [Mono.Cecil.Cil.Instruction]) { $operand = 'branch:' + $instructions.IndexOf($operand) }
                    elseif ($operand -is [Mono.Cecil.Cil.Instruction[]]) { $operand = 'switch:' + (($operand | ForEach-Object { $instructions.IndexOf($_) }) -join ',') }
                    elseif ($operand -is [Mono.Cecil.Cil.VariableDefinition]) { $operand = 'local:' + $operand.Index }
                    elseif ($operand -is [Mono.Cecil.ParameterDefinition]) { $operand = 'arg:' + $operand.Index }
                    if ($ins.OpCode.Code -eq [Mono.Cecil.Cil.Code]::Ldstr) {
                        $strings.Add([ordered]@{token=$method.MetadataToken.ToInt32(); instruction=$instructions.IndexOf($ins); method=$method.FullName; source_text=[string]$ins.Operand})
                    }
                    $ins.OpCode.Name + ' ' + [string]$operand
                }
            )
            $body = @('initlocals:' + $method.Body.InitLocals, 'locals:' + (($method.Body.Variables | ForEach-Object { $_.VariableType.FullName }) -join ',')) + $lines
            foreach ($handler in $method.Body.ExceptionHandlers) {
                $body += 'handler:' + $handler.HandlerType + ':' + $handler.CatchType + ':' + $instructions.IndexOf($handler.TryStart) + ':' + $instructions.IndexOf($handler.TryEnd) + ':' + $instructions.IndexOf($handler.HandlerStart) + ':' + $instructions.IndexOf($handler.HandlerEnd) + ':' + $instructions.IndexOf($handler.FilterStart)
            }
            $methods[$method.FullName] = [ordered]@{sha256=(Digest ($body -join "`n")); instructions=$instructions.Count; il=$lines; normalized_body=$body}
        }
    }
    $codecType = $types | Where-Object FullName -eq 'USEncoder.ToUnicode'
    $cctor = $codecType.Methods | Where-Object Name -eq '.cctor'
    $rva = $cctor.Body.Instructions | Where-Object { $_.OpCode.Code -eq [Mono.Cecil.Cil.Code]::Ldtoken } | Select-Object -First 1
    $codec = $rva.Operand.Resolve().InitialValue
    if ($codec.Length -ne 131074) { throw 'Unexpected codec length' }
    $result = [ordered]@{assembly_sha256=(Get-FileHash -LiteralPath $InputDll -Algorithm SHA256).Hash.ToLowerInvariant(); architecture=[string]$assembly.MainModule.Architecture; runtime=$assembly.MainModule.RuntimeVersion; methods=$methods; fields=$fields; initialized_fields=$initializedFields; strings=$strings; codec_base64=[Convert]::ToBase64String($codec)}
    [IO.File]::WriteAllText($output, ($result | ConvertTo-Json -Depth 12), [Text.UTF8Encoding]::new($false))
    Write-Output "Inspected $($methods.Count) methods, $($strings.Count) literal occurrences"
} finally { $assembly.Dispose() }
