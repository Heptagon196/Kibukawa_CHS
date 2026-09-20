"""One existing artistic-lettering master; reusable parts for every title/state."""
from functools import lru_cache
from PIL import Image
import pipeline as p
MASTER=p.WORK/'images/artwork/title-master-v2.png'
BOXES={'t_start':(431,191,525,371),'t_help':(291,197,398,538),'t_append':(160,198,261,538),'caption':(1138,39,1217,784),'after':(455,912,556,1143)}
SIZES={'t_start':(14,28),'t_help':(15,52),'t_append':(14,47),'caption':(14,140),'after':(16,38)}
@lru_cache(maxsize=None)
def component(name):
    source=Image.open(MASTER).convert('RGB').crop(BOXES[name]);mask=Image.new('L',source.size)
    for y in range(source.height):
        for x in range(source.width):
            r,g,b=source.getpixel((x,y))
            # The menu ink is vivid red; the master background ornament is dim.
            a=r if name.startswith('t_') and r>170 and g<80 and b<80 else (min(r,g,b) if not name.startswith('t_') else 0)
            mask.putpixel((x,y),a)
    return mask.resize(SIZES[name],Image.Resampling.LANCZOS)
def tile(name,size,color=(255,255,255,255)):
    mask=component(name);out=Image.new('RGBA',size,(0,0,0,255))
    ink=Image.new('RGBA',mask.size,color);out.paste(ink,((size[0]-mask.width)//2,1),mask)
    return out
