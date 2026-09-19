"""Package a hash-checked text/layout update for the installed 0.1.22 runtime."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import pipeline as p


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--release', required=True)
    parser.add_argument('--revision', required=True)
    parser.add_argument('--readme', required=True)
    parser.add_argument('--include-dialogue-font', action='store_true')
    args = parser.parse_args()
    release = p.inside(p.WORK / 'out' / args.release)
    build = release / 'build'
    package = release / 'package'
    prefix = Path('BepInEx/plugins/Kibu9ZhCN')
    files = {}
    names = ['translations.bin', 'translations.json', 'dialogue-layout.bin']
    if args.include_dialogue_font:
        names.extend(('fonts/dialogue-16.bin', 'fonts/dialogue-16.png'))
    for name in names:
        source = build / name
        if not source.is_file():
            raise SystemExit('Missing build output: ' + str(source))
        target = package / prefix / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        files[(prefix / name).as_posix()] = sha(target)
    manifest = dict(revision=args.revision, groups=2422, files=files)
    (release / 'data-update.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (release / 'README.txt').write_text(args.readme + '\n', encoding='utf-8-sig')
    archive = release / (args.revision + '.zip')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for relative in files:
            output.write(package / relative, relative)
        output.write(release / 'README.txt', 'README.txt')
    manifest['archive_sha256'] = sha(archive)
    (release / 'data-update.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PACKAGED', len(files), 'files ->', archive)


if __name__ == '__main__':
    main()
