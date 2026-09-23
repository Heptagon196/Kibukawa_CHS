from pathlib import Path
import json,re,shutil
from PIL import Image

ROOT=Path(__file__).resolve().parent
GAME=ROOT/'birthday'

def main():
    rows=json.loads((GAME/'work/dialogue.json').read_text(encoding='utf-8'))
    if any(not r['target'] for r in rows):raise ValueError('Untranslated rows')
    build=GAME/'build';shutil.copytree(GAME/'originals',build,dirs_exist_ok=True)
    byfile={}
    for row in rows:byfile.setdefault(row['file'],[]).append(row)
    for file,items in byfile.items():
        lines=(GAME/'originals'/file).read_text(encoding='utf-8-sig').splitlines()
        for row in items:
            assert lines[row['line']-1].strip()==row['source'],row['id']
            lines[row['line']-1]=row['target']
        text='\n'.join(lines)+'\n'
        text=text.replace('text="はじめる"','text="开始游戏"').replace('text="iPhone用"','text="兼容模式"')
        text=text.replace('（伊綱）','（伊纲）').replace('（尾場）','（尾场）')
        (build/file).write_text(text,encoding='utf-8')
    config=build/'data/system/Config.tjs'
    text=config.read_text(encoding='utf-8-sig')
    text=re.sub(r'(projectID\s*=\s*)([^;\r\n]+)',r'\1kibukawa_birthday_chs',text)
    if text.count(';defaultPitch = -1;') != 1:raise ValueError('Unexpected Tyrano defaultPitch')
    text=text.replace(';defaultPitch = -1;', ';defaultPitch = 1;')
    config.write_text(text,encoding='utf-8')
    Image.open(GAME/'work/title-chs.png').convert('RGB').resize((640,640),Image.Resampling.LANCZOS).save(build/'data/fgimage/title.png')
    lang=build/'tyrano/lang.js'
    text=lang.read_text(encoding='utf8')
    messages={'タイトルに戻ります。よろしいですね？':'确定返回标题吗？',
              'ウィンドウを閉じて終了します。よろしいですね？':'确定关闭游戏吗？',
              'まだ、保存されているデータがありません':'尚无存档',
              'エラーが発生しました。スクリプトを確認して下さい':'脚本发生错误，请检查游戏文件',
              'エラーが発生しました':'发生错误', 'は存在しません':'不存在',
              'は同一シナリオファイル内に重複しています':'在同一剧本文件中重复',
              'タグ':'指令','ラベル':'标签'}
    for jp,zh in messages.items():text=text.replace(jp,zh)
    lang.write_text(text,encoding='utf8')
    shutil.copytree(ROOT/'birthday/work/html',build/'tyrano/html',dirs_exist_ok=True)
    tag_js=build/'tyrano/plugins/kag/kag.tag.js'
    text=tag_js.read_text(encoding='cp932')
    anchor='''  start: function (pm) {
    this.kag.setMessageCurrentSpan();
    var new_font = {};'''
    replacement='''  start: function (pm) {
    this.kag.setMessageCurrentSpan();
    if (pm.class) this.kag.getMessageCurrentSpan().addClass(pm.class);
    var new_font = {};'''
    if text.count(anchor) != 1:raise ValueError('Unexpected Tyrano font tag implementation')
    tag_js.write_text(text.replace(anchor,replacement),encoding='cp932')
    html=(build/'index.html').read_text(encoding='utf-8')
    html=html.replace('<title>Loading TyranoScript</title>','<title>诞生纪念日事件 · 中文版</title>')
    html=re.sub(r'<link href="https://fonts.googleapis.com/[^\"]+" rel="stylesheet">','',html)
    html=html.replace('</head>','<style>.message_inner,.message_inner p,.message_inner span,.glink_button {font-family:"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",sans-serif !important;} .message_inner span.birthday-game-font,.message_inner span.birthday-game-font span {font-family:webfont_1,"Microsoft YaHei","PingFang SC",serif !important;letter-spacing:2px !important;}</style></head>')
    (build/'index.html').write_text(html,encoding='utf-8')
    (build/'verification.json').write_text(json.dumps({'status':'candidate_not_playtested','dialogue_rows':len(rows),'unique_rows':len({r['target'] for r in rows}),'ruby':'Japanese readings removed from Chinese text','missing_glyphs':'system CJK font; needs browser validation'},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Built',build)

if __name__=='__main__':main()
