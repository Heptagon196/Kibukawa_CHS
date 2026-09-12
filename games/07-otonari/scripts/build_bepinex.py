"""Build and validate the kibu7 runtime translation without installing/launching."""
import argparse
import base64
import collections
import io
import re
import struct
import subprocess
import sys
import time
import zipfile

import pipeline as p

sys.path.insert(0, str(p.SERIES/'tools'))
from click_boundaries import validate as validate_click_boundaries

sys.path.insert(0, str(p.SERIES/'engine/bepinex'))
import build as shared


def write_binary_pack(pack, destination):
    data = io.BytesIO()
    def integer(value):
        data.write(struct.pack('<i', value))
    def text(value):
        encoded = value.encode('utf-8') if value is not None else None
        integer(len(encoded) if encoded is not None else -1)
        if encoded is not None:
            data.write(encoded)
    data.write(b'KBZH')
    integer(pack['schema'])
    text(pack['gameAssemblySha256'])
    text(pack['scratchpadSha256'])
    integer(len(pack['scripts']))
    for entry in pack['scripts']:
        for key in ('index', 'instruction', 'slot', 'opcode'):
            integer(entry[key])
        for key in ('script', 'source', 'target'):
            text(entry[key])
    for group in ('ui', 'localization'):
        integer(len(pack[group]))
        for entry in pack[group]:
            for key in ('source', 'target', 'key'):
                text(entry.get(key))
    integer(len(pack['literals']))
    for entry in pack['literals']:
        for key in ('index', 'token', 'instruction'):
            integer(entry[key])
        for key in ('source', 'target', 'method'):
            text(entry[key])
    p.inside(destination).write_bytes(data.getvalue())


def export_pack(output):
    manifest = p.validate_sources()
    cache = p.load(p.WORK/'work/cache.json')
    config = p.load(p.WORK/'project.json')
    menu_labels = p.load(p.WORK/'bepinex/menu-labels.json')
    rows = [x for group in cache['files'].values() for x in group['items']]
    by_id = {x['text_index']: x for x in rows}
    p.require(len(rows) == len(by_id) == len(manifest['entries']), 'Missing or duplicate cache entries')
    definitions = {int(key): value for key, value in manifest['definitions'].items()}
    pack = dict(schema=1, gameAssemblySha256=manifest['source_hashes'][p.DLL],
                scratchpadSha256=manifest['source_hashes'][p.STREAM+'scratchpad'], scripts=[], ui=[], localization=[], literals=[])
    ui = collections.defaultdict(set)
    for entry in manifest['entries']:
        row = by_id[entry['text_index']]
        loc = entry['location']
        p.require(row['source_text'] == entry['source_text'] and row['extra']['location'] == loc, 'Source/position changed at '+str(entry['text_index']))
        if entry['excluded'] or str(entry['text_index']) in config.get('reviewed_exclusions', {}):
            p.require(row['translation_status'] == 7 and row['translated_text'] == '', 'Protected entry changed')
            continue
        p.require(row['translation_status'] in (1, 2), 'Untranslated entry '+str(entry['text_index']))
        target = row['translated_text']
        retained=config.get('approved_preserved_terms',{}).get(str(entry['text_index']),{})
        approved=retained.get('term')==target and target in row['source_text'] and bool(retained.get('reason'))
        p.require(isinstance(target, str) and '\0' not in target and (not re.search(r'[ぁ-ゖァ-ヺｦ-ﾟ]', target) or approved), 'Invalid target or kana residue')
        if target == '':
            empty=config.get('approved_empty_layout_text', {}).get(str(entry['text_index']), {})
            p.require(loc['kind']=='script' and loc['opcode']==72 and empty.get('source')==row['source_text'] and empty.get('target')=='' and empty.get('reason'), 'Unapproved empty translation')
        if loc['kind'] == 'script':
            p.require(not any(c in target for c in '\r\n\t') and len(target.encode('utf-16-le'))//2 <= 20, 'Invalid script buffer content')
        tokens = lambda text: collections.Counter(re.findall(r'\{\d+(?:[^{}]*)\}|</?[A-Za-z][^>]*>', text))
        p.require(tokens(target) == tokens(row['source_text']), 'Placeholder/tag mismatch')
        if loc['kind'] == 'script' and 105 <= loc['opcode'] < 120:
            target = menu_labels.get(row['source_text'], target)
        base = dict(index=entry['text_index'], source=row['source_text'], target=target)
        if loc['kind'] == 'script':
            script = loc.get('member') or 'subscn_'+str(loc['part']+1)
            slot = definitions[loc['opcode']][:loc['argument']].count(3)
            pack['scripts'].append(dict(base, script=script, instruction=loc['instruction'], slot=slot, opcode=loc['opcode']))
        else:
            ui[base['source']].add(target)
            if loc['kind'] == 'csv':
                pack['localization'].append(dict(source=base['source'], target=target, key=loc['key']))
            elif loc['kind'] == 'assembly':
                pack['literals'].append(dict(base, token=loc['token'], instruction=loc['instruction'], method=loc['method']))
    # Visible Text labels only; excluded CharacterInputKeySettings keys remain untouched.
    for label in p.load(p.WORK/'bepinex/display-labels.json')['labels']:
        ui[label['source']].add(label['target'])
    for source, targets in ui.items():
        p.require(len(targets) == 1, 'Conflicting UI targets: '+source)
        pack['ui'].append(dict(source=source, target=next(iter(targets))))
    p.save(output/'translations.json', pack)
    write_binary_pack(pack, output/'translations.bin')
    # Reparse actual original bytes. No original script/jump/save is rewritten.
    assets = p.text_assets(p.GAME/(p.STREAM+'file'))
    p.require(p.definitions(assets['define']) == definitions, 'Command definitions changed')
    archive = zipfile.ZipFile(io.BytesIO(p.text_assets(p.GAME/(p.STREAM+'scratchpad'))[config['resource_archive']]))
    scripts = {name: archive.read(name) for name in archive.namelist() if re.fullmatch(r'scn\d+', name)}
    scripts.update({'subscn_'+str(i+1): data for i, data in enumerate(p.sub_parts(assets['subscn']))})
    table = struct.unpack('<65537H', base64.b64decode(manifest['codec_base64']))
    targets = {(e['script'], e['instruction'], e['slot']): e['target'] for e in pack['scripts']}
    replay, slots = [], set()
    for name, data in scripts.items():
        for command in p.parse_script(data, definitions):
            strings = [p.decode(arg['value'], table) if arg['value'] else None for arg in command['args'] if arg['kind'] == 3]
            integers = [arg['value'] if arg['value'] < 2147483648 else arg['value']-4294967296 for arg in command['args'] if arg['kind'] != 3]
            expected = [targets.get((name, command['offset'], i), value) for i, value in enumerate(strings)]
            slots.update((name, command['offset'], i) for i in range(len(strings)))
            replay.append(dict(script=name, instruction=command['offset'], opcode=command['opcode'], nextCursor=command['end'], strings=strings, expected=expected, integers=integers))
    p.require(set(targets).issubset(slots), 'Translation refers to a nonexistent script slot')
    p.save(p.WORK/'bepinex/build/replay.json', dict(commands=replay))
    from tagged_dialogue import validate as validate_tags
    validate_tags(replay)
    subprocess.run([sys.executable, str(p.WORK/'scripts/validate_translation.py')], check=True)
    validate_click_boundaries(replay, p.WORK)
    return pack, manifest



def build_history(framework):
    """Compile public history sources for this game only; do not rebuild other games."""
    root=p.SERIES/'engine/history'; dest=p.WORK/'bepinex/build/history'; dest.mkdir(parents=True,exist_ok=True)
    sources=sorted((root/'src').glob('*.cs'))
    shared.compile_plugin(framework,p.GAME/'kibu7_Data/Managed',dest/'KibukawaHistory.dll',sources,dest/'compile.rsp',
        ['mscorlib.dll','netstandard.dll','System.dll','System.Core.dll','UnityEngine.dll','UnityEngine.CoreModule.dll','UnityEngine.UI.dll','UnityEngine.UIModule.dll','UnityEngine.TextRenderingModule.dll','UnityEngine.IMGUIModule.dll','UnityEngine.InputLegacyModule.dll'])
    test=dest/'HistoryTests.exe'
    subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/out:'+str(test),str(root/'src/HistoryBuffer.cs'),str(root/'src/ColoredHistoryLayout.cs'),str(root/'tests/HistoryTests.cs')],check=True)
    subprocess.run([str(test)],check=True)
    subprocess.run(['pwsh', '-NoProfile', '-File', str(root/'tests/validate.ps1'), '-Game', 'kibu7', '-Unrestricted', '-PluginPath', str(dest/'KibukawaHistory.dll')], check=True)
    report=dict(version='1.6.2',sha256={'kibu7':p.sha((dest/'KibukawaHistory.dll').read_bytes())},source_hashes={x.relative_to(p.SERIES).as_posix():p.sha(x.read_bytes()) for x in sources+[root/'tests/HistoryTests.cs',root/'tests/validate.ps1',root/'README.md']},validation='unrestricted process metadata, kibu7 original hook metadata, compile and shared history buffer/layout tests; live interaction pending')
    p.save(dest/'manifest.json',report)
    with zipfile.ZipFile(dest/('kibu7-history-'+report['version']+'.zip'), 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.write(dest/'KibukawaHistory.dll', 'BepInEx/plugins/KibukawaHistory/KibukawaHistory.dll')
        archive.write(root/'README.md', '历史记录说明.md')
        archive.write(p.SERIES/'LICENSE', 'LICENSE')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--export-only', action='store_true')
    parser.add_argument('--refresh-dependency', action='store_true')
    args = parser.parse_args()
    if args.probe:
        subprocess.run([sys.executable, str(p.WORK/'scripts/build_probe.py'), '--probe'], check=True)
        return
    # Hash immutable original files only; a running game owns and locks BepInEx caches/logs.
    original_paths = p.load(p.WORK/'work/manifest.json')['game_hashes']
    original_hashes = lambda: {name: p.sha((p.GAME/name).read_bytes()) for name in original_paths}
    before = original_hashes()
    p.require(before == original_paths, 'Original game files changed')
    first_before = p.first_project_hashes()
    cache_hash = p.sha((p.WORK/'work/cache.json').read_bytes())
    config = p.load(p.WORK/'project.json')
    target = config['bepinex']
    output = p.inside(p.WORK/'bepinex/build/plugin')
    output.mkdir(parents=True, exist_ok=True)
    pack, manifest = export_pack(output)
    if args.export_only:
        print('Exported '+str(len(pack['scripts']))+' script slots and actual-byte replay.')
        return
    font_test=p.WORK/'bepinex/build/UiFontLifecycleTests.exe'
    subprocess.run(['C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe','/nologo','/out:'+str(font_test),str(p.WORK/'bepinex/src/UiFontPolicy.cs'),str(p.WORK/'bepinex/tests/UiFontLifecycleTests.cs')],check=True)
    subprocess.run([str(font_test)],check=True)
    from build_pixel_font import build_font
    from build_help_pages import build_help_pages
    profile = p.load(p.SERIES/'engine/bepinex/profiles'/(target['profile']+'.json'))
    p.require(profile['backend'] == 'mono' and profile['architecture'] == 'x64', 'Unsupported backend/profile')
    executable = (p.GAME/'kibu7.exe').read_bytes()
    offset = struct.unpack_from('<I', executable, 0x3c)[0]
    p.require(executable[offset:offset+4] == b'PE\0\0' and struct.unpack_from('<H', executable, offset+4)[0] == 0x8664, 'Expected AMD64 executable')
    framework, dependency = shared.ensure_framework(p.SERIES/'engine/bepinex/locks'/profile['lock'], p.SERIES/'cache/bepinex'/target['profile'], args.refresh_dependency)
    font_report = build_font(pack, output)
    help_report = build_help_pages()
    subprocess.run([sys.executable, str(p.SERIES/'tools/build_image_replacements.py'), '--game', 'kibu7'], check=True)
    image_root = p.SERIES/'out/image-replacements-1.1.0'
    image_report = next(r for r in p.load(image_root/'build-report.json') if r['game'] == 'kibu7')
    sources = sorted((p.SERIES/'engine/core').glob('*.cs')) + sorted((p.SERIES/'engine/adapters/gmode-v1/src').glob('*.cs'))
    sources += sorted(path for path in (p.WORK/'bepinex/src').glob('*.cs') if path.name != 'BootstrapPlugin.cs')
    p.require(len({path.name for path in sources}) == len(sources), 'Duplicate C# source names')
    audit_sources = sources + sorted((p.WORK/'scripts').glob('*.py')) + [p.WORK/'scripts/validate_runtime.ps1', p.WORK/'bepinex/display-labels.json', p.WORK/'bepinex/menu-labels.json', p.WORK/'bepinex/font-dependency.lock.json'] + sorted((p.WORK/'bepinex/tests').glob('*.cs'))
    audit_sources += [p.SERIES/'tools/click_boundaries.py', p.WORK/'work/click_boundaries.reviewed.json']
    audit_sources += [p.SERIES/'tools/dialogue_tags.py', p.WORK/'work/dialogue-tagged.json', p.WORK/'research/color-spans.reviewed.json', p.WORK/'research/color-commands.json', p.WORK/'research/hard-breaks.json', p.WORK/'dialogue-hard-breaks.json', p.WORK/'images/help-pages.translation.json']
    audit_sources += [p.SERIES/'series.json', p.WORK/'scripts/install_bepinex.ps1']
    audit_sources += [p.WORK/'project.json', p.WORK/'bepinex/README_INSTALL.txt']
    history=build_history(framework)
    audit_sources += [p.SERIES/name for name in history['source_hashes']]
    source_hashes = {path.relative_to(p.SERIES).as_posix(): p.sha(path.read_bytes()) for path in audit_sources}
    source_hashes.update(image_report['source_hashes'])
    shared.compile_plugin(framework, p.GAME/target['managed'], output/target['assembly'], sources, p.WORK/'bepinex/build/compile.rsp', target['references'])
    subprocess.run([sys.executable, str(p.WORK/'scripts/check_runtime.py')], check=True)
    subprocess.run([sys.executable, str(p.WORK/'scripts/validate_pixel_font.py'), '--existing', '--out', str(output)], check=True)
    validation = p.load(p.WORK/'bepinex/build/runtime-validation.json')
    p.require(p.sha((p.WORK/'work/cache.json').read_bytes()) == cache_hash, 'Translation changed during build')
    p.require(all(p.sha((p.SERIES/name).read_bytes()) == digest for name, digest in source_hashes.items()), 'Runtime sources changed during compilation')
    release = p.inside(p.WORK/'out'/('bepinex_zh-CN_'+time.strftime('%Y%m%d_%H%M%S')+'_'+str(time.time_ns()%1000000000)))
    package = release/'package'
    prefix = 'BepInEx/plugins/'+target['plugin_directory']+'/'
    payload = {prefix+name: output/name for name in (target['assembly'], 'translations.json', 'translations.bin')}
    for subdir in ('fonts', 'licenses', 'images'):
        for path in (output/subdir).rglob('*'):
            if path.is_file():
                payload[prefix+path.relative_to(output).as_posix()] = path
    payload['README_Kibu7_汉化安装.txt'] = p.WORK/'bepinex/README_INSTALL.txt'
    payload['BepInEx/licenses/BepInEx-LICENSE.txt'] = p.SERIES/'engine/bepinex/licenses/BepInEx-LICENSE.txt'
    for name, digest in image_report['package_files'].items():
        path = image_root/'kibu7/package'/name
        p.require(name not in payload and p.sha(path.read_bytes()) == digest, 'Image payload conflict/checksum mismatch')
        payload[name] = path
    history_dll=p.WORK/'bepinex/build/history/KibukawaHistory.dll'
    p.require(p.sha(history_dll.read_bytes())==history['sha256']['kibu7'],'History payload checksum mismatch')
    payload['BepInEx/plugins/KibukawaHistory/KibukawaHistory.dll']=history_dll
    payload['历史记录说明.md']=p.SERIES/'engine/history/README.md'
    payload['BepInEx/licenses/KibukawaHistory-LICENSE.txt']=p.SERIES/'LICENSE'
    p.require(set(p.load(p.SERIES/'series.json')['required_plugins'].values())<=set(payload),'Missing mandatory plugin')
    shared.stage_package(package, framework, dependency, payload, set(manifest['game_hashes']))
    archive = release/'Kibu7_ZhCN_BepInEx_Full.zip'
    shared.archive_package(package, archive)
    p.require(original_hashes() == before, 'Original game changed during build')
    p.require(p.first_project_hashes() == first_before, 'Previous-game projects changed during build')
    report = dict(plugin_version=config['plugin_version'], edition='BepInEx runtime translation', history_version=history['version'],
                  history_artifacts=(p.WORK/'bepinex/build/history').relative_to(p.SERIES).as_posix(),
                  output=str(release), zip=str(archive), zip_sha256=p.sha(archive.read_bytes()),
                  dependency=dependency, script_slots=len(pack['scripts']), ui_strings=len(pack['ui']),
                  localization_keys=len(pack['localization']), assembly_literals=len(pack['literals']),
                  translation_sha256=cache_hash, source_hashes=source_hashes,
                  shared_builder_sha256=p.sha((p.SERIES/'engine/bepinex/build.py').read_bytes()),
                  pixel_dialogue_font=font_report, help_pages=help_report, native_images=image_report, validation=validation,
                  original_game_unchanged=True, previous_projects_unchanged=True, game_runtime_tested=False,
                  original_assets_in_package=False, install_ready=True, release_ready=config['compatibility'].get('release_ready', False),
                  user_accepted=config['compatibility'].get('user_accepted', False),
                  user_accepted_date=config['compatibility'].get('user_accepted_date'),
                  package_files={path.relative_to(package).as_posix(): p.sha(path.read_bytes()) for path in package.rglob('*') if path.is_file()})
    p.save(release/'build_report.json', report)
    p.save(p.WORK/'reports/bepinex_latest.json', report)
    print(('RELEASE READY: ' if report['release_ready'] else 'READY FOR USER TESTING: ')+str(archive))


if __name__ == '__main__':
    main()
