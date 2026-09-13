"""Small monochrome roman letters from Pillow's bundled classic bitmap font."""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from importlib.metadata import distribution
sys.path.insert(0, str(Path(__file__).resolve().parents[3]/'engine/tools'))
from kbf3_atlas import encode_kbf3

def build(output):
    target=Path(output)/'fonts/roman'
    target.mkdir(parents=True,exist_ok=True)
    font=ImageFont.load_default_imagefont()
    records=[]
    for i,cp in enumerate(list(range(32,127))+[0x25a1]):
        glyph=Image.new('L',(6,11)); draw=ImageDraw.Draw(glyph)
        if cp==0x25a1: draw.rectangle((0,2,4,8),outline=255)
        else: draw.text((0,0),chr(cp),font=font,fill=255)
        box=glyph.getbbox() or (0,0,0,0)
        x,y=(i%16)*8,(i//16)*16
        l,t,r,b=box; w,h=r-l,b-t
        alpha=glyph.crop(box).tobytes() if w and h else b''
        records.append((cp,x,y,6,w,h,l,-b,alpha))
    data,rgba=encode_kbf3(12,128,128,records,transparent_white=True)
    sheet=Image.frombytes('RGBA',(128,128),rgba)
    (target/'dialogue-16.bin').write_bytes(data)
    sheet.save(target/'dialogue-16.png')

    license_target=Path(output)/"licenses/Pillow-LICENSE.txt"
    license_target.parent.mkdir(parents=True,exist_ok=True)
    license_target.write_text(distribution("Pillow").read_text("licenses/LICENSE"),encoding="utf-8")
