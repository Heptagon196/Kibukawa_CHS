"""Build a local Ruffle compatibility candidate; never modify downloaded originals.

The author published an unfinished game. This does not supply missing chapters.
Dependencies are pinned by URL and SHA-256 in flash-dependencies.json.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import urllib.request
import zipfile
from patch_saina_flash import patch, patch_progress_bar
from localize_saina_ui import localize, UI
from repair_saina_draft import repair
from build_saina_title import build as build_title

ROOT = Path(__file__).resolve().parent
GAME = ROOT / 'saina-onsen'


def dependencies():
    vendor = ROOT / 'vendor'
    for entry in json.loads((ROOT / 'flash-dependencies.json').read_text('utf8')):
        dest = vendor / entry['path']
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            data = urllib.request.urlopen(entry['url'], timeout=90).read()
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError(f"Dependency hash mismatch: {dest}")
            dest.write_bytes(data)
        if hashlib.sha256(dest.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f"Dependency hash mismatch: {dest}")
        if 'extract' in entry:
            target = vendor / entry['extract']
            with zipfile.ZipFile(dest) as archive:
                for name in archive.namelist():
                    if not (target / name).resolve().is_relative_to(target.resolve()):
                        raise ValueError('Unsafe archive path')
                archive.extractall(target)
    return vendor


def main():
    vendor = dependencies()
    out = GAME / 'build'
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((GAME / 'source-manifest.json').read_text('utf8'))
    for rel, digest in manifest['files'].items():
        source = GAME / 'originals' / rel
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError(f'Original changed: {rel}')
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    rows = json.loads((GAME / 'work/dialogue.json').read_text('utf8'))
    if any(not r['target'] for r in rows):
        raise ValueError('Untranslated dialogue')
    for file in sorted({r['file'] for r in rows}):
        p = out / file
        lines = p.read_text('utf-8-sig').splitlines()
        for row in rows:
            if row['file'] == file and row['target']:
                index = row['line'] - 1
                if lines[index].strip() != row['source'].strip():
                    raise ValueError(f"Text position changed: {row['id']}")
                lines[index] = row['target']
        p.write_text('\n'.join(lines) + '\n', encoding='utf8')
    # Canvas font rendering is provided by Ruffle, with an OFL font loaded locally.
    for p in [out / 'LemoNovel.ini', *sorted((out / 'script').glob('*.adv'))]:
        s = p.read_text('utf-8-sig')
        if p.suffix == '.adv':
            s = localize(s, p.name)
            s = repair(s, p.name)
        s = re.sub(r'(font_Name(?:_Rb)?\s*=\s*)"[^"]*"', r'\1"Saina Noto"', s, flags=re.I)
        s = re.sub(r'(font_Embed(?:_Rb)?\s*=\s*)true', r'\1false', s, flags=re.I)
        if p.name == 'first.adv':
            # The source reads @version three times but accidentally defines SVersion.
            assert s.count('[Var SVersion=126]') == 1
            s = s.replace('[Var SVersion=126]', '[Var version=126]')
            # Obsolete preload names; the actual characters use the existing
            # per-expression SWFs in CharaIN. Do not invent missing portraits.
            s = s.replace('[Cache path="./resorce/Char/kom.swf"]', '')
            s = s.replace('[LoadChar id=1 path="./resorce/Char/izuna.swf"]', '')
        if p.suffix == '.ini':
            s = s.replace('game_Id = "saina-onsen"', 'game_Id = "saina-onsen-local-chs"')
            # Noto's font metrics are taller than YOzFont. Keep 27px glyphs,
            # but compensate leading so all three original body lines fit.
            s = re.sub(r'(layerMsg_InterlinearSpc\s*=\s*)16', r'\g<1>2', s)
        p.write_text(s, encoding='utf8')
    shutil.copyfile(out / 'resorce/Effect/black.jpg', out / 'resorce/BG/black.jpg')
    build_title(GAME / 'originals/resorce/BG/title.swf', GAME / 'work/title-chs.png', out / 'resorce/BG/title.swf')
    patch_progress_bar(GAME / 'originals/resorce/plug-in/ProgressBar.swf',
                       out / 'resorce/plug-in/ProgressBar.swf',
                       GAME / 'work/progressbar-notice.txt', vendor, GAME / 'reports')
    shutil.copytree(vendor / 'ruffle-nightly', out / 'ruffle', dirs_exist_ok=True)
    shutil.copyfile(vendor / 'noto-sans-sc/NotoSansSC[wght].ttf', out / 'NotoSansSC.ttf')
    shutil.copyfile(vendor / 'noto-sans-sc/OFL.txt', out / 'OFL-NotoSansSC.txt')
    shutil.copyfile(ROOT / 'saina-player.html', out / 'index.html')
    patch(GAME / 'originals/LemoNovel.swf', out / 'LemoNovel.swf', vendor, GAME / 'reports')
    report = {'status': 'translated_available_source_not_full_playthrough',
              'translated': sum(bool(r['target']) for r in rows), 'total': len(rows),
              'ui_entries': len(UI),
              'ruffle': 'nightly-2026-09-23', 'original_files_unchanged': True,
              'swf_patch': ['Flush caption auto-size before disabling it in ChgCaptionWidth',
                            'Detach saved and restored SharedObject snapshots from mutable engine state',
                            'Localize the ProgressBar loading notice'],
              'missing_original_chapters': ['s06.adv', 's07.adv']}
    (out / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
