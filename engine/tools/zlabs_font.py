"""Read verified upstream KBITX pixels without rasterization or resizing."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from kbitfont import KbitFont
ROOT = Path(__file__).resolve().parents[1] / 'fonts'

@lru_cache(maxsize=1)
def load_source():
    lock = json.loads((ROOT/'zlabs-12px.lock.json').read_text(encoding='utf-8'))
    for item in lock['dependencies'].values():
        path = ROOT/'cache'/item['file']
        data = path.read_bytes()
        if len(data)!=item['size'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
            raise ValueError('Font dependency mismatch: '+str(path))
    source = KbitFont.load_kbitx(ROOT/'cache'/lock['dependencies']['glyphs']['file'])
    if (source.props.em_ascent,source.props.em_descent)!=(10,2):
        raise ValueError('Unexpected native font metrics')
    return lock,source

def load_glyphs():
    lock,source=load_source()
    glyphs={}
    for cp,g in source.characters.items():
        rows=[sum((1<<(g.width-1-x)) for x,v in enumerate(row) if v) for row in g.bitmap]
        glyphs[cp]=(g.advance,g.width,g.height,g.x,g.y-g.height,rows)
    return glyphs

def native_alpha(cp,x,y):
    g=load_source()[1].characters[cp]
    return g.bitmap[y][x] if 0<=x<g.width and 0<=y<g.height else 0
