"""Export native packed images and an inspection contact sheet for title localization."""
import hashlib, io, json, zipfile
from pathlib import Path
import UnityPy
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
records = []
for game, config in json.loads((ROOT/'series.json').read_text('utf-8'))['games'].items():
    installation = (ROOT/config['installation']).resolve()
    output = ROOT/config['project']/'images/title-source'
    output.mkdir(parents=True, exist_ok=True)
    env = UnityPy.load(str(installation/f'{game}_Data/StreamingAssets/scratchpad'))
    local = []
    for obj in env.objects:
        if obj.type.name != 'TextAsset': continue
        asset = obj.read()
        raw = asset.m_Script.encode('utf-8', 'surrogateescape')
        if not zipfile.is_zipfile(io.BytesIO(raw)): continue
        archive = zipfile.ZipFile(io.BytesIO(raw))
        for member in archive.namelist():
            if member not in ('gif1', 'gif2'): continue
            packed = archive.read(member)
            pos = 1
            for index in range(packed[0]):
                length = int.from_bytes(packed[pos:pos+2], 'big'); pos += 2
                data = packed[pos:pos+length]; pos += length
                if not length: continue
                try:
                    im = Image.open(io.BytesIO(data)); im.load()
                except Exception: continue
                name = f'{asset.m_Name}-{member}-{index:02d}.png'
                im.save(output/name)
                record = dict(game=game, archive=asset.m_Name, member=member, index=index,
                              size=list(im.size), sha256=hashlib.sha256(data).hexdigest(),
                              source=str((output/name).relative_to(ROOT)))
                records.append(record); local.append(record)
    cols, w, h = 6, 250, 270
    sheet = Image.new('RGB', (cols*w, ((len(local)+cols-1)//cols)*h), '#777777')
    draw = ImageDraw.Draw(sheet)
    for k, r in enumerate(local):
        im = Image.open(ROOT/r['source']).convert('RGBA'); im.thumbnail((240,240))
        x, y = k%cols*w, k//cols*h
        sheet.paste(im, (x,y+25), im)
        draw.text((x+2,y+2), f"{r['archive']} {r['member']} {r['index']}", fill='white')
    sheet.save(output/'contact-sheet.png')
    print(game, len(local), str(output/'contact-sheet.png'))
(ROOT/'series/title-image-inventory.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), 'utf-8')
