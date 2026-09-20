"""Build the tenth history plugin without installing or launching the game."""
import subprocess
import sys
import pipeline as p
sys.path.insert(0, str(p.SERIES / 'engine/bepinex'))
import build as shared


def sources():
    result = [p.WORK / 'bepinex/src/HistoryPlugin.cs',
              p.PROJECT['adapter_path'] / 'src/HistoryRuntime.cs',
              p.SERIES / 'engine/adapters/gmode-20050817/src/HistoryCapture.cs']
    result += [p.SERIES / 'engine/adapters/gmode-v2/src' / name
               for name in ('HistoryView.cs', 'HistoryState.cs', 'HistoryAudioMute.cs')]
    result += [p.SERIES / 'engine/history/src' / name
               for name in ('HistoryBuffer.cs', 'ColoredHistoryLayout.cs', 'RuntimePolicy.cs')]
    return result


def build(framework=None):
    config = p.load(p.WORK / 'project.json')['bepinex']
    if framework is None:
        profile = p.load(p.SERIES / 'engine/bepinex/profiles' / (config['profile'] + '.json'))
        framework, _ = shared.ensure_framework(
            p.SERIES / 'engine/bepinex/locks' / profile['lock'],
            p.SERIES / 'cache/bepinex' / config['profile'])
    tests = p.WORK / 'bepinex/tests'
    subprocess.run([sys.executable, str(tests / 'test_history_bindings.py')], check=True)
    subprocess.run(['pwsh', '-NoProfile', '-File', str(tests / 'Run-HistoryTests.ps1')], check=True)
    output = p.WORK / 'bepinex/build/history/KibukawaHistory.dll'
    references = list(config['references']) + [
        'UnityEngine.IMGUIModule.dll', 'UnityEngine.InputLegacyModule.dll', 'UnityEngine.AudioModule.dll']
    shared.compile_plugin(framework, p.GAME / config['managed'], output, sources(),
                          output.parent / 'compile.rsp', references)
    p.save(p.WORK / 'reports/history-build.json', dict(
        source_sha256={file.relative_to(p.SERIES).as_posix(): p.sha(file.read_bytes()) for file in sources()},
        assembly_sha256=p.sha(output.read_bytes()),
        offline_tests_passed=True, runtime_tested=False))
    return {'BepInEx/plugins/KibukawaHistory/KibukawaHistory.dll': output}


if __name__ == '__main__':
    for name, path in build().items():
        print(name + ': ' + str(path))
