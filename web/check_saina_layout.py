"""Conservative fixed-line checks using the shipped font, not character counts."""
from pathlib import Path
import json,re
from PIL import ImageFont
ROOT=Path(__file__).resolve().parent
GAME=ROOT/'saina-onsen'
font=ImageFont.truetype(str(ROOT/'vendor/noto-sans-sc/NotoSansSC[wght].ttf'),27)
macros={'生王':'生王','癸生川':'癸生川','伊綱':'伊纲','白鷺洲':'白鹭洲',
        '鞠浜':'鞠滨','狭稲':'狭稻','柄名山':'柄名山','神名備':'神名备','東浜':'东滨','澪':'澪'}
issues=[]
for p in sorted((GAME/'build/script').glob('s0*.adv')):
    speaker=''; page=[]; width=570; line=''; start=0
    def finish():
        global page,line
        content=page+([line] if line else [])
        if speaker not in '１２３４５６７８' and len(content)>3:
            issues.append({'file':p.name,'line':start,'type':'height','text':content})
        page=[];line=''
    for n,s in enumerate(p.read_text('utf8').splitlines(),1):
        s=s.strip()
        if not s or s.startswith('//'):continue
        if s.startswith('*'):finish();continue
        m=re.search(r'\[Talker char="([^"]*)"',s)
        if m:
            finish();speaker=m[1];width=515 if speaker else 565
        # Text rows only; commands on their own never contribute printed text.
        if s.startswith('[') and not re.match(r'\[(?:Font|bw|nw|生王|癸生川|伊綱|白鷺洲|鞠浜|狭稲|柄名山|神名備|東浜|澪)[\] ]',s):continue
        if not page and not line:start=n
        for k,v in macros.items():s=s.replace('['+k+']',v)
        for t in re.split(r'(\[[^\]]*\])',s):
            if t in ('[r]','[rr]'):
                page.append(line);line=''
            elif t in ('[pp]','[ppp]','[pp_j]','[p]'):
                finish()
            elif t.startswith('['):continue
            else:
                line+=t
                if font.getlength(line)>width:
                    issues.append({'file':p.name,'line':n,'type':'width','pixels':round(font.getlength(line)),'text':line})
    finish()
(GAME/'reports/layout.json').write_text(json.dumps(issues,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(issues,ensure_ascii=False,indent=2))
raise SystemExit(bool(issues))
