"""Download public game files only; record hashes; never execute fetched code."""
from pathlib import Path
import base64, concurrent.futures, hashlib, io, json, re, urllib.request, zipfile

ROOT = Path(__file__).resolve().parent
SOURCES = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
EXT = r'(?:ks|adv|ini|tjs|js|css|html?|png|jpe?g|gif|wav|mp3|ogg|swf|woff2?|ttf|otf)'

def fetch(game, paths):
    base = SOURCES[game]['url']
    root = ROOT / game / 'originals'
    seen, errors = set(), {}
    pending = set(paths)
    def get(path):
        target = root / path
        if target.exists():
            return path, target.read_bytes(), None
        try:
            data = urllib.request.urlopen(base + path, timeout=25).read()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return path, data, None
        except Exception as exc:
            return path, b'', str(exc)
    while pending:
        todo = sorted(pending - seen)
        pending.clear()
        if not todo:
            break
        seen.update(todo)
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            for path, data, error in pool.map(get, todo):
                if error:
                    errors[path] = error
                    continue
                if not re.search(r'\.(?:ks|adv|ini|tjs|js|css|html?)$', path):
                    continue
                text = data.decode('utf-8-sig', 'replace')
                if game == 'saina-onsen':
                    refs = re.findall(r'\./([^\s"\]\']+\.' + EXT + ')', text)
                else:
                    refs = re.findall(r'(?:src|href)=["\']\./([^"\']+)["\']', text)
                    if game == 'birthday':
                        # The speech sounds are stored in sf.popose, not in a
                        # literal playse storage attribute.
                        refs += ['data/sound/'+x for x in re.findall(r"sf\.popose\s*=\s*'([^']+\.wav)'",text)]
                    for line in text.splitlines():
                        m = re.search(r'(?:\[|^@)(\w+)\b[^\]]*\bstorage=["\']?([^\s"\]\']+)', line.strip())
                        if not m or m[2].startswith('&'):
                            continue
                        tag, value = m.groups()
                        if value.startswith(('data/', './data/')): prefix = ''; value = value.removeprefix('./')
                        elif value.endswith('.ks'): prefix = 'data/scenario/'
                        elif tag in ('playbgm', 'preloadbgm'): prefix = 'data/bgm/'
                        elif tag in ('playse',): prefix = 'data/sound/'
                        elif tag == 'bg': prefix = 'data/bgimage/'
                        else: prefix = 'data/fgimage/'
                        refs.append(prefix + value)
                    if path.endswith('.css'):
                        for val in re.findall(r'url\(["\']?([^\)"\']+)', text):
                            if not val.startswith(('http', 'data:')):
                                import posixpath
                                refs.append(posixpath.normpath(str(Path(path).parent).replace('\\','/') + '/' + val))
                pending.update(x for x in refs if '..' not in Path(x).parts and ':' not in x and not x.startswith('/') and re.search(r'\.' + EXT + '$',x))
        print(game, 'processed', len(seen), 'pending', len(pending - seen), flush=True)
    files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in root.rglob('*') if p.is_file() and p.name not in ('strings.txt', 'decompressed.bin')}
    report = {'url': base, 'files': files, 'errors': errors}
    (ROOT / game / 'source-manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return report

if __name__ == '__main__':
    fetch('birthday', ['index.html', 'data/scenario/first.ks', 'data/scenario/scene1.ks', 'data/scenario/scene2.ks', 'data/system/Config.tjs'])
    fetch('saina-onsen', ['start.htm', 'LemoNovel.swf', 'LemoNovel.ini', 'EmbedFonts.swf', 'CustomPt.swf', 'script/first.adv', 'script/def_macro.adv'])
    root = ROOT / 'operation-check-2' / 'originals'
    root.mkdir(parents=True, exist_ok=True)
    data = urllib.request.urlopen(SOURCES['operation-check-2']['url'], timeout=25).read()
    (root / 'index.html').write_bytes(data)
    package = base64.b64decode(re.search(rb'base64: "([^"]+)"', data)[1])
    (root / 'adv.pyxapp').write_bytes(package)
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        for item in archive.infolist():
            if '..' in Path(item.filename).parts or Path(item.filename).is_absolute():
                raise ValueError('Unsafe archive path')
        archive.extractall(root / 'extracted')
    fetch('operation-check-2', ['index.html'])
