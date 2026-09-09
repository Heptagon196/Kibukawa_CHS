"""Build and validate the kibu4 runtime translation without installing/launching."""
import argparse
import base64
import collections
import io
import json
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
        if entry['excluded']:
            p.require(row['translation_status'] == 7 and row['translated_text'] == '', 'Protected entry changed')
            continue
        pending = row['translation_status'] == 0
        if pending:
            p.require(row['translated_text'] == '', 'Pending row contains an unapproved target')
        else:
            p.require(row['translation_status'] in (1, 2), 'Invalid translation status '+str(entry['text_index']))
        target = row['source_text'] if pending else row['translated_text']
        if not pending:
            p.require(isinstance(target, str) and '\0' not in target and not re.search(r'[ぁ-ゖァ-ヺｦ-ﾟ]', target), 'Invalid target or kana residue')
            if target == '':
                p.require(loc['kind'] == 'script' and loc['opcode'] == 72 and config.get('approved_empty_name_readings', {}).get(str(entry['text_index'])) == row['source_text'], 'Unapproved empty translation')
            if loc['kind'] == 'script':
                p.require(not any(c in target for c in '\r\n\t') and len(target.encode('utf-16-le'))//2 <= 20, 'Invalid script buffer content')
            tokens = lambda text: collections.Counter(re.findall(r'\{\d+(?:[^{}]*)\}|</?[A-Za-z][^>]*>', text))
            p.require(tokens(target) == tokens(row['source_text']), 'Placeholder/tag mismatch')
        if loc['kind'] == 'script' and 105 <= loc['opcode'] < 130:
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
            elif loc['kind'] == 'assembly' and not pending:
                pack['literals'].append(dict(base, token=loc['token'], instruction=loc['instruction'], method=loc['method']))
    for source, targets in ui.items():
        p.require(len(targets) == 1, 'Conflicting UI targets: '+source)
        pack['ui'].append(dict(source=source, target=next(iter(targets))))
    p.save(output/'translations.json', pack)
    write_binary_pack(pack, output/'translations.bin')
    # Reparse actual original bytes. No original script/jump/save is rewritten.
    assets = p.text_assets(p.GAME/(p.STREAM+'file'), ('define', 'subscn'))
    p.require(p.definitions(assets['define']) == definitions, 'Command definitions changed')
    scratch = p.text_assets(p.GAME/(p.STREAM+'scratchpad'))
    scripts = {}
    for archive_name in config['resource_archives']:
        archive = zipfile.ZipFile(io.BytesIO(scratch[archive_name]))
        for name in archive.namelist():
            if re.fullmatch(r'scn\d+', name):
                p.require(name not in scripts, 'Duplicate scenario route')
                scripts[name] = archive.read(name)
    scripts.update({'subscn_'+str(i+1): data for i, data in enumerate(p.sub_parts(assets['subscn']))})
    p.save(p.WORK/'bepinex/build/read-fixtures.json', dict(scripts={k: base64.b64encode(v).decode('ascii') for k,v in scripts.items()}, definitions=[[k]+v for k,v in definitions.items()]))
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
    from dialogue_tags import validate as validate_tags
    validate_tags(p.WORK,replay)
    validate_click_boundaries(replay, p.WORK)
    return pack, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--export-only', action='store_true')
    parser.add_argument('--refresh-dependency', action='store_true')
    args = parser.parse_args()
    if args.probe:
        subprocess.run([sys.executable, str(p.WORK/'scripts/build_probe.py'), '--probe'], check=True)
        return
    before = p.game_hashes()
    first_before = p.first_project_hashes()
    cache_hash = p.sha((p.WORK/'work/cache.json').read_bytes())
    config = p.load(p.WORK/'project.json')
    cache_rows = [x for g in p.load(p.WORK/'work/cache.json')['files'].values() for x in g['items']]
    translation_complete = not any(x['translation_status'] == 0 for x in cache_rows)
    target = config['bepinex']
    output = p.inside(p.WORK/'bepinex/build/plugin')
    output.mkdir(parents=True, exist_ok=True)
    pack, manifest = export_pack(output)
    if args.export_only:
        print('Exported '+str(len(pack['scripts']))+' script slots and actual-byte replay.')
        return
    from build_pixel_font import build_font
    from build_help_pages import build_help_pages
    profile = p.load(p.SERIES/'engine/bepinex/profiles'/(target['profile']+'.json'))
    p.require(profile['backend'] == 'mono' and profile['architecture'] == 'x64', 'Unsupported backend/profile')
    executable = (p.GAME/'kibu4.exe').read_bytes()
    offset = struct.unpack_from('<I', executable, 0x3c)[0]
    p.require(executable[offset:offset+4] == b'PE\0\0' and struct.unpack_from('<H', executable, offset+4)[0] == 0x8664, 'Expected AMD64 executable')
    framework, dependency = shared.ensure_framework(p.SERIES/'engine/bepinex/locks'/profile['lock'], p.SERIES/'cache/bepinex'/target['profile'], args.refresh_dependency)
    font_report = build_font(pack, output)
    help_report = build_help_pages()
    version_source = p.WORK/'bepinex/build/OriginalVersion.cs'
    version_source.write_text('namespace Kibu1ZhCN { public static class OriginalVersion { public const string FileSha256 = '+json.dumps(manifest['source_hashes'][p.STREAM+'file'])+'; } }', encoding='utf-8')
    sources = sorted((p.SERIES/'engine/core').glob('*.cs')) + sorted((p.SERIES/'engine/adapters/gmode-v1/src').glob('*.cs')) + sorted(p.PROJECT['adapter_path'].glob('*.cs'))
    sources += [version_source]
    sources += sorted(path for path in (p.WORK/'bepinex/src').glob('*.cs') if path.name != 'BootstrapPlugin.cs')
    p.require(len({path.name for path in sources}) == len(sources), 'Duplicate C# source names')
    audit_sources = sources + sorted((p.WORK/'scripts').glob('*.py')) + [p.WORK/'scripts/validate_runtime.ps1', p.WORK/'bepinex/menu-labels.json', p.WORK/'bepinex/font-dependency.lock.json'] + sorted((p.WORK/'bepinex/tests').glob('*.cs'))
    audit_sources += [p.SERIES/'tools/dialogue_tags.py',p.WORK/'work/dialogue-tagged.json',p.WORK/'research/color-spans.reviewed.json']
    source_hashes = {path.relative_to(p.SERIES).as_posix(): p.sha(path.read_bytes()) for path in audit_sources}
    shared.compile_plugin(framework, p.GAME/target['managed'], output/target['assembly'], sources, p.WORK/'bepinex/build/compile.rsp', target['references'])
    subprocess.run([sys.executable, str(p.WORK/'scripts/check_runtime.py')], check=True)
    validation = p.load(p.WORK/'bepinex/build/runtime-validation.json')
    p.require(p.sha((p.WORK/'work/cache.json').read_bytes()) == cache_hash, 'Translation changed during build')
    p.require(all(p.sha((p.SERIES/name).read_bytes()) == digest for name, digest in source_hashes.items()), 'Runtime sources changed during compilation')
    release = p.inside(p.WORK/'out'/('bepinex_zh-CN_'+time.strftime('%Y%m%d_%H%M%S')+'_'+str(time.time_ns()%1000000000)))
    package = release/'package'
    prefix = 'BepInEx/plugins/'+target['plugin_directory']+'/'
    payload = {prefix+name: output/name for name in (target['assembly'], 'translations.json', 'translations.bin')}
    for subdir in ('fonts', 'licenses'):
        for path in (output/subdir).rglob('*'):
            if path.is_file():
                payload[prefix+path.relative_to(output).as_posix()] = path
    payload['README_Kibu4_汉化安装.txt'] = p.WORK/'bepinex/README_INSTALL.txt'
    payload['BepInEx/licenses/BepInEx-LICENSE.txt'] = p.SERIES/'engine/bepinex/licenses/BepInEx-LICENSE.txt'
    shared.stage_package(package, framework, dependency, payload, set(manifest['game_hashes']))
    archive = release/'Kibu4_ZhCN_BepInEx_Test.zip'
    shared.archive_package(package, archive)
    p.require(p.game_hashes() == before, 'Game changed during build')
    p.require(p.first_project_hashes() == first_before, 'Previous-game projects changed during build')
    report = dict(plugin_version=config['plugin_version'], edition='BepInEx Chinese translation draft - user testing',
                  output=str(release), zip=str(archive), zip_sha256=p.sha(archive.read_bytes()),
                  dependency=dependency, script_slots=len(pack['scripts']), ui_strings=len(pack['ui']),
                  localization_keys=len(pack['localization']), assembly_literals=len(pack['literals']),
                  translation_sha256=cache_hash, translated_source_records=sum(x['translation_status'] in (1,2) for x in cache_rows), translated_script_slots=sum(e['source'] != e['target'] for e in pack['scripts']), source_hashes=source_hashes,
                  shared_builder_sha256=p.sha((p.SERIES/'engine/bepinex/build.py').read_bytes()),
                  pixel_dialogue_font=font_report, help_pages=help_report, validation=validation,
                  original_game_unchanged=True, previous_projects_unchanged=True, game_runtime_tested=False,
                  original_assets_in_package=False, release_ready=translation_complete, hooks_ready=True, translation_complete=translation_complete,
                  package_files={path.relative_to(package).as_posix(): p.sha(path.read_bytes()) for path in package.rglob('*') if path.is_file()})
    p.save(release/'build_report.json', report)
    p.save(p.WORK/'reports/bepinex_latest.json', report)
    print('READY FOR USER TESTING: '+str(archive))


if __name__ == '__main__':
    main()
