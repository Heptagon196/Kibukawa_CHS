"""Build the independent history add-on against every enabled local game."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
SERIES = ROOT.parent.parent
sys.path.insert(0, str(SERIES / 'engine/bepinex'))
import build as shared

def main():
    output = SERIES / 'out/history'
    output.mkdir(parents=True, exist_ok=True)
    framework = SERIES.parent
    config = json.loads((SERIES / 'series.json').read_text(encoding='utf-8-sig'))
    hashes = {}
    files = {}
    for game, entry in config['games'].items():
        if not entry['enabled']:
            continue
        managed = (SERIES / entry['installation']).resolve() / (game + '_Data/Managed')
        dest = output / game
        dest.mkdir(exist_ok=True)
        shared.compile_plugin(framework, managed, dest / 'KibukawaHistory.dll', sorted((ROOT/'src').glob('*.cs')),
                              dest/'compile.rsp', ['mscorlib.dll', 'netstandard.dll', 'System.dll', 'System.Core.dll',
                              'UnityEngine.dll', 'UnityEngine.CoreModule.dll', 'UnityEngine.UI.dll',
                              'UnityEngine.UIModule.dll', 'UnityEngine.TextRenderingModule.dll',
                              'UnityEngine.IMGUIModule.dll', 'UnityEngine.InputLegacyModule.dll'])
        files[game] = {'KibukawaHistory.dll': hashlib.sha256((dest/'KibukawaHistory.dll').read_bytes()).hexdigest()}
        hashes[game] = hashlib.sha256((dest/'KibukawaHistory.dll').read_bytes()).hexdigest()
    compiler = Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
    test = output/'HistoryTests.exe'
    subprocess.run([str(compiler), '/nologo', '/out:'+str(test), str(ROOT/'src/HistoryBuffer.cs'), str(ROOT/'src/ColoredHistoryLayout.cs'), str(ROOT/'tests/HistoryTests.cs')], check=True)
    subprocess.run([str(test)], check=True)
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT/'tests/runtime-policy.ps1')], check=True)
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ROOT/'tests/validate.ps1')], check=True)
    for game in hashes:
        with zipfile.ZipFile(output/(game+'-history-1.6.1.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
            for relative in files[game]:
                archive.write(output/game/relative, 'BepInEx/plugins/KibukawaHistory/'+relative)
            archive.write(ROOT/'README.md', '历史记录说明.md')
            archive.write(SERIES/'LICENSE', 'LICENSE')
        with zipfile.ZipFile(output/(game+'-history-1.6.1.zip')) as archive:
            assert len(archive.namelist()) == 3, 'Unexpected personal data in release'
            assert hashlib.sha256(archive.read('BepInEx/plugins/KibukawaHistory/KibukawaHistory.dll')).hexdigest() == hashes[game]
    (output/'manifest.json').write_text(json.dumps({'version':'1.6.1', 'sha256':hashes, 'files':files,
        'validation':'five-game compile, hook metadata, buffer, coroutine and idle left-softkey hint tests; live interaction pending'}, indent=2), encoding='utf-8')
    print('History add-ons built and verified: '+', '.join(hashes))

if __name__ == '__main__':
    main()
