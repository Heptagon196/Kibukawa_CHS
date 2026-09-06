"""Compose Chinese map labels offline for the game's non-readable GIF textures."""
import io
import os
from pathlib import Path
import struct
import subprocess
import zipfile
from PIL import Image
import pipeline as p


def build_floorplan(output):
    spec_path = p.WORK/'bepinex/src-data/floorplan-labels.json'
    spec = p.load(spec_path)
    resource = p.text_assets(p.GAME/p.STREAM/'scratchpad')['kairou.res']
    with zipfile.ZipFile(io.BytesIO(resource)) as archive:
        member = archive.read('gif1')
    offset = 1
    frames = []
    for _ in range(member[0]):
        length = int.from_bytes(member[offset:offset+2], 'big')
        offset += 2
        frames.append(member[offset:offset+length])
        offset += length
    source = frames[10]
    p.require(p.sha(source) == spec['source_gif_sha256'], 'Floor-plan source GIF mismatch')
    original = Image.open(io.BytesIO(source)).convert('RGBA')
    p.require(original.size == (220, 128), 'Floor-plan dimensions changed')
    research = p.inside(p.WORK/'research/map')
    research.mkdir(parents=True, exist_ok=True)
    source_png = research/'gif1_10.png'
    original.save(source_png)  # Unedited decode, solely for offline UI review.
    compiler = Path(os.environ.get('WINDIR', 'C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    renderer = p.WORK/'bepinex/tests/RenderFloorPlanLabels.cs'
    exe = p.WORK/'bepinex/build/RenderFloorPlanLabels.exe'
    subprocess.run([str(compiler), '/nologo', '/r:System.Drawing.dll', '/r:System.Web.Extensions.dll', '/out:'+str(exe), str(renderer)], check=True)
    subprocess.run([str(exe), str(spec_path), str(source_png), str(output/'floorplan'), str(research/'preview')], check=True)
    data = (output/'floorplan.bin').read_bytes()
    p.require(data[:12] == b'KMAP'+struct.pack('<ii',220,128) and len(data)==112652, 'Invalid floor-plan payload')
    preview = Image.open(research/'preview.png').convert('RGBA')
    mask = Image.open(output/'floorplan.png').convert('RGBA')
    changed = 0
    for y in range(128):
        for x in range(220):
            i = 12+(y*220+x)*4
            inside = any(a['x']<=x<a['x']+a['width'] and a['y']<=y<a['y']+a['height'] for a in spec['labels'])
            if not inside:
                p.require(mask.getpixel((x,y))[3] == 0 and preview.getpixel((x,y)) == original.getpixel((x,y)), 'Map geometry changed outside label regions')
            p.require(tuple(data[i:i+4]) == preview.getpixel((x,y)), 'Runtime map differs from reviewed preview')
            pixel = original.getpixel((x,y))
            if pixel[:3] == (255,0,0) or (pixel[:3] == (255,255,0) and not (43<=x<63 and 26<=y<36)):
                p.require(preview.getpixel((x,y)) == pixel, 'Door marker or room number changed')
            if (21<=x<96 and 66<=y<124) or (155<=x<218 and 76<=y<123):
                if pixel[:3] in ((255,255,255),(230,230,230)):
                    p.require(inside, 'Uncovered source-label pixel')
            changed += preview.getpixel((x,y)) != original.getpixel((x,y))
    report = dict(source='scratchpad:kairou.res/gif1[10]', source_sha256=p.sha(source), dimensions=[220,128],
                  label_count=len(spec['labels']), labels=spec['labels'], changed_pixels=changed,
                  outside_label_pixels_unchanged=True, door_markers_and_room_numbers_unchanged=True,
                  no_old_room_label_pixels=True, translated_map_in_payload=True, original_gif_in_payload=False, runtime_visual_tested=False,
                  specification_sha256=p.sha(spec_path.read_bytes()), renderer_sha256=p.sha(renderer.read_bytes()),
                  overlay_sha256=p.sha(data), preview=str(research/'preview-6x.png'))
    p.save(p.WORK/'bepinex/build/floorplan-report.json', report)
    return report


if __name__ == '__main__':
    build_floorplan(p.WORK/'bepinex/build/plugin')
