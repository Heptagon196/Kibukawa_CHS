"""Download pinned Unifont and Z Labs Pixel sources into the ignored font cache.

Run before building; builds remain offline. No font binaries belong in Git.
"""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1] / 'bepinex'


def fetch():
    import sys
    sys.path.insert(0,str(ROOT.parents[2]/'engine/fonts'))
    from fetch_zlabs import fetch as fetch_ui
    fetch_ui()
    items = []
    for name in ('font-dependency.lock.json', 'fusion-icon-font-dependency.lock.json'):
        lock = json.loads((ROOT / name).read_text('utf-8'))
        items.extend(lock['dependencies'].values())
    for item in items:
        path = ROOT / 'fonts' / item['file']
        if Path(item['file']).name != item['file']:
            raise ValueError('Dependency filename must be a basename')
        if path.is_file():
            data = path.read_bytes()
            if len(data) == item['size'] and hashlib.sha256(data).hexdigest() == item['sha256']:
                print('Verified cached ' + path.name)
                continue
        with urllib.request.urlopen(item['url'], timeout=120) as response:
            data = response.read(item['size'] + 1)
        if len(data) != item['size'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Downloaded font differs from dependency lock: ' + item['file'])
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + '.download')
        temporary.write_bytes(data)
        temporary.replace(path)
        print('Downloaded and verified ' + path.name)


if __name__ == '__main__':
    fetch()
