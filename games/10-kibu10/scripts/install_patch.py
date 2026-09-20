"""Install the verified tenth-game package without starting the game."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import time
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
SERIES = PROJECT.parents[1]
GAME = (SERIES / '../../GmodeArchivesPlus_kibu10').resolve()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    report = json.loads((PROJECT / 'reports/build_latest.json').read_text('utf-8'))
    manifest = json.loads((PROJECT / 'work/manifest.json').read_text('utf-8'))
    assert report['release_ready'] and not report['smoke']
    assert (GAME / 'kibu10.exe').is_file()
    archive = PROJECT / report['archive']
    assert digest(archive.read_bytes()) == report['archive_sha256'], 'Archive hash mismatch'
    for name, expected in manifest['source_hashes'].items():
        assert digest((GAME / name).read_bytes()) == expected, 'Game version mismatch: ' + name
    before = {p.relative_to(GAME).as_posix(): digest(p.read_bytes())
              for p in GAME.rglob('*') if p.is_file()}
    payload = {}
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        assert len(package.namelist()) == len(set(package.namelist()))
        assert set(package.namelist()) == set(report['package_files'])
        for name, expected in report['package_files'].items():
            relative = PurePosixPath(name)
            assert not relative.is_absolute() and '..' not in relative.parts
            target = (GAME / name).resolve()
            assert target.is_relative_to(GAME) and target != GAME
            assert name not in manifest['game_hashes'], 'Package would overwrite an original: ' + name
            content = package.read(name)
            assert digest(content) == expected, 'Package member hash mismatch: ' + name
            payload[name] = content
    obsolete = {}
    previous_receipt = PROJECT / 'reports/install_latest.json'
    if previous_receipt.exists():
        previous = json.loads(previous_receipt.read_text('utf-8'))
        prior_plan = Path(previous['installation_record']) / 'plan.json'
        if prior_plan.is_file():
            for name, expected in json.loads(prior_plan.read_text('utf-8'))['files'].items():
                target = (GAME / name).resolve()
                assert target.is_relative_to(GAME) and target != GAME
                if name not in payload and name in before:
                    assert before[name] == expected, 'Obsolete installed file was modified: ' + name
                    obsolete[name] = expected
    collisions = sorted(set(payload) & set(before))
    print(json.dumps(dict(destination=str(GAME), files=len(payload), collisions=collisions, obsolete=list(obsolete),
                          archive_sha256=report['archive_sha256'], apply=args.apply)))
    if not args.apply:
        return
    record = PROJECT / 'installations' / time.strftime('%Y%m%d_%H%M%S')
    record.mkdir(parents=True, exist_ok=False)
    for name in collisions + list(obsolete):
        backup = record / 'backup' / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(GAME / name, backup)
        assert digest(backup.read_bytes()) == before[name]
    plan = dict(destination=str(GAME), archive_sha256=report['archive_sha256'],
                files=report['package_files'], overwritten=collisions,
                added=sorted(set(payload)-set(before)), before=before)
    (record / 'plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    for name in obsolete:
        # Checked absolute per-file target; backup above preserves the old bytes.
        (GAME / name).unlink()
    for name, content in payload.items():
        target = GAME / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    for name, expected in report['package_files'].items():
        assert digest((GAME / name).read_bytes()) == expected, 'Installed hash mismatch: ' + name
    for name, expected in before.items():
        if name not in payload and name not in obsolete:
            assert digest((GAME / name).read_bytes()) == expected, 'Existing file changed: ' + name
    receipt = dict(destination=str(GAME), installed_files=len(payload),
                   archive_sha256=report['archive_sha256'], overwritten=collisions, removed_obsolete=list(obsolete),
                   original_and_save_files_unchanged=True, game_started=False,
                   installation_record=str(record))
    (record / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    (PROJECT / 'reports/install_latest.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
