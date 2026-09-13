"""Compile outlined account labels on native character sprites, preserving bodies."""
import struct
from PIL import Image, ImageFilter

def load_font(folder):
    data=(folder/'dialogue-16.bin').read_bytes()
    magic,size,width,height,count=struct.unpack_from('<5i',data)
    if magic!=0x3346424b:raise ValueError('Nameplates require native-bearing KBF3 font')
    glyphs={}
    atlas=Image.open(folder/'dialogue-16.png').convert('RGBA')
    for i in range(count):
        code,x,y,advance,w,h,bx,by=struct.unpack_from('<8i',data,20+i*32)
        glyphs[chr(code)]=(atlas.crop((x,y,x+w,y+h)).getchannel('A'),advance,bx,by)
    return glyphs

def render_nameplate(source,label,glyphs):
    source=source.convert('RGBA');alpha=source.getchannel('A')
    occupied=[y for y in range(source.height) if alpha.crop((0,y,source.width,y+1)).getbbox()]
    top=occupied[0];bottom=top+1
    while bottom in occupied:bottom+=1
    if bottom-top>16 or not any(y>bottom for y in occupied):raise ValueError('No separate native nameplate found')
    original_box=alpha.crop((0,top,source.width,bottom)).getbbox()
    width=sum(glyphs[c][1] for c in label)
    ink=Image.new('L',(width+4,36));pen=2
    for c in label:
        mask,advance,bx,by=glyphs[c];ink.paste(mask,(pen+bx,20-by-mask.height));pen+=advance
    box=ink.getbbox();ink=ink.crop((box[0]-1,box[1]-1,box[2]+1,box[3]+1))
    outline=ink.filter(ImageFilter.MaxFilter(3));tile=Image.new('RGBA',ink.size,(0,0,0,0))
    tile.paste((0,0,0,255),(0,0,*ink.size),outline);tile.paste((255,255,255,255),(0,0,*ink.size),ink)
    x=round((original_box[0]+original_box[2]-tile.width)/2);y=max(0,bottom-tile.height)
    body_top=next(v for v in occupied if v>bottom)
    if x<0 or y<0 or x+tile.width>source.width or y+tile.height>body_top:raise ValueError('Nameplate exceeds native sprite')
    out=source.copy();out.paste((0,0,0,0),(0,top,source.width,bottom));out.alpha_composite(tile,(x,y))
    if out.crop((0,body_top,source.width,source.height)).tobytes()!=source.crop((0,body_top,source.width,source.height)).tobytes():raise ValueError('Character pixels changed')
    return out,dict(original_name_bounds=[original_box[0],top,original_box[2],bottom],localized_name_bounds=[x,y,x+tile.width,y+tile.height],body_unchanged=True)
