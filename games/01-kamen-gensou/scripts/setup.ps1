$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$python = Join-Path $root '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $python)) {
    & python -m venv --without-pip (Join-Path $root '.venv')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& python -m pip --python $python install -r (Join-Path $root 'requirements.txt')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $python (Join-Path $root 'tools/setup_ilspy.py')
exit $LASTEXITCODE
