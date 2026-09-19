"""Read-only ninth-game research extraction; never installs or launches."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import UnityPy

WORK = Path(__file__).resolve().parents[1]
SERIES = WORK.parents[1]
sys.path.insert(0, str(SERIES / 'tools'))
from project_config import resolve
PROJECT = resolve(project=WORK, allow_disabled=True)
GAME = PROJECT['installation']
sys.path.insert(0, str(PROJECT['adapter_path']))
from container import entries, require


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def inside(path):
    path = Path(path).resolve()
    require(path.is_relative_to(WORK) and path != WORK, 'Output outside ninth-game project')
    return path


def save(path, data):
    path = inside(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def source_names():
    names = ['kibu9_Data/Managed/Assembly-CSharp.dll', 'kibu9_Data/StreamingAssets/scratchpad',
             'kibu9_Data/StreamingAssets/file', 'kibu9_Data/StreamingAssets/localization']
    for source in load(WORK / 'project.json')['scenario_sources']:
        names.append('kibu9_Data/StreamingAssets/' + source['bundle'])
    return sorted(set(names))


def game_hashes():
    manifest = WORK / 'work/manifest.json'
    paths = load(manifest)['game_hashes'] if manifest.exists() else [p.relative_to(GAME).as_posix()
                                                                    for p in GAME.rglob('*') if p.is_file()]
    return {name: sha((GAME / name).read_bytes()) for name in sorted(paths)}


def first_project_hashes():
    return {p.relative_to(SERIES).as_posix(): sha(p.read_bytes())
            for directory in sorted((SERIES / 'games').iterdir()) if directory != WORK and directory.is_dir()
            for p in directory.rglob('*') if p.is_file()}


def validate_sources():
    manifest = load(WORK / 'work/manifest.json')
    for name, digest in manifest['source_hashes'].items():
        require(sha((GAME / name).read_bytes()) == digest, 'Original changed: ' + name)
    return manifest


def shell():
    """The PowerShell interpreter to shell out to.

    PowerShell 7 is not always on PATH even when it is installed; ``run.ps1`` falls
    back to the interpreter recorded in ``runtime.json``, and the build scripts have to
    resolve it the same way rather than assuming ``pwsh`` resolves on its own.
    """
    found = shutil.which('pwsh')
    if found:
        return found
    record = SERIES / 'runtime.json'
    if record.is_file():
        candidate = load(record).get('pwsh')
        if candidate and Path(candidate).is_file():
            return candidate
    raise RuntimeError('PowerShell 7 not found: install it or point runtime.json at it')


def inspect(game, data, output):
    inside(output).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([shell(), '-NoProfile', '-File', str(WORK / 'scripts/inspect_assembly.ps1'),
                    '-InputDll', str(game / data / 'Managed/Assembly-CSharp.dll'), '-OutputJson', str(output)], check=True)
    return load(output)


def bundle_text_assets(relative):
    assets = {}
    for obj in UnityPy.load(str(GAME / relative)).objects:
        if obj.type.name == 'TextAsset':
            asset = obj.read()
            require(asset.m_Name not in assets, 'Duplicate TextAsset')
            assets[asset.m_Name] = asset.m_Script.encode('utf-8', 'surrogateescape')
    return assets


def normalized_methods(data, prefix):
    return {re.sub(r'(?<=d__)\d+', '#', key.replace(prefix, '')):
            re.sub(r'(?<=d__)\d+', '#', '\n'.join(value['body']).replace(prefix, ''))
            for key, value in data['methods'].items() if 'CanvasEx' in key}


def text_draft():
    """Write the source-side dialogue draft, the readable dump and the manifest entries.

    The draft is the translator-facing artifact and the runtime's lookup source:
    one entry per display line, nameplate and menu label, keyed on the canonical
    script name plus the script-relative offset of the command that carries the
    text. Existing targets are preserved by that key, so re-running the extraction
    refreshes the sources without discarding translation work.

    ``work/manifest.json`` also gets one ``entries`` record per unit in the shape the
    series tooling reads, so ``tools/select_glossary.py --game kibu9 --script <group>``
    can filter the public and local tables for a single script.
    """
    sys.path.insert(0, str(PROJECT['adapter_path']))
    import runtime_pack
    config = load(WORK / 'project.json')
    assets = {}
    for source in config['scenario_sources']:
        bundle = source['bundle']
        member = source['asset']
        for path in sorted((WORK / 'raw' / bundle).glob('*.bin')):
            assets[path.stem] = (bundle, member if source['kind'] == 'container' else path.name)
    draft_path = WORK / 'work/dialogue-tagged.json'
    previous = {}
    if draft_path.is_file():
        for unit in load(draft_path)['units']:
            # A recoloured line carries its translation split by colour run as well as
            # whole; both have to survive a re-extraction.
            previous[(unit['script'], unit['offset'])] = (unit.get('target') or '',
                                                          unit.get('runs'))
    units = []
    records = []
    readable = {}
    emphasis = []
    for path in sorted((WORK / 'raw').rglob('*.bin')):
        if path.name == 'scn0.bin':
            continue
        name = path.stem
        bundle, asset = assets[name]
        group = '%s/%s.txt' % (bundle, name)
        content = path.read_bytes()
        parsed = runtime_pack.parse_bin(content)
        rows = []
        for entry in runtime_pack.script_lines(content):
            # A line is a run of fragments; the pack keys it on its first fragment's
            # command offset and the runtime stocks the whole line there.
            rows.append((entry['offset'], 'line', entry['text'], entry['limit'],
                         len(entry['fragments']), 3))
        for offset, entry in runtime_pack.single_texts(parsed).items():
            rows.append((offset, entry['kind'], entry['source'], 0, 1,
                         0 if entry['kind'] == 'choice' else 1))
        rows.sort()
        # A line recoloured part-way through is emphasised text. IRO starts an override
        # and F7 restores the base colour after ruby closes; record both boundaries so
        # the translation keeps emphasis on the same words as the Japanese script.
        for offset, runs in sorted(runtime_pack.emphasis_runs(parsed).items()):
            emphasis.append(dict(script=name, offset=offset, runs=runs))
        for offset, kind, source, limit, fragments, argument in rows:
            target, runs = previous.get((name, offset), ('', None))
            units.append(dict(script=name, kind=kind, offset=offset, source=source,
                              fragments=fragments, limit=limit, target=target,
                              **({'runs': runs} if runs else {})))
            records.append(dict(
                text_index=len(records) + 1, source_text=source, tagged_source=source,
                location=dict(kind='script', file='kibu9_Data/StreamingAssets/' + bundle, asset=asset,
                              member=name, instruction=offset, opcode=opcode_of(kind),
                              unit_id='%s/%s:%d:arg%d' % (bundle, name, offset, argument),
                              argument=argument),
                group=group, excluded=False))
        readable[name] = rows
    save(draft_path, dict(schema=1, units=units))
    save(WORK / 'work/emphasis.json', dict(
        schema=1,
        note='Display lines whose effective text colour changes part-way through. '
             'BUNSYOU_IRO starts an override and BUNSYOU_F7 restores the base colour '
             'after ruby closes. Runs carry their effective colour and must stay on '
             'the same semantic content in translation.',
        lines=emphasis))
    manifest = load(WORK / 'work/manifest.json')
    manifest['entries'] = records
    manifest['coverage'] = ('Container, VM and script text extraction; %d units over %d scripts; '
                            'no translated entries yet.' % (len(records), len(readable)))
    save(WORK / 'work/manifest.json', manifest)
    for name, rows in readable.items():
        destination = WORK / 'texts' / (name + '.txt')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(''.join(
            '[%#08x] %-6s%-12s %s\n' % (offset, kind, ('limit %d' % limit) if limit else '', source)
            for offset, kind, source, limit, _, _ in rows), encoding='utf-8')
    return units


def opcode_of(kind):
    return dict(line=255, choice=8, name=17)[kind]


def extract():
    existing = (WORK / 'work/manifest.json').exists()
    if existing:
        validate_sources()
    before, prior = game_hashes(), first_project_hashes()
    save(WORK / 'reports/previous-projects-extract-baseline.json', prior)
    config = load(WORK / 'project.json')
    target = inspect(GAME, 'kibu9_Data', WORK / 'research/kibu9-assembly.json')
    baseline_config = resolve('kibu8', allow_disabled=True)
    baseline = inspect(baseline_config['installation'], 'kibu8_Data', WORK / 'research/kibu8-assembly.json')
    require(baseline['assembly_sha256'] == load(baseline_config['project'] / 'work/manifest.json')
            ['source_hashes']['kibu8_Data/Managed/Assembly-CSharp.dll'], 'Unverified baseline')
    containers = {}
    materials = {}
    for source in config['scenario_sources']:
        relative = 'kibu9_Data/StreamingAssets/' + source['bundle']
        assets = bundle_text_assets(relative)
        require(source['asset'] in assets, 'Missing scenario asset: ' + source['asset'])
        if source['kind'] == 'container':
            members = entries(assets[source['asset']])
        else:
            members = [(source['asset'], assets[source['asset']])]
        inventory = []
        for name, raw in members:
            destination = inside(WORK / 'raw' / source['bundle'] / name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            inventory.append(dict(name=name, bytes=len(raw), sha256=sha(raw)))
        materials[relative + ':' + source['asset']] = inventory
        containers[relative + ':' + source['asset']] = [item for item in inventory if item['name'].endswith('.bin')]
    old, new = normalized_methods(baseline, 'appli1.'), normalized_methods(target, '')
    common = old.keys() & new.keys()
    comparison = dict(baseline='kibu8', baseline_sha256=baseline['assembly_sha256'],
                      target_sha256=target['assembly_sha256'],
                      unchanged_methods=sorted(k for k in common if old[k] == new[k]),
                      changed_methods=sorted(k for k in common if old[k] != new[k]),
                      missing_methods=sorted(old.keys() - new.keys()),
                      added_methods=sorted(new.keys() - old.keys()),
                      codec_equal=baseline['codec_base64'] == target['codec_base64'], runtime_tested=False,
                      conclusion='Different 20050117 VM; gmode-v1 and gmode-20050817 runtime hooks are not '
                                 'compatible. Shared BepInEx build layer remains reusable.')
    save(WORK / 'research/engine-comparison.json', comparison)
    save(WORK / 'research/container-inventory.json', containers)
    save(WORK / 'research/material-inventory.json', materials)
    save(WORK / 'research/assembly-strings.json', target['strings'])
    source_hashes = {name: before[name] for name in source_names()}
    for name in source_hashes:
        destination = inside(WORK / 'originals' / name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((GAME / name).read_bytes())
    if not existing:
        save(WORK / 'work/cache.json', dict(project_id='kibu9-' + source_hashes['kibu9_Data/StreamingAssets/scratchpad'][:16],
             project_type='Txt', project_name=PROJECT['title'],
             input_path=os.path.relpath(GAME, SERIES).replace('\\', '/'), files={}, stats_data={},
             extra={}))
        save(WORK / 'work/manifest.json', dict(version=1, source_hashes=source_hashes, game_hashes=before, entries=[],
             coverage='Container, VM and script text extraction; no translated entries yet.'))
    units = text_draft()
    kinds = {}
    for unit in units:
        kinds[unit['kind']] = kinds.get(unit['kind'], 0) + 1
    translated = sum(1 for unit in units if unit['target'])
    emphasised = len(load(WORK / 'work/emphasis.json')['lines'])
    cache = load(WORK / 'work/cache.json')
    cache['extra'] = dict(translation_stage='source_extracted' if not translated else 'translation_started',
                          coverage='%d display lines, %d nameplates and %d menu labels extracted to '
                                   'work/dialogue-tagged.json; %d translated.' %
                                   (kinds.get('line', 0), kinds.get('name', 0), kinds.get('choice', 0), translated),
                          text=draft_summary(units))
    save(WORK / 'work/cache.json', cache)
    require(before == game_hashes(), 'Game changed during extraction')
    after = first_project_hashes()
    changes = sorted(name for name in prior.keys() | after.keys() if prior.get(name) != after.get(name))
    save(WORK / 'reports/extraction.json', dict(containers=len(containers),
         scenarios=sum(len(value) for value in containers.values()),
         materials=sum(len(value) for value in materials.values()),
         text_units=len(units), text_kinds=kinds, text_translated=translated,
         text_emphasis=emphasised,
         text_extraction_complete=True,
         original_game_unchanged=True, previous_projects_unchanged=not changes,
         concurrent_previous_project_changes=changes, runtime_tested=False))
    status()


def draft_summary(units):
    kinds = {}
    for unit in units:
        kinds[unit['kind']] = kinds.get(unit['kind'], 0) + 1
    return dict(draft='work/dialogue-tagged.json', units=len(units), kinds=kinds,
                translated=sum(1 for unit in units if unit['target']),
                renderings='texts/<script>.txt')


def status():
    if not (WORK / 'work/manifest.json').exists():
        print('kibu9 registered; extraction pending; release disabled.')
        return
    validate_sources()
    result = dict(game='kibu9', **load(WORK / 'reports/extraction.json'))
    result['stage'] = load(WORK / 'project.json')['compatibility']['stage']
    if (WORK / 'reports/translation-audit.json').exists():
        audit = load(WORK / 'reports/translation-audit.json')
        result.update(text_extraction_complete=True, translated=audit['translated'],
                      pending=audit['pending'], structure_valid=audit['structure_valid'])
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['extract', 'status'])
    globals()[parser.parse_args().action]()
