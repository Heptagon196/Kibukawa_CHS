"""Build the eighth-game memory-only translation using the shared BepInEx layer."""
import sys
import json
import subprocess
import time
from pathlib import Path
import pipeline as p


def main():
    if '--probe' in sys.argv:
        from build_probe import main as probe
        return probe()
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(p.SERIES/'engine/tools'), '-p', 'test_kbf3_atlas.py'], check=True)
    subprocess.run([sys.executable, str(p.SERIES/'engine/adapters/gmode-v2/ui/tests/run.py')], check=True)
    subprocess.run([sys.executable, str(p.WORK/'bepinex/tests/Run-HistoryAudio.py')], check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(p.SERIES/'engine/ui-assets'), '-p', 'test_ui_asset_catalog.py'], check=True)
    manifest = p.validate_sources()
    before = p.game_hashes()
    sys.path.insert(0, str(p.SERIES/'engine/bepinex'))
    import build as shared
    sys.path.insert(0, str(p.SERIES/'engine/adapters/gmode-20050817'))
    from runtime_pack import compile_pack, make_translation_pack, encode_translation_pack
    from generate_ui_data import generate
    from pagination import generate as generate_pagination
    generate_pagination(p.WORK)
    from translation import audit
    from build_pixel_font import build_font
    audit_result = audit()
    p.require(audit_result['pending'] == 0 and not audit_result['findings'], 'Incomplete text draft')
    exact, keys = generate()
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(p.SERIES/'engine/adapters/gmode-20050817'), '-p', 'test_*.py'], check=True)
    for adapter in ('gmode-v2', 'gmode-20050117'):
        subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(p.SERIES/'engine/adapters'/adapter), '-p', 'test_*.py'], check=True)
    output = p.WORK/'bepinex/build/plugin'
    output.mkdir(parents=True, exist_ok=True)
    scripts, text_report = compile_pack(p.WORK)
    reference = []
    for script in scripts:
        for display in script['displays']:
            for index, row in enumerate(display['rows']):
                digest = p.sha(row['text'].encode('utf-8') + b'\0' + bytes(row['colors']) + b'\0' + bytes(row['controls']))
                reference.append(f"{script['hash'].hex()}\t{display['offset']}\t{index}\t{digest}\n")
    (p.WORK/'reports/runtime-row-reference.tsv').write_text(''.join(reference), encoding='utf-8')
    script_names = {}
    for item in text_report['scripts']:
        script_names.setdefault(item['sha256'], item['name'])
    identity = p.WORK/'bepinex/src/ScriptIdentityData.cs'
    identity.write_text('using System.Collections.Generic;\nnamespace Kibukawa8.Runtime { internal static class ScriptIdentityData {\n'
        'internal static readonly Dictionary<string,string> Names = new Dictionary<string,string> {\n'
        + ''.join('{' + json.dumps(key) + ',' + json.dumps(value) + '},\n' for key,value in sorted(script_names.items()))
        + '};\n} }\n', encoding='utf-8')
    runtime = output/'translations.bin'
    readable = output/'translations.json'
    translated = make_translation_pack(scripts, manifest['source_hashes']['kibu8_Data/Managed/Assembly-CSharp.dll'],
        manifest['source_hashes']['kibu8_Data/StreamingAssets/scratchpad'],
        [dict(source=k,target=v,key=None) for k,v in sorted(exact.items())],
        [dict(source=None,target=v,key=k) for k,v in sorted(keys.items())], script_names=script_names)
    p.save(readable, translated)
    runtime.write_bytes(encode_translation_pack(translated))
    p.require(encode_translation_pack(p.load(readable)) == runtime.read_bytes(), 'Readable translation JSON differs from binary')
    text_report.update(sha256=p.sha(runtime.read_bytes()), bytes=runtime.stat().st_size)
    p.save(p.WORK/'reports/runtime-pack.json', text_report)
    font_report = build_font(output=output)
    from build_notebook_font import build as build_notebook_font
    build_notebook_font(output)
    source_manifest = output/'sources.sha256'
    source_manifest.write_text(''.join(h+'  '+name+'\n' for name,h in sorted(manifest['source_hashes'].items())), encoding='utf-8')
    config = p.load(p.WORK/'project.json')['bepinex']
    profile = p.load(p.SERIES/'engine/bepinex/profiles'/(config['profile']+'.json'))
    framework, dependency = shared.ensure_framework(p.SERIES/'engine/bepinex/locks'/profile['lock'], p.SERIES/'cache/bepinex'/config['profile'])
    sources = [p.SERIES/'engine/adapters/gmode-20050817/RuntimePack.cs',
        p.SERIES/'engine/core/TranslationCatalog.cs', p.SERIES/'engine/core/TranslationPackReader.cs',
        p.SERIES/'engine/adapters/gmode-v2/src/BitmapFontAtlas.cs',
        p.SERIES/'engine/adapters/gmode-v2/src/LegacyFontRenderer.cs']
    sources += [p.WORK/'bepinex/src'/name for name in ('Plugin.cs','NotebookReading.cs','PuzzleNotebook.cs','UiLocalization.cs','UiLocalizationData.cs','ScriptIdentityData.cs','NativePaginationData.cs')]
    sources += [p.SERIES/'engine/adapters/gmode-20050817/src'/name for name in ('CanvasRuntime.cs','RuntimeLayout.cs','NativeDialogueLayout.cs','NativeChoiceMemory.cs','NativePagination.cs','NativeMenuPosition.cs')]
    sources += [p.SERIES/'engine/adapters/gmode-v2/ui/src/UiLocalizationRuntime.cs']
    sources += [p.SERIES/'engine/adapters/gmode-v2/src'/name for name in ('PageMemory.cs','TextBreaks.cs','MenuMemory.cs','TextGeometry.cs')]
    references = list(config['references']) + ['UnityEngine.IMGUIModule.dll']
    plugin = output/config['assembly']
    shared.compile_plugin(framework, p.GAME/config['managed'], plugin, sources, p.WORK/'bepinex/build/compile.rsp', references)
    subprocess.run(['pwsh', '-NoProfile', '-File', str(p.WORK/'scripts/validate_runtime.ps1'), '-PluginDll', str(plugin),
                    '-ReportPath', str(p.WORK/'reports/runtime-bindings.json')], check=True)
    subprocess.run([sys.executable, str(p.WORK/'bepinex/tests/Run-MonoBindingProbe.py')], check=True)
    integration = subprocess.run(['pwsh', '-NoProfile', '-File', str(p.WORK/'bepinex/tests/Run-RuntimeTests.ps1')], check=True, capture_output=True, text=True)
    print(integration.stdout.strip())
    subprocess.run(['pwsh', '-NoProfile', '-File', str(p.WORK/'bepinex/tests/Run-ChoiceMemoryTests.ps1')], check=True)
    subprocess.run(['pwsh', '-NoProfile', '-File', str(p.WORK/'bepinex/tests/Run-ImageLifetimeTests.ps1')], check=True)
    geometry = subprocess.run(['pwsh', '-NoProfile', '-File', str(p.WORK/'bepinex/tests/Run-FontGeometryTests.ps1')], check=True, capture_output=True, text=True)
    print(geometry.stdout.strip())
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(p.WORK/'scripts'), '-p', 'test_pixel_font.py'], check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(p.WORK/'scripts'), '-p', 'test_command_icons.py'], check=True)
    history_sources = [p.WORK/'bepinex/history/HistoryPlugin.cs']
    history_sources += [p.PROJECT['adapter_path']/'src'/name for name in ('HistoryRuntime.cs','HistoryCapture.cs')]
    history_sources += [p.SERIES/'engine/adapters/gmode-v2/src'/name for name in ('HistoryView.cs','HistoryState.cs','HistoryAudioMute.cs')]
    history_sources += [p.SERIES/'engine/history/src'/name for name in ('HistoryBuffer.cs', 'ColoredHistoryLayout.cs', 'RuntimePolicy.cs')]
    history = p.WORK/'bepinex/build/history/KibukawaHistory.dll'
    shared.compile_plugin(framework, p.GAME/config['managed'], history, history_sources,
                          p.WORK/'bepinex/build/history/compile.rsp', references + ['UnityEngine.InputLegacyModule.dll','UnityEngine.AudioModule.dll'])
    subprocess.run([sys.executable, str(p.WORK/'bepinex/tests/Run-NotebookHistoryHook.py')], check=True)
    history_test = subprocess.run(['pwsh', '-NoProfile', '-File', str(p.WORK/'bepinex/tests/Run-HistoryTests.ps1')], check=True, capture_output=True, text=True)
    print(history_test.stdout.strip())
    image_output = p.WORK/'out'/('images_full_'+str(time.time_ns()))
    subprocess.run([sys.executable, str(p.WORK/'scripts/build_image_replacements.py'), '--output', str(image_output)], check=True)
    image_report = p.load(image_output/'build-report.json')
    sources += history_sources
    release = p.WORK/'out'/('translation_'+time.strftime('%Y%m%d_%H%M%S')+'_'+str(time.time_ns()%1000000000))
    package = release/'package'
    prefix = 'BepInEx/plugins/'+config['plugin_directory']+'/'
    payload = {prefix+name: output/name for name in (config['assembly'],'translations.bin','sources.sha256')}
    for name in ('fonts/dialogue-16.bin', 'fonts/dialogue-16.png',
                 'fonts/ui-12/dialogue-16.bin', 'fonts/ui-12/dialogue-16.png',
                 'fonts/roman/dialogue-16.bin', 'fonts/roman/dialogue-16.png'):
        payload[prefix+name] = output/name
    for file in (output/'licenses').rglob('*'):
        if file.is_file(): payload[prefix+file.relative_to(output).as_posix()] = file
    payload['README_Kibu8_CHS.txt'] = p.WORK/'bepinex/README_PATCH.txt'
    payload['BepInEx/licenses/BepInEx-LICENSE.txt'] = p.SERIES/'engine/bepinex/licenses/BepInEx-LICENSE.txt'
    payload['BepInEx/plugins/KibukawaHistory/KibukawaHistory.dll'] = history
    for name, expected in image_report['package_files'].items():
        file = image_output/'package'/name
        p.require(p.sha(file.read_bytes()) == expected, 'Image package hash mismatch: '+name)
        if name.startswith('BepInEx/plugins/KibukawaImageReplacements/images/') and name.endswith('.png'):
            continue
        p.require(name not in payload, 'Duplicate payload: '+name)
        payload[name] = file
    required_plugins = p.load(p.SERIES/'series.json')['required_plugins']
    p.require(all(name in payload for name in required_plugins.values()), 'Missing mandatory series plugin')
    runtime_dependency = dict(dependency, files=[name for name in dependency['files']
        if not name.endswith('.xml') and name != 'changelog.txt'])
    shared.stage_package(package, framework, runtime_dependency, payload, set(manifest['game_hashes']))
    archive = release/'Kibu8_CHS_0.5.69.zip'
    shared.archive_package(package, archive)
    p.require(before == p.game_hashes(), 'Game changed during build')
    report = dict(schema=1, version='0.5.69', output=release.relative_to(p.WORK).as_posix(), archive=archive.relative_to(p.WORK).as_posix(),
        archive_sha256=p.sha(archive.read_bytes()), package_files={f.relative_to(package).as_posix():p.sha(f.read_bytes()) for f in package.rglob('*') if f.is_file()},
        runtime_pack=text_report, font=font_report, dependency=dependency, integration_test=integration.stdout.strip(), font_geometry_test=geometry.stdout.strip(),
        required_plugins=required_plugins, images=image_report, history_version='1.6.5', history_test=history_test.stdout.strip(),
        sources={f.relative_to(p.SERIES).as_posix():p.sha(f.read_bytes()) for f in sources},
        shared_builder_sha256=p.sha((p.SERIES/'engine/bepinex/build.py').read_bytes()),
        original_game_unchanged=True, immutable_script_offsets=True, runtime_tested=False,
        limitations=['Runtime appearance requires user verification.', 'Image localization covers three titles, three menu highlights and shell cover.', 'Japanese ruby disabled on Chinese rows; metadata retained.'])
    p.save(release/'build_report.json', report)
    p.save(p.WORK/'reports/build_latest.json', report)
    print('BUILT '+str(archive))


if __name__ == '__main__': main()
