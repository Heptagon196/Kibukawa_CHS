"""Native 48x24 command pair renderer; caller supplies art, labels and BDF glyphs."""
import collections
from PIL import Image


def render_command(source, blank, label, glyphs):
    if blank.size != (48,24): raise ValueError('Command background dimensions changed')
    if len(label) != 2: raise ValueError('Command label must contain two 10px characters')
    if source.size!=(48,24):raise ValueError('Command sprite dimensions changed')
    image=Image.new('RGBA',(48,24))
    for state in range(2):
        x0=state*24
        native=source.crop((x0,0,x0+24,24))
        left=x0;top=0
        tile=blank.crop((left,top,left+24,top+24))
        palette=list(set(native.get_flattened_data()))
        for y in range(24):
            for x in range(24):
                if y<14 or x in (0,23):tile.putpixel((x,y),native.getpixel((x,y)))
                else:
                    c=tile.getpixel((x,y))
                    tile.putpixel((x,y),min(palette,key=lambda p:sum((p[k]-c[k])**2 for k in range(4))))
        ink=set()
        for column,ch in enumerate(label):
            advance,w,h,bx,by,rows=glyphs[ord(ch)]
            if advance != 10: raise ValueError("Command labels require native 10px glyphs")
            for dy,bits in enumerate(rows):
                for dx in range(w):
                    if bits & (1<<(w-1-dx)):ink.add((2+column*10+bx+dx,22-by-h+dy))
        outline=collections.Counter(native.crop((0,14,24,24)).get_flattened_data()).most_common(1)[0][0]
        # Only glyph-adjacent pixels receive the native dark outline.
        for x,y in ink:
            for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
                xx,yy=x+dx,y+dy
                if 0<=xx<24 and 0<=yy<24:tile.putpixel((xx,yy),outline)
        for x,y in ink:
            if not (0<=x<24 and 0<=y<24):raise ValueError('Command glyph exceeds image')
            tile.putpixel((x,y),(255,255,255,255) if state==0 else (128,128,128,255))
        image.paste(tile,(x0,0))
    if image.crop((0,0,48,12)).tobytes()!=source.crop((0,0,48,12)).tobytes():raise ValueError('Command pictogram changed')
    return image
