"""Translate display fields only; Japanese labels/character dispatch stay intact."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
UI = dict(line.split('\t', 1) for line in
          (ROOT / 'saina-onsen/work/ui.tsv').read_text('utf8').splitlines() if line)

def translate(value):
    if value in UI:
        return UI[value]
    if 'SOUND:' in value:
        return '声音：开【关】' if '【OFF】' in value else '声音：【开】关'
    parts = re.split(r'([,>＞])', value)
    if len(parts) > 1:
        return ''.join(p if p in ',>＞' else translate(p.strip()) for p in parts)
    if re.search('[一-鿿ぁ-ヿ]', value):
        raise ValueError('Untranslated UI: ' + value)
    return value

def localize(text, filename):
    output = []
    for line in text.splitlines():
        if not line.lstrip().startswith('//'):
            if line.lstrip().startswith('*') and '|' in line:
                label, title = line.split('|',1)
                title = re.sub(r'[「｢]([^」｣]+)[」｣]',lambda m:'「'+translate(m[1])+'」',title)
                if title == 'テストモード':title = '测试模式'
                line = label+'|'+title
            # Never translate control keys, goto targets, character IDs or paths.
            line = re.sub(r'\b(caption|CmdText|place|time|btnCap)="([^"\r\n]*)"',
                          lambda m: m[1]+'="'+translate(m[2])+'"', line)
            if '[LogCmd ' in line:
                line = re.sub(r'\btext="([^"\r\n]*)"', lambda m:'text="'+translate(m[1])+'"', line)
            line = re.sub(r'\bmsg="(午前|午後|４章デバッグモード|５章デバッグモード)"',
                          lambda m:'msg="'+UI[m[1]]+'"', line)
            line = line.replace('NO DATA', '无存档').replace('AutoSave：', '自动存档：')
            for n in range(1, 4):
                line = line.replace(f'Data {n}　：', f'存档 {n}：')
            line = line.replace('[ChgMsgLayer id=1]SAVE', '[ChgMsgLayer id=1]保存')
            line = line.replace('[ChgMsgLayer id=1]LOAD', '[ChgMsgLayer id=1]读取')
            line = line.replace('se_newward.mp3', 'se_newword.mp3')
            if '[Button ' in line and 'group=sv ' in line and 'template=LONG_COMMAND' in line:
                line = line.replace('template=LONG_COMMAND', 'template=LONG_COMMAND font_Size=24')
            line = line.replace('path_Pic="./resorce/Button/back_button.swf"',
                                'path_Pic="" caption="返回" font_Name="Saina Noto" font_Embed=false font_Size=18 font_Color=0xffffff')
        output.append(line)
    text = '\n'.join(output)+'\n'
    if filename == 'def_macro.adv':
        anchor = '[Output id=1 *msg="\'(\' + %char + \')\'"]'
        assert text.count(anchor) == 1
        names = {'伊綱':'伊纲', '音成':'林居', '東浜':'东滨', '宮間':'宫间', '観光客':'游客', '女性客':'女游客'}
        mapping = '[Var displayName=%char]\n' + '\n'.join(
            f'[If exp="%char == \'{jp}\'"][Var displayName="{zh}"][EndIf]' for jp,zh in names.items())
        text = text.replace(anchor, mapping+'\n[Output id=1 *msg="\'(\' + @displayName + \')\'"]')
    return text
