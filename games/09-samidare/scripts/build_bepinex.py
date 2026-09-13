"""Build the ninth-game release, labelled smoke package, or bootstrap probe.

The default release path is gated by the complete tagged draft, the shipped UI table,
the image source manifest and every offline runtime check. ``--smoke`` substitutes the
small labelled text fixture but still packages the completed UI/image/runtime layers.
"""
import subprocess
import sys
import time

import pipeline as p

sys.path.insert(0, str(p.SERIES / 'engine/bepinex'))
import build as shared

PLUGIN_DIR = 'BepInEx/plugins/'


def build_runtime():
    subprocess.run([sys.executable, str(p.WORK / 'scripts/build_runtime.py')], check=True)


def run_runtime_tests(pack_path=None):
    command = [p.shell(), '-NoProfile', '-File', str(p.WORK / 'bepinex/tests/Run-RuntimeTests.ps1')]
    if pack_path is not None:
        command.extend(['-PackPath', str(pack_path)])
    subprocess.run(command, check=True)
    subprocess.run([p.shell(), '-NoProfile', '-File', str(p.WORK / 'bepinex/tests/Run-HistoryTests.ps1')], check=True)


def build_pack(smoke, output=None):
    command = [sys.executable, str(p.WORK / 'scripts/build_pack.py')]
    if smoke:
        command.append('--smoke')
    if output is not None:
        command.extend(['--output', str(output)])
    subprocess.run(command, check=True)


def build_font(smoke):
    sys.path.insert(0, str(p.WORK / 'scripts'))
    import build_pixel_font
    draft = p.WORK / ('work/smoke-lines.json' if smoke else 'work/dialogue-tagged.json')
    return build_pixel_font.build(output=p.WORK / 'bepinex/build/pack/fonts', draft=draft)


def build_images():
    output = p.WORK / 'out' / ('images_build_' + str(time.time_ns()))
    subprocess.run([sys.executable, str(p.WORK / 'scripts/build_image_replacements.py'),
                    '--output', str(output)], check=True)
    return output, p.load(output / 'build-report.json')


HISTORY_SOURCES = [
    'engine/history/src/HistoryBuffer.cs',
    'engine/history/src/ColoredHistoryLayout.cs',
    'engine/history/src/RuntimePolicy.cs',
    'engine/adapters/gmode-v2/src/HistoryView.cs',
    'engine/adapters/gmode-v2/src/HistoryState.cs',
    'engine/adapters/gmode-v2/src/HistoryAudioMute.cs',
    'engine/adapters/gmode-20050117/src/HistoryRuntime.cs',
    'games/09-samidare/bepinex/history/HistoryPlugin.cs',
]


def build_history(framework, references):
    """Compile the shared history layer plus this version's capture glue."""
    output = p.inside(p.WORK / 'bepinex/build/history/KibukawaHistory.dll')
    output.parent.mkdir(parents=True, exist_ok=True)
    sources = [p.SERIES / name for name in HISTORY_SOURCES]
    for source in sources:
        p.require(source.is_file(), 'Missing history source: ' + str(source))
    shared.compile_plugin(framework, p.GAME / 'kibu9_Data/Managed', output, sources,
                          p.WORK / 'bepinex/build/history/compile.rsp',
                          references + ['UnityEngine.IMGUIModule.dll', 'UnityEngine.AudioModule.dll',
                                        'UnityEngine.InputLegacyModule.dll'])
    return output


def main():
    if '--probe' in sys.argv:
        from build_probe import main as probe
        return probe()
    smoke = '--smoke' in sys.argv
    if not smoke:
        subprocess.run([sys.executable, str(p.WORK / 'scripts/translation_batch.py'),
                        'check', '--strict'], check=True)
    manifest = p.validate_sources()
    config = p.load(p.WORK / 'project.json')
    bepinex = config['bepinex']
    build_runtime()
    build_pack(smoke)
    font = build_font(smoke)
    image_output, image_report = build_images()
    # RuntimeTests is a deterministic behavioural fixture whose assertions refer to
    # smoke-lines.json.  A release pack legitimately translates additional slots and
    # can use revised final wording, so exercise the production runtime with a separate
    # smoke pack instead of treating the release data as the test fixture.
    runtime_pack = None
    if not smoke:
        runtime_pack = p.WORK / 'bepinex/build/runtime-test-pack'
        build_pack(True, runtime_pack)
        runtime_pack = runtime_pack / 'translations.bin'
    run_runtime_tests(runtime_pack)
    profile = p.load(p.SERIES / 'engine/bepinex/profiles' / (bepinex['profile'] + '.json'))
    framework, dependency = shared.ensure_framework(p.SERIES / 'engine/bepinex/locks' / profile['lock'],
                                                    p.SERIES / 'cache/bepinex' / bepinex['profile'])
    history = build_history(framework, bepinex['references'])
    binding = subprocess.run([p.shell(), '-NoProfile', '-File', str(p.WORK / 'scripts/validate_history.ps1'),
                              '-PluginDll', str(history),
                              '-GameDll', str(p.GAME / bepinex['managed'] / 'Assembly-CSharp.dll'),
                              '-ReportPath', str(p.WORK / 'reports/history-bindings.json')],
                             check=True, capture_output=True, text=True)
    print(binding.stdout.strip())
    staged = p.WORK / 'bepinex/build/pack'
    kind = 'smoke_' if smoke else 'translation_'
    release = p.inside(p.WORK / 'out' / (kind + time.strftime('%Y%m%d_%H%M%S') + '_' + str(time.time_ns() % 1000000000)))
    package = release / 'package'
    prefix = PLUGIN_DIR + bepinex['plugin_directory'] + '/'
    payload = {
        prefix + bepinex['assembly']: p.WORK / 'bepinex/build/plugin' / bepinex['assembly'],
        prefix + 'translations.bin': staged / 'translations.bin',
        prefix + 'translations.json': staged / 'translations.json',
        prefix + 'fonts/dialogue-16.bin': staged / 'fonts/dialogue-16.bin',
        prefix + 'fonts/dialogue-16.png': staged / 'fonts/dialogue-16.png',
        prefix + 'fonts/font-dependency.lock.json': staged / 'fonts/font-dependency.lock.json',
        'BepInEx/plugins/KibukawaHistory/KibukawaHistory.dll': history,
        'README_Kibu9_CHS.txt': p.WORK / ('bepinex/README_SMOKE.txt' if smoke else 'bepinex/README_PATCH.txt'),
        'BepInEx/licenses/BepInEx-LICENSE.txt': p.SERIES / 'engine/bepinex/licenses/BepInEx-LICENSE.txt',
    }
    for name, expected in image_report['package_files'].items():
        file = image_output / 'package' / name
        p.require(p.sha(file.read_bytes()) == expected, 'Image package hash mismatch: ' + name)
        # The RGBA payloads are the runtime source; PNG copies under images/ are review aids.
        if name.startswith('BepInEx/plugins/KibukawaImageReplacements/images/') and name.endswith('.png'):
            continue
        p.require(name not in payload, 'Duplicate package payload: ' + name)
        payload[name] = file
    required = p.load(p.SERIES / 'series.json')['required_plugins']
    for name in required.values():
        if name.endswith('KibukawaHistory.dll'):
            p.require(name in payload, 'Missing mandatory history plugin in the package')
    missing_plugins = sorted(name for name in required.values() if name not in payload)
    if missing_plugins:
        raise SystemExit('Package is missing mandatory series plugins: ' + ', '.join(missing_plugins))
    for license_file in sorted((staged / 'fonts/licenses').glob('*')):
        payload[prefix + 'licenses/' + license_file.name] = license_file
    shared.stage_package(package, framework, dependency, payload, set(manifest['game_hashes']))
    archive = release / ('Kibu9_SMOKE_NOT_RELEASE.zip' if smoke else 'Kibu9_CHS_0.1.0.zip')
    shared.archive_package(package, archive)
    limitations = (['Smoke fixture only: 15 opening lines of c0_00 plus a few names, menu labels and UI strings.',
                    'Runtime appearance and input require user verification.'] if smoke else
                   ['Runtime appearance and input require user verification.'])
    report = dict(schema=1, version=None if smoke else '0.1.0', smoke=smoke,
                  release_ready=not smoke, runtime_tested=False,
                  archive=archive.relative_to(p.WORK).as_posix(), archive_sha256=p.sha(archive.read_bytes()),
                  lines=p.load(staged / 'pack-report.json')['lines'], font=font,
                  images=image_report,
                  history_version='1.0.0', history_sha256=p.sha(history.read_bytes()),
                  missing_required_plugins=missing_plugins,
                  package_files={f.relative_to(package).as_posix(): p.sha(f.read_bytes())
                                 for f in package.rglob('*') if f.is_file()},
                  original_game_unchanged=True,
                  immutable_script_offsets=True,
                  limitations=limitations)
    p.save(release / 'build_report.json', report)
    p.save(p.WORK / ('reports/smoke_latest.json' if smoke else 'reports/build_latest.json'), report)
    print(('SMOKE PACKAGE (not a release): ' if smoke else 'BUILT RELEASE: ') + str(archive))


if __name__ == '__main__':
    main()
