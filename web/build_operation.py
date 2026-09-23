"""Build a local Pyxel Chinese candidate; original game assets remain ignored."""
from pathlib import Path
import base64, gzip, hashlib, io, json, re, unicodedata, zipfile
from PIL import Image

ROOT = Path(__file__).resolve().parent
GAME = ROOT / 'operation-check-2'

def width(text):
    return sum(16 if unicodedata.east_asian_width(c) in ('F','W','A') else 8 for c in text)

def make_bdf(chars):
    font = ROOT.parent / 'games/10-kibu10/bepinex/fonts/unifont-16.0.04.hex.gz'
    glyphs = {}
    with gzip.open(font, 'rt', encoding='ascii') as f:
        for line in f:
            cp, bits = line.strip().split(':')
            if chr(int(cp,16)) in chars:
                glyphs[int(cp,16)] = bits
    missing = sorted(ord(c) for c in chars if ord(c) not in glyphs and c not in '\r\n\t')
    if missing: raise ValueError(f'Missing glyphs: {missing}')
    out = ['STARTFONT 2.1','FONT -gnu-unifont-medium-r-normal--16-160-75-75-c-80-iso10646-1',
           'SIZE 16 75 75','FONTBOUNDINGBOX 16 16 0 -2','STARTPROPERTIES 2','FONT_ASCENT 14','FONT_DESCENT 2','ENDPROPERTIES',f'CHARS {len(glyphs)}']
    for cp,bits in sorted(glyphs.items()):
        w = len(bits)//4
        out += [f'STARTCHAR U{cp:04X}',f'ENCODING {cp}',f'SWIDTH {w*1000//16} 0',f'DWIDTH {w} 0',f'BBX {w} 16 0 -2','BITMAP']
        out += [bits[i:i+w//4] for i in range(0,len(bits),w//4)] + ['ENDCHAR']
    return ('\n'.join(out+['ENDFONT'])+'\n').encode()

def main():
    dialogue = json.loads((GAME/'work/dialogue.json').read_text(encoding='utf-8'))
    ui = json.loads((GAME/'work/ui.json').read_text(encoding='utf-8'))
    if any(not x['target'] for x in dialogue): raise ValueError('Untranslated dialogue')
    translations = {x['source']:x['target'] for x in dialogue}
    def translate_script(text):
        output=[]
        for line in text.splitlines():
            clean=line.strip()
            if clean in translations:
                line=translations[clean]
            elif clean.startswith('@') and re.search('[ぁ-ヿ]',clean):
                raise ValueError('Untranslated script row: '+clean)
            if clean.startswith('[setSelect '):
                m=re.search(r'txt=(.*?)(?= \w+=)',line)
                line=line[:m.start(1)]+ui[m[1]]+line[m.end(1):]
            for a,b in {'違約金':'违约金','運転':'驾驶','睡眠':'睡眠','動作':'运行','模倣':'模仿','確認':'测试','逆転':'逆转','妨害':'妨碍'}.items():
                line=re.sub(r'(\[setVar \$w[12]=)'+a+r'\]',lambda m:m[1]+b+']',line)
            line=line.replace('name="（尾場）"','name="（尾场）"').replace('name="（伊綱）"','name="（伊纲）"')
            output.append(line)
        return '\n'.join(output)+'\n'
    with zipfile.ZipFile(GAME/'originals/adv.pyxapp') as archive:
        files={x:archive.read(x) for x in archive.namelist()}
    title=io.BytesIO()
    Image.open(GAME/'work/title-chs.png').convert('RGB').resize((340,130),Image.Resampling.LANCZOS).save(title,format='PNG')
    files['adv/title.png']=title.getvalue()
    for filename in ('adv/script.txt',):
        files[filename]=translate_script(files[filename].decode('utf-8-sig')).encode('utf-8')
    code=files['adv/adv.py'].decode('utf-8')
    code=code.replace('FONT_MAIN = "KH-Dot-Kodenmachou-16.bdf"','FONT_MAIN = "chs.bdf"')
    code=code.replace('APPLICATION_NAME = "kibukawa_dosa"','APPLICATION_NAME = "kibukawa_dosa_chs"')
    code=code.replace('is_vscode = os.environ.get("TERM_PROGRAM") == "vscode"','is_vscode = False  # Use the verified Chinese script.')
    code=code.replace('癸生川凌介事件譚 動作確認事件Ⅱ','癸生川凌介事件谭 运行测试事件Ⅱ')
    files['adv/adv.py']=code.encode('utf-8')
    compile(code,'adv.py','exec')
    chars=set(''.join(x['target'] for x in dialogue)+''.join(ui.values())+'（生王）（癸生川）（伊纲）（尾场）运行测试')
    files['adv/chs.bdf']=make_bdf(chars)
    warnings=[]
    for row in dialogue:
        for segment in row['target'][1:].split('[r]'):
            plain=re.sub(r'\[[^\]]+\]','',segment)
            if width(plain)>340:warnings.append({'id':row['id'],'text':plain,'width':width(plain)})
    if warnings: raise ValueError(json.dumps(warnings,ensure_ascii=False))
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():archive.writestr(name,data)
    build=GAME/'build';build.mkdir(exist_ok=True)
    (build/'adv-chs.pyxapp').write_bytes(stream.getvalue())
    html=(GAME/'originals/index.html').read_text(encoding='utf-8')
    html=re.sub(r'base64: "[^"]+"','base64: "'+base64.b64encode(stream.getvalue()).decode()+'"',html)
    html='<meta charset="utf-8"><title>运行测试事件Ⅱ · 中文版</title>\n'+html
    (build/'index.html').write_text(html,encoding='utf-8')
    (build/'verification.json').write_text(json.dumps({'status':'candidate_not_playtested','dialogue':len(dialogue),'choices':len(ui),'missing_glyphs':0,'width_overflows':warnings,'archive_sha256':hashlib.sha256(stream.getvalue()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Built',build,'dialogue',len(dialogue),'choices',len(ui))

if __name__=='__main__':main()
