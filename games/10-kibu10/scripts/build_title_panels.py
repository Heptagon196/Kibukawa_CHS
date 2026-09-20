"""Keep the complete master background beneath every animated menu state."""
from PIL import Image
import pipeline as p
from title_art_parts import MASTER, BOXES

# Covers both the master's lettering and all three original native draw areas.
PANEL_BOX=(27,34,103,125)
KEYS=('t_start','t_help','t_append')
LEVELS=(1024,900,700,500,400)

def menu_mask(key):
    source=Image.open(MASTER).convert('RGB')
    mask=Image.new('L',source.size)
    l,t,r,b=BOXES[key]
    for y in range(t,b):
        for x in range(l,r):
            red,green,blue=source.getpixel((x,y))
            if red>170 and green<80 and blue<80:
                mask.putpixel((x,y),red)
    return mask.resize((240,240),Image.Resampling.LANCZOS).crop(PANEL_BOX)

def build():
    out=p.WORK/'images/ui';out.mkdir(parents=True,exist_ok=True)
    base=Image.open(MASTER).convert('RGBA').resize((240,240),Image.Resampling.LANCZOS).crop(PANEL_BOX)
    files=[]
    for selected,key in enumerate(KEYS):
        mask=menu_mask(key)
        for state,level in enumerate(LEVELS):
            panel=base.copy()
            ink=Image.new('RGBA',base.size,(level*255//1024,)*3+(255,))
            panel.paste(ink,(0,0),mask)
            file=out/f'title-panel-{selected}-{state}.png'
            panel.save(file);files.append(file)
    return files

if __name__=='__main__':build()
