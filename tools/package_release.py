"""Verify build artifacts and copy them under the documented release names."""
import argparse
import hashlib
import json
import io
from pathlib import Path
import shutil
import zipfile

from project_config import ROOT, resolve
from click_boundaries import audit_project


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
    parser.add_argument('--with-images', action='store_true', help='Merge verified generic image replacement packs into each full patch')
    parser.add_argument('--with-history', action='store_true', help='Merge the verified history plugin into each full patch')
    args = parser.parse_args()
    output = (ROOT / args.output).resolve()
    require(output.is_relative_to((ROOT / 'out').resolve()), 'Output must be under workspace out/')
    naming = read(ROOT / 'series/release-names.json')
    verified, names = [], set()
    image_reports = {}
    if args.with_images:
        image_reports = {x['game']:x for x in read(ROOT/'out/image-replacements-1.1.0/build-report.json')}
    for game in args.game:
        project = resolve(game)['project']
        audit_project(project, strict=True)
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
        content=archive.read_bytes()
        image_metadata={}
        if args.with_images:
            image_report=image_reports[game]
            require(image_report['version']=='1.1.0','Unexpected image plugin version')
            for relative, expected in image_report['source_hashes'].items():
                require(digest(ROOT/relative)==expected,'Stale image replacement source: '+relative)
            require(digest(ROOT/'engine/bepinex/build.py')==image_report['shared_builder_sha256'],'Stale image builder')
            installation=resolve(game)['installation']
            require(digest(installation/config['bepinex']['managed']/'Assembly-CSharp.dll')==image_report['assembly_sha256'],'Image/game assembly mismatch')
            require(digest(installation/(game+'_Data/StreamingAssets/scratchpad'))==image_report['scratchpad_sha256'],'Image/game resource mismatch')
            image_zip=Path(image_report['package'])
            require(digest(image_zip)==image_report['package_sha256'],'Image package checksum mismatch')
            with zipfile.ZipFile(image_zip) as addon, zipfile.ZipFile(archive) as base:
                require(addon.testzip() is None,'Corrupt image ZIP')
                addon_members=[i.filename for i in addon.infolist() if not i.is_dir()]
                require(len(set(addon_members))==len(addon_members) and set(addon_members)==set(image_report['package_files']),'Unexpected image ZIP members')
                require(not set(addon_members).intersection(base.namelist()),'Image add-on overwrites text patch files')
                require(not set(addon_members).intersection(originals),'Image add-on contains original game files')
                merged=io.BytesIO()
                with zipfile.ZipFile(merged,'w',zipfile.ZIP_DEFLATED) as package:
                    for name in members: package.writestr(name,base.read(name))
                    for name in addon_members:
                        require(not name.startswith(('/', '\\')) and '..' not in name.replace('\\','/').split('/'),'Unsafe image ZIP path')
                        data=addon.read(name)
                        require(hashlib.sha256(data).hexdigest()==image_report['package_files'][name],'Image ZIP member mismatch')
                        package.writestr(name,data)
                content=merged.getvalue()
            with zipfile.ZipFile(io.BytesIO(content)) as combined:
                require(combined.testzip() is None,'Corrupt combined ZIP')
                for name, expected in payload.items():
                    require(hashlib.sha256(combined.read(name)).hexdigest()==expected,'Text patch changed while merging')
            image_metadata=dict(image_plugin_version=image_report['version'],image_routes=len(image_report['routes']),
                                base_zip_sha256=digest(archive),image_zip_sha256=image_report['package_sha256'],
                                image_runtime_visual_tested=image_report['runtime_visual_tested'])
        if args.with_history:
            history=read(ROOT/'out/history/manifest.json')
            require(bool(history.get('source_hashes')), 'History build lacks source fingerprints')
            for relative, expected in history['source_hashes'].items():
                require(digest(ROOT/relative)==expected,'Stale history source: '+relative)
            history_zip=ROOT/'out/history'/(game+'-history-'+history['version']+'.zip')
            dll='BepInEx/plugins/KibukawaHistory/KibukawaHistory.dll'
            with zipfile.ZipFile(history_zip) as addon, zipfile.ZipFile(io.BytesIO(content)) as base:
                require(addon.testzip() is None,'Corrupt history ZIP')
                require(len(addon.namelist())==3 and set(addon.namelist())=={dll,'历史记录说明.md','LICENSE'},'Unexpected history ZIP members')
                require(hashlib.sha256(addon.read(dll)).hexdigest()==history['sha256'][game],'History DLL mismatch')
                require(addon.read('LICENSE')==(ROOT/'LICENSE').read_bytes(),'History license mismatch')
                require(addon.read('历史记录说明.md')==(ROOT/'engine/history/README.md').read_bytes(),'History instructions mismatch')
                require(not {dll,'历史记录说明.md'}.intersection(base.namelist()),'History file collision')
                merged=io.BytesIO()
                with zipfile.ZipFile(merged,'w',zipfile.ZIP_DEFLATED) as package:
                    for name in base.namelist():package.writestr(name,base.read(name))
                    package.writestr(dll,addon.read(dll))
                    package.writestr('历史记录说明.md',addon.read('历史记录说明.md'))
                    if 'LICENSE' not in base.namelist():package.writestr('LICENSE',addon.read('LICENSE'))
                    else:require(base.read('LICENSE')==addon.read('LICENSE'),'License collision')
                with zipfile.ZipFile(io.BytesIO(merged.getvalue())) as combined:
                    require(combined.testzip() is None,'Corrupt history merged ZIP')
                    for name in base.namelist():require(combined.read(name)==base.read(name),'Existing payload changed')
                content=merged.getvalue()
            image_metadata.update(history_plugin_version=history['version'],history_zip_sha256=digest(history_zip))
        verified.append((content, dict(game=game, number=entry['number'], title=entry['title'],
                                      version=config['plugin_version'], filename=filename, github_name=entry['github_name'],
                                      size=len(content), sha256=hashlib.sha256(content).hexdigest(),
                                      translation_sha256=provenance['translation_sha256'],**image_metadata)))
    output.mkdir(parents=True, exist_ok=True)
    for content, record in verified:
        destination = output / record['filename']
        require(not destination.exists() or digest(destination) == record['sha256'], 'Different existing release asset')
        destination.write_bytes(content)
        require(digest(destination) == record['sha256'], 'Release copy mismatch')
    records = [record for _, record in verified]
    (output / 'manifest.json').write_text(json.dumps(dict(schema=1, assets=records), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (output / 'SHA256SUMS.txt').write_text(''.join(x['sha256'] + '  ' + x['filename'] + '\n' for x in records), encoding='utf-8')
    (output / 'SHA256SUMS.github.txt').write_text(''.join(x['sha256'] + '  ' + x['github_name'] + '\n' for x in records), encoding='utf-8')
    print(json.dumps(records, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
