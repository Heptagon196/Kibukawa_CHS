"""Verify build artifacts and copy them under the documented release names."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

from project_config import ROOT, resolve


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    require(output.is_relative_to((ROOT / 'out').resolve()), 'Output must be under workspace out/')
    naming = read(ROOT / 'series/release-names.json')
    verified, names = [], set()
    for game in args.game:
        project = resolve(game)['project']
        config = read(project / 'project.json')
        report = read(project / 'reports/bepinex_latest.json')
        provenance = report.get('reproducibility', report)
        require(report['plugin_version'] == config['plugin_version'], 'Stale plugin version: ' + game)
        require(digest(project / config['translation']) == provenance['translation_sha256'], 'Stale translation: ' + game)
        for relative, expected in provenance['source_hashes'].items():
            require(digest(ROOT / relative) == expected, 'Stale source: ' + relative)
        builder = provenance.get('bepinex_builder_sha256', report.get('shared_builder_sha256'))
        require(digest(ROOT / 'engine/bepinex/build.py') == builder, 'Stale shared builder: ' + game)
        archive = Path(report['zip']).resolve()
        require(archive.is_relative_to(project / 'out'), 'Archive outside project output')
        require(digest(archive) == report['zip_sha256'], 'Archive SHA256 mismatch')
        originals = set(read(project / config['source_fingerprints'])['game_hashes'])
        payload = report['package_files']
        with zipfile.ZipFile(archive) as package:
            require(package.testzip() is None, 'Corrupt ZIP')
            members = [x.filename for x in package.infolist() if not x.is_dir()]
            require(len(set(members)) == len(members) and set(members) == set(payload), 'Unexpected ZIP members')
            require(not set(members).intersection(originals), 'Package contains original game files')
            for name in members:
                require(not name.startswith(('/', '\\')) and '..' not in name.replace('\\', '/').split('/'), 'Unsafe ZIP path')
                require(hashlib.sha256(package.read(name)).hexdigest() == payload[name], 'ZIP member mismatch: ' + name)
        entry = naming['games'][game]
        filename = naming['filename_pattern'].format(**entry)
        require(Path(filename).name == filename and filename not in names, 'Invalid or duplicate release name')
        names.add(filename)
        verified.append((archive, dict(game=game, number=entry['number'], title=entry['title'],
                                      version=config['plugin_version'], filename=filename, github_name=entry['github_name'],
                                      size=archive.stat().st_size, sha256=digest(archive),
                                      translation_sha256=provenance['translation_sha256'])))
    output.mkdir(parents=True, exist_ok=True)
    for archive, record in verified:
        destination = output / record['filename']
        require(not destination.exists() or digest(destination) == record['sha256'], 'Different existing release asset')
        shutil.copyfile(archive, destination)
        require(digest(destination) == record['sha256'], 'Release copy mismatch')
    records = [record for _, record in verified]
    (output / 'manifest.json').write_text(json.dumps(dict(schema=1, assets=records), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'SHA256SUMS.txt').write_text(''.join(x['sha256'] + '  ' + x['filename'] + '\n' for x in records), encoding='utf-8')
    (output / 'SHA256SUMS.github.txt').write_text(''.join(x['sha256'] + '  ' + x['github_name'] + '\n' for x in records), encoding='utf-8')
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
