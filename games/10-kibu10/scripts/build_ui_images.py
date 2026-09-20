"""Deterministic code-native Chinese UI labels; never edits native artwork."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pipeline as p
from title_art_parts import tile

FONT = Path('C:/Windows/Fonts/NotoSansSC-VF.ttf')
FONT_SHA = '763146584cf0710223441356b4395e279021b0806c196614377a7a0174ae074a'
LABELS = {'name00': '工藤贵树', 'name01': '石上雅人', 'name02': '妹浦澄佳', 'name03': '白鹭洲伊纲', 'sell_end1': '已通关'}
MENUS = {'t_start': ('开始', (16, 67)), 't_help': ('玩法说明', (17, 86)), 't_append': ('附加内容', (17, 51))}

def font(size):
    f=ImageFont.truetype(str(FONT),size); f.set_variation_by_name('Bold'); return f

def build():
    if p.sha(FONT.read_bytes()) != FONT_SHA: raise ValueError('UI font changed')
    out=p.WORK/'images/ui'; out.mkdir(parents=True,exist_ok=True)
    routes=[]; evidence=[]
    for key,text in LABELS.items():
        im=Image.new('RGBA',(48,18),((85,30,12,255) if key=='sell_end1' else (38,18,85,255)));d=ImageDraw.Draw(im)
        f=font(11 if len(text)<=4 else 9)
        box=d.textbbox((0,0),text,font=f)
        d.text(((48-box[2]+box[0])//2-box[0],(18-box[3]+box[1])//2-box[1]),text,font=f,fill='white')
        file=out/(key+'.png');im.save(file)
        routes.append(dict(id=key,png='ui/'+file.name,size=[48,18],sources=[dict(loader='LoadGraphic',name=key+'.gif'),dict(loader='Image_createImage',name='/'+key+'.gif')]))
        evidence.append(dict(id=key,text=text,size=[48,18],sha256=p.sha(file.read_bytes())))
    for key,(text,size) in MENUS.items():
        for level in (1024,900,700,500,400,0):
            color=(160,0,0,255) if level==0 else (level*255//1024,)*3+(255,)
            im=tile(key,size,color)
            suffix='' if level==1024 else '-'+str(level)
            file=out/(key+suffix+'.png');im.save(file)
            evidence.append(dict(id=key+suffix,text=text,size=list(size),brightness=level,sha256=p.sha(file.read_bytes())))
            if level==1024: routes.append(dict(id=key,png='ui/'+file.name,size=list(size),sources=[dict(loader='LoadGraphic',name=key+'.gif'),dict(loader='Image_createImage',name='/'+key+'.gif')]))
    p.save(p.WORK/'images/ui-labels.reviewed.json',dict(schema=1,game='kibu10',source='Name plates typeset locally; all title-menu lettering uses one shared artistic master title2-zh.png',font_sha256=FONT_SHA,entries=evidence))
    return routes

if __name__=='__main__': build()
