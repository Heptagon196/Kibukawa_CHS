"""Typeset four Chinese help diagrams from the reviewed seventh-game text.

No source raster is edited; original Unity assets and page order are verified.
"""
from pathlib import Path
import hashlib
import json
import sys
import UnityPy
from PIL import Image, ImageDraw, ImageFont

WORK = Path(__file__).resolve().parents[1]
ROOT = WORK.parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from project_config import resolve


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_help_pages():
    spec_path = WORK / 'images/help-pages.translation.json'
    spec = json.loads(spec_path.read_text('utf-8'))
    manifest = json.loads((WORK / 'work/manifest.json').read_text('utf-8'))
    game = resolve(project=WORK, allow_disabled=True)['installation']
    bundle = game / spec['bundle']
    if sha(bundle) != manifest['game_hashes'][spec['bundle']]:
        raise ValueError('Seventh-game help bundle changed')
    objects = {o.path_id: o for o in UnityPy.load(str(bundle)).objects}
    model = objects[spec['model_path_id']].read_typetree()
    expected = [p['sprite_path_id'] for p in spec['pages']]
    if [p['m_PathID'] for p in model['howToPlayImages']] != expected:
        raise ValueError('Seventh-game help page order changed')
    out = WORK / 'bepinex/build/plugin/images'
    out.mkdir(parents=True, exist_ok=True)
    font_path = Path('C:/Windows/Fonts/msyh.ttc')
    bounds, pages = [], []
    for index, page in enumerate(spec['pages']):
        sprite = objects[page['sprite_path_id']].read_typetree()
        if sprite['m_Name'] != page['sprite_name'] or [sprite['m_Rect'][k] for k in ('width', 'height')] != [930, 632]:
            raise ValueError('Unexpected source sprite')
        texture = objects[page['texture_path_id']].read()
        if [texture.m_Width, texture.m_Height] != [930, 632]:
            raise ValueError('Unexpected source texture dimensions')
        im = Image.new('RGBA', (930, 632), '#202942')
        draw = ImageDraw.Draw(im)
        rendered = []

        def text(value, x, y, size=27, fill='white', center=False, maxwidth=850, line=None):
            font = ImageFont.truetype(str(font_path), size)
            while draw.textbbox((0, 0), value, font=font)[2] > maxwidth and size > 18:
                size -= 1
                font = ImageFont.truetype(str(font_path), size)
            box = draw.textbbox((0, 0), value, font=font)
            if box[2] - box[0] > maxwidth:
                raise ValueError('Text exceeds available width: ' + value)
            if center:
                x = (930 - (box[2] - box[0])) / 2
            y -= box[1]
            box = draw.textbbox((x, y), value, font=font)
            if box[0] < 0 or box[1] < 0 or box[2] > 930 or box[3] > 632:
                raise ValueError('Text clipped: ' + value)
            bounds.append(dict(page=index + 1, text=value, bounds=list(box), size=size, source_line=line))
            draw.text((x, y), value, font=font, fill=fill)
            if line is not None:
                rendered.append(line)

        lines = page['lines']
        if index < 2:
            text(lines[0]['translation'], 0, 31, 36, center=True, line=0)
            text(lines[1]['translation'], 0, 85, 25, center=True, line=1)
            for row in range(5):
                y = 134 + row * 64
                draw.rounded_rectangle((36, y, 449, y + 58), radius=5, fill='#5b6995')
                draw.rounded_rectangle((453, y, 894, y + 58), radius=5, fill='#b7bbcf')
                control_index = 2 + row * 2
                control = lines[control_index]['translation']
                if control == '[保留R肩键图标]':
                    draw.rounded_rectangle((65, y + 8, 133, y + 50), radius=12, outline='white', width=2)
                    text('R', 88, y + 14, 28, line=control_index)
                elif control == 'S↓ / ↓↓':
                    # The lower arrows indicate pressing the two keys; they are not extra keys.
                    text('S     /     ↓', 155, y + 5, 24, line=control_index)
                    text('↓             ↓', 153, y + 31, 19)
                else:
                    text(control, 52, y + 17, 27, maxwidth=380, line=control_index)
                text(lines[control_index + 1]['translation'], 471, y + 17, 27, '#101524', maxwidth=407, line=control_index + 1)
            for j in range(12, len(lines)):
                text(lines[j]['translation'], 0, 548 + (j - 12) * 32, 23, center=True, line=j)
        else:
            text(lines[0]['translation'], 0, 37, 33, center=True, line=0)
            if index == 2:
                positions = [155, 194, 233, 302, 341, 380, 449, 488]
                for line, y in enumerate(positions, 1):
                    text(lines[line]['translation'], 0, y, 27, center=True, line=line)
            else:
                text(lines[1]['translation'], 0, 96, 35, center=True, line=1)
                for line, y in zip(range(2, len(lines)), [203, 246, 289, 382, 425]):
                    text(lines[line]['translation'], 0, y, 27, center=True, line=line)
        if sorted(rendered) != list(range(len(lines))):
            raise ValueError('A reviewed source line was omitted or duplicated')
        path = out / ('help-%02d.png' % index)
        im.save(path)
        pages.append(dict(page=index + 1, sprite_name=page['sprite_name'], sprite_path_id=page['sprite_path_id'],
                          png=str(path.relative_to(WORK)), size=list(im.size), sha256=sha(path), reviewed_lines=len(lines)))
    report = dict(page_count=4, translated_pages=4, reviewed_lines=sum(p['reviewed_lines'] for p in pages),
                  source_bundle=spec['bundle'], source_bundle_sha256=sha(bundle), translation_sha256=sha(spec_path),
                  pages=pages, text_bounds=bounds, runtime_visual_tested=False,
                  method='Newly typeset diagrams; source raster and assets unchanged',
                  font_rendering=dict(font='Microsoft YaHei', source_sha256=sha(font_path), font_file_distributed=False))
    target = WORK / 'bepinex/build/help-pages-report.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    return report


if __name__ == '__main__':
    result = build_help_pages()
    print('PASS: %d Chinese help pages, %d reviewed lines, all text within bounds' % (result['page_count'], result['reviewed_lines']))
