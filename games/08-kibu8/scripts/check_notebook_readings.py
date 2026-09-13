"""Verify every profile title and actual two-line bitmap bounds; render a review sheet."""
import json,re,struct
from pathlib import Path
from PIL import Image
from build_notebook_font import build
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'bepinex/build/plugin'
build(out)
runtime=(ROOT/'bepinex/src/NotebookReading.cs').read_text(encoding='utf-8')
readings=dict(re.findall(r'\{"([^"]+)","([^"]+)"\}',runtime))
ROMAN_BASELINE=int(re.search(r'RomanBaseline = (\d+)',runtime).group(1))
NAME_BASELINE=int(re.search(r'NameBaseline = (\d+)',runtime).group(1))
assert 'Line(__0,reading,roman,RomanBaseline,a);' in runtime
assert 'Line(__0,text,names,NameBaseline,b);' in runtime
def atlas(folder):
    raw=(folder/'dialogue-16.bin').read_bytes(); magic,size,w,h,count=struct.unpack_from('<5i',raw)
    assert magic==0x3346424B
    return {g[0]:g[1:] for g in [struct.unpack_from('<8i',raw,20+32*i) for i in range(count)]},Image.open(folder/'dialogue-16.png')
roman=atlas(out/'fonts/roman'); names=atlas(out/'fonts/ui-12')
def bounds(text,font):
    pen=0; boxes=[]
    for c in text:
        x,y,advance,w,h,bx,by=font[0][ord(c)]
        if w and h: boxes.append((pen+bx,pen+bx+w,by,by+h))
        pen+=advance
    return [min(b[0] for b in boxes),max(b[1] for b in boxes),min(b[2] for b in boxes),max(b[3] for b in boxes)]
def draw(im,text,font,baseline,b):
    pen=(359-b[0]-b[1])//2
    for c in text:
        x,y,advance,w,h,bx,by=font[0][ord(c)]
        if w and h:
            glyph=font[1].crop((x,y,x+w,y+h)).convert('RGBA')
            ink=Image.new('RGBA',glyph.size,(40,40,40)); ink.putalpha(glyph.getchannel('A'))
            im.alpha_composite(ink,(pen+bx,baseline-by-h))
        pen+=advance
titles=[]; count=0; positions={}
for u in json.loads((ROOT/'work/dialogue-tagged.json').read_text(encoding='utf-8'))['units']:
    if not u['script'].endswith('/sousamemo') or not 0<u['instruction']<12800:continue
    text=re.sub('<[^>]+>','',u['target'].split('<row/>')[0]).replace('\u3000',' ').strip()
    text=' '.join(text.split()); key=text.replace(' ','')
    assert key in readings,(u['id'],text)
    count+=1
    if text not in titles:titles.append(text)
sheet=Image.new('RGBA',(240*3,88*((len(titles)+2)//3)),(225,225,225))
for i,text in enumerate(titles):
    r=readings[text.replace(' ','')]; a,b=bounds(r,roman),bounds(text,names)
    positions[text]=(ROMAN_BASELINE,NAME_BASELINE)
    height=a[3]-a[2]+1+b[3]-b[2]
    assert height<=24 and a[1]-a[0]<=102 and b[1]-b[0]<=102,(text,height,a,b)
    roman_box=(ROMAN_BASELINE-a[3],ROMAN_BASELINE-a[2])
    name_box=(NAME_BASELINE-b[3],NAME_BASELINE-b[2])
    assert roman_box[0]>=36 and name_box[1]<=60 and name_box[0]-roman_box[1]>=1,(text,roman_box,name_box)
    im=Image.new('RGBA',(240,120),'white');im.alpha_composite(Image.open(ROOT/'images/memo-profile-zh.png').convert('RGBA'),(24,32))
    draw(im,r,roman,ROMAN_BASELINE,a);draw(im,text,names,NAME_BASELINE,b)
    sheet.alpha_composite(im.crop((0,32,240,120)),((i%3)*240,(i//3)*88))
anchor=next(value for text,value in positions.items() if text.replace(' ','')=='羽泽昌泰')
misaligned={text:value for text,value in positions.items() if value!=anchor}
assert not misaligned,(anchor,misaligned)
sheet.resize((sheet.width*2,sheet.height*2),Image.Resampling.NEAREST).save(ROOT/'reports/notebook-readings-preview.png')
print(f'PASS: {count} profile variants, {len(titles)} displayed names; all glyphs covered and both lines fit centered name cell.')
