"""Download the pinned native 12px font and its license; builds remain offline."""
import hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def fetch():
    lock=json.loads((ROOT/'zlabs-12px.lock.json').read_text(encoding='utf-8'))
    for item in lock['dependencies'].values():
        if Path(item['file']).name!=item['file']:raise ValueError('Unsafe filename')
        p=ROOT/'cache'/item['file']
        data=p.read_bytes() if p.exists() else urllib.request.urlopen(item['url'],timeout=120).read(item['size']+1)
        if len(data)!=item['size'] or hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Font source mismatch')
        p.parent.mkdir(parents=True,exist_ok=True)
        if not p.exists():p.write_bytes(data)
        if item is lock['dependencies']['license'] and data!=(ROOT/'licenses/ZLabs-OFL.txt').read_bytes():raise ValueError('License differs from source')
        print('Verified '+item['file'])
if __name__=='__main__':fetch()
