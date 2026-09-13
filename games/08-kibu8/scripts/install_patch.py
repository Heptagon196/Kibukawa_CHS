"""Install/restore only the manifest-listed eighth-game patch files, with backups."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

WORK = Path(__file__).resolve().parents[1]
SERIES = WORK.parents[1]
GAME = (SERIES/'../../GmodeArchivesPlus_kibu8').resolve()


def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def require(value, message):
    if not value: raise ValueError(message)
def inside(root, relative):
    target = (root/relative).resolve()
    require(target.is_relative_to(root.resolve()) and target != root.resolve(), 'Path outside target: '+str(target))
    return target
def game_closed():
    result = subprocess.run(['powershell','-NoProfile','-Command', "if ([System.Diagnostics.Process]::GetProcessesByName('kibu8').Count -gt 0) { exit 1 }"], check=False)
    require(result.returncode == 0, 'Close kibu8.exe before installing or restoring; installer does not close the game.')
def copy_atomic(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name+'.kibu8-tmp-'+uuid.uuid4().hex)
    try:
        shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        if temporary.exists(): temporary.unlink()
def verify_originals():
    require(GAME.name == 'GmodeArchivesPlus_kibu8' and (GAME/'kibu8.exe').is_file(), 'Wrong game directory')
    manifest = load(WORK/'work/manifest.json')
    for name, expected in manifest['game_hashes'].items():
        require(sha(inside(GAME,name)) == expected, 'Original game file changed: '+name)
    return manifest


def prepare():
    game_closed()
    originals = verify_originals()
    report = load(WORK/'reports/build_latest.json')
    package = inside(WORK,report['output'])/'package'
    actual = {file.relative_to(package).as_posix() for file in package.rglob('*') if file.is_file()}
    require(actual == set(report['package_files']), 'Package file list changed')
    entries = []
    for name, expected in sorted(report['package_files'].items()):
        source, target = inside(package,name), inside(GAME,name)
        require(name not in originals['game_hashes'], 'Refusing to replace original game data: '+name)
        require(sha(source) == expected, 'Package hash mismatch: '+name)
        require(not target.exists() or target.is_file(), 'Target is not a regular file: '+name)
        entries.append(dict(path=name, installed_sha256=expected, previous_sha256=sha(target) if target.exists() else None))
    require(any(e['path']=='BepInEx/plugins/Kibu8ZhCN/Kibu8ZhCN.dll' for e in entries), 'Not a translation package')
    return report, package, entries


def install(dry_run=False):
    report, package, entries = prepare()
    if dry_run:
        print(json.dumps(dict(target=str(GAME), files=len(entries), replaced=sum(e['previous_sha256'] is not None for e in entries),
            new=sum(e['previous_sha256'] is None for e in entries), package=str(package), originals_verified=True), ensure_ascii=False))
        return
    folder = WORK/'installations'/(time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8])
    folder.mkdir(parents=True)
    record = dict(schema=1, game=str(GAME), package=str(package), version=report['version'], status='prepared', entries=entries)
    for e in entries:
        target = inside(GAME,e['path'])
        require((sha(target) if target.exists() else None)==e['previous_sha256'], 'Target changed since preflight')
        if e['previous_sha256'] is not None:
            backup = inside(folder/'backup',e['path'])
            backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(target,backup)
            require(sha(backup)==e['previous_sha256'],'Backup verification failed')
    save(folder/'installation.json',record)
    written=[]
    try:
        for e in entries:
            copy_atomic(inside(package,e['path']),inside(GAME,e['path']))
            written.append(e)
            require(sha(inside(GAME,e['path']))==e['installed_sha256'],'Installed file mismatch')
        verify_originals()
    except Exception:
        for e in reversed(written):
            target=inside(GAME,e['path'])
            if e['previous_sha256'] is None: target.unlink()
            else: copy_atomic(inside(folder/'backup',e['path']),target)
        record['status']='rolled_back'
        save(folder/'installation.json',record)
        raise
    record.update(status='installed',original_files_unchanged=True,installed_files_verified=True,runtime_tested=False)
    save(folder/'installation.json',record)
    save(WORK/'reports/installation_latest.json',dict(manifest=str(folder/'installation.json'),**record))
    print('INSTALLED '+str(folder/'installation.json'))


def restore(manifest):
    game_closed()
    manifest=manifest.resolve()
    require(manifest.is_relative_to((WORK/'installations').resolve()),'Restoration manifest outside eighth-game installations')
    record=load(manifest)
    require(Path(record['game']).resolve()==GAME,'Restoration target mismatch')
    require(record['status']=='installed','Installation is not active')
    for e in record['entries']:
        target=inside(GAME,e['path'])
        require(target.exists() and sha(target)==e['installed_sha256'],'Installed file changed; manual review required: '+e['path'])
        if e['previous_sha256'] is not None:
            require(sha(inside(manifest.parent/'backup',e['path']))==e['previous_sha256'],'Backup hash mismatch')
    for e in reversed(record['entries']):
        target=inside(GAME,e['path'])
        if e['previous_sha256'] is None: target.unlink()
        else: copy_atomic(inside(manifest.parent/'backup',e['path']),target)
    record['status']='restored'
    save(manifest,record)
    verify_originals()
    print('RESTORED '+str(GAME))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run',action='store_true')
    group.add_argument('--install',action='store_true')
    group.add_argument('--restore',type=Path)
    args=parser.parse_args()
    if args.restore: restore(args.restore)
    else: install(dry_run=args.dry_run)
