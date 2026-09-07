"""Compile/package a fourth-game bootstrap probe using the shared build layer.
This is intentionally not a translation release and never installs or launches.
"""
import argparse
import json
import struct
import subprocess
import sys
import time

import pipeline as p

sys.path.insert(0, str(p.SERIES/'engine/bepinex'))
import build as shared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', required=True)
    parser.parse_args()
    manifest = p.validate_sources()
    p.status()
    before = p.game_hashes()
    first_before = p.first_project_hashes()
    config = p.load(p.WORK/'project.json')
    target = dict(config['bepinex'], assembly='Kibu4Bootstrap.dll', plugin_directory='Kibu4Bootstrap')
    profile = p.load(p.SERIES/'engine/bepinex/profiles'/(target['profile']+'.json'))
    p.require(profile['backend'] == 'mono' and profile['architecture'] == 'x64' and profile['platform'] == 'windows', 'Unsupported profile')
    executable = (p.GAME/'kibu4.exe').read_bytes()
    pe = struct.unpack_from('<I', executable, 0x3c)[0]
    p.require(executable[pe:pe+4] == b'PE\0\0' and struct.unpack_from('<H', executable, pe+4)[0] == 0x8664, 'Expected AMD64 PE game executable')
    p.require((p.GAME/'MonoBleedingEdge').is_dir() and not (p.GAME/'GameAssembly.dll').exists(), 'Expected Mono backend')
    lock_path = p.SERIES/'engine/bepinex/locks'/profile['lock']
    framework, dependency = shared.ensure_framework(lock_path, p.SERIES/'cache/bepinex'/target['profile'])
    output = p.inside(p.WORK/'bepinex/build/plugin')
    output.mkdir(parents=True, exist_ok=True)
    # Reuse framework, core, font and menu code as sources. No first-game project
    # imports, addresses, help pages, release files or translations are copied.
    sources = sorted((p.SERIES/'engine/core').glob('*.cs'))
    sources += [p.SERIES/'engine/adapters/gmode-v1/src'/name for name in
                ('BitmapFontAtlas.cs', 'LegacyFontRenderer.cs', 'MenuSelectionMemory.cs')]
    sources += [p.WORK/'bepinex/src/BootstrapPlugin.cs']
    plugin = output/target['assembly']
    shared.compile_plugin(framework, p.GAME/target['managed'], plugin, sources,
                          p.WORK/'bepinex/build/compile.rsp', target['references'])
    result = subprocess.run(['pwsh', '-NoProfile', '-File', str(p.WORK/'scripts/validate_probe.ps1'),
                             '-PluginDll', str(plugin)], check=True, capture_output=True, text=True)
    print(result.stdout.strip())
    release = p.inside(p.WORK/'out'/('bootstrap_'+time.strftime('%Y%m%d_%H%M%S')+'_'+str(time.time_ns()%1000000000)))
    package = release/'package'
    payload = {
        'BepInEx/plugins/'+target['plugin_directory']+'/'+target['assembly']: plugin,
        'README_BUILD_PROBE.txt': p.WORK/'bepinex/README_PROBE.txt',
        'BepInEx/licenses/BepInEx-LICENSE.txt': p.SERIES/'engine/bepinex/licenses/BepInEx-LICENSE.txt',
    }
    shared.stage_package(package, framework, dependency, payload, set(before))
    archive = release/'Kibu4_Bootstrap_NOT_TRANSLATION.zip'
    shared.archive_package(package, archive)
    p.require(p.game_hashes() == before, 'Fourth-game files changed during build')
    p.require(p.first_project_hashes() == first_before, 'Previous-game project files changed during build')
    report = dict(edition='bootstrap-only, no translation hooks', plugin_version='0.1.0',
                  output=release.relative_to(p.WORK).as_posix(), archive=archive.relative_to(p.WORK).as_posix(),
                  archive_sha256=p.sha(archive.read_bytes()), dependency=dependency,
                  source_hashes=manifest['source_hashes'], profile=profile,
                  sources={x.relative_to(p.SERIES).as_posix(): p.sha(x.read_bytes()) for x in sources},
                  shared_builder_sha256=p.sha((p.SERIES/'engine/bepinex/build.py').read_bytes()),
                  translation_sha256=p.sha((p.WORK/'work/cache.json').read_bytes()),
                  plugin_metadata_verified=True, original_game_unchanged=True, previous_projects_unchanged=True,
                  runtime_tested=False, translation_hooks=False, release_ready=False,
                  omitted_adapter_sources=['DialogueReflow.cs: game-specific ChatLayout and FixedCardLayout policies pending'],
                  package_files={x.relative_to(package).as_posix(): p.sha(x.read_bytes()) for x in package.rglob('*') if x.is_file()})
    p.save(release/'build_report.json', report)
    p.save(p.WORK/'reports/bootstrap_latest.json', report)
    print('PROBE READY (not a translation patch): ' + str(archive))


if __name__ == '__main__':
    main()
