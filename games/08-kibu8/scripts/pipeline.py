"""Read-only eighth-game research extraction; never installs or launches."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
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
from container import scenarios, require


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def inside(path):
    path = Path(path).resolve()
    require(path.is_relative_to(WORK) and path != WORK, 'Output outside eighth-game project')
    return path


def save(path, data):
    path = inside(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def game_hashes():
    manifest = WORK / 'work/manifest.json'
    paths = load(manifest)['game_hashes'] if manifest.exists() else [p.relative_to(GAME).as_posix() for p in GAME.rglob('*') if p.is_file()]
    return {name: sha((GAME/name).read_bytes()) for name in sorted(paths)}


def first_project_hashes():
    return {p.relative_to(SERIES).as_posix(): sha(p.read_bytes())
            for directory in sorted((SERIES/'games').iterdir()) if directory != WORK and directory.is_dir()
            for p in directory.rglob('*') if p.is_file()}


def validate_sources():
    manifest = load(WORK/'work/manifest.json')
    for name, digest in manifest['source_hashes'].items():
        require(sha((GAME/name).read_bytes()) == digest, 'Original changed: ' + name)
    return manifest


def inspect(game, data, output):
    inside(output).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['pwsh', '-NoProfile', '-File', str(WORK/'scripts/inspect_assembly.ps1'),
                    '-InputDll', str(game/data/'Managed/Assembly-CSharp.dll'), '-OutputJson', str(output)], check=True)
    return load(output)


def extract():
    existing = (WORK/'work/manifest.json').exists()
    if existing:
        validate_sources()
    before, prior = game_hashes(), first_project_hashes()
    save(WORK/'reports/previous-projects-extract-baseline.json', prior)
    target = inspect(GAME, 'kibu8_Data', WORK/'research/kibu8-assembly.json')
    baseline_config = resolve('kibu6')
    baseline = inspect(baseline_config['installation'], 'kibu6_Data', WORK/'research/kibu6-assembly.json')
    require(baseline['assembly_sha256'] == load(baseline_config['project']/'work/manifest.json')['source_hashes']['kibu6_Data/Managed/Assembly-CSharp.dll'], 'Unverified baseline')
    assets = {}
    relative = 'kibu8_Data/StreamingAssets/scratchpad'
    for obj in UnityPy.load(str(GAME/relative)).objects:
        if obj.type.name == 'TextAsset':
            asset = obj.read()
            require(asset.m_Name not in assets, 'Duplicate TextAsset')
            assets[asset.m_Name] = asset.m_Script.encode('utf-8', 'surrogateescape')
    containers = {}
    for name in load(WORK/'project.json')['resource_containers']:
        records = scenarios(assets[name])
        inventory = []
        for record in records:
            raw = record.pop('raw')
            script = record.pop('script')
            destination = inside(WORK/'raw'/name/(record['name'][:-4] + '.bin'))
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            inventory.append(dict(record, sha256=sha(raw), script_sha256=sha(script), script_bytes=len(script)))
        containers[name] = inventory
    def normalized_methods(data, prefix):
        return {re.sub(r'(?<=d__)\d+', '#', key.replace(prefix, '')): re.sub(r'(?<=d__)\d+', '#', '\n'.join(value['body']).replace(prefix, ''))
                for key, value in data['methods'].items() if 'CanvasEx' in key}
    old, new = normalized_methods(baseline, 'appli1.'), normalized_methods(target, '')
    common = old.keys() & new.keys()
    comparison = dict(baseline='kibu6', baseline_sha256=baseline['assembly_sha256'], target_sha256=target['assembly_sha256'],
                      unchanged_methods=sorted(k for k in common if old[k] == new[k]),
                      changed_methods=sorted(k for k in common if old[k] != new[k]),
                      missing_methods=sorted(old.keys()-new.keys()), added_methods=sorted(new.keys()-old.keys()),
                      codec_equal=baseline['codec_base64'] == target['codec_base64'], runtime_tested=False,
                      conclusion='Different 20050817 VM; gmode-v1 runtime hooks are not compatible. Shared build layer remains reusable.')
    save(WORK/'research/engine-comparison.json', comparison)
    save(WORK/'research/container-inventory.json', containers)
    save(WORK/'research/assembly-strings.json', target['strings'])
    source_names = ['kibu8_Data/Managed/Assembly-CSharp.dll', relative, 'kibu8_Data/StreamingAssets/file', 'kibu8_Data/StreamingAssets/localization']
    source_hashes = {name: before[name] for name in source_names}
    for name in source_names:
        destination = inside(WORK/'originals'/name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((GAME/name).read_bytes())
    if not existing:
        require(not (WORK/'work/cache.json').exists(), 'Refusing to overwrite an existing cache')
        save(WORK/'work/cache.json', dict(project_id='kibu8-'+source_hashes[relative][:16], project_type='Txt', project_name=PROJECT['title'],
             input_path=os.path.relpath(GAME, SERIES).replace('\\', '/'), files={}, stats_data={},
             extra=dict(translation_stage='engine_research', coverage='Empty initialization only; script string extraction is pending.')))
        save(WORK/'work/manifest.json', dict(version=1, source_hashes=source_hashes, game_hashes=before, entries=[],
             coverage='Container extraction only; no validated text opcode mapping yet.'))
    require(before == game_hashes(), 'Game changed during extraction')
    after = first_project_hashes()
    changes = sorted(name for name in prior.keys() | after.keys() if prior.get(name) != after.get(name))
    save(WORK/'reports/extraction.json', dict(containers=len(containers), scenarios=sum(map(len, containers.values())),
         original_game_unchanged=True, previous_projects_unchanged=not changes, concurrent_previous_project_changes=changes,
         text_extraction_complete=False, runtime_tested=False))
    status()


def status():
    if not (WORK/'work/manifest.json').exists():
        print('kibu8 registered; extraction pending; release disabled.')
        return
    validate_sources()
    result = dict(game='kibu8', **load(WORK/'reports/extraction.json'))
    result['stage'] = load(WORK/'project.json')['compatibility']['stage']
    if (WORK/'reports/translation-audit.json').exists():
        audit = load(WORK/'reports/translation-audit.json')
        result.update(text_extraction_complete=True, translated=audit['translated'], pending=audit['pending'], structure_valid=audit['structure_valid'])
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['extract', 'status'])
    globals()[parser.parse_args().action]()
