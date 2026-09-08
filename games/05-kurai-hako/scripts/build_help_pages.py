"""Build newly typeset Chinese help pages from independently inspected kibu5 assets.
No source raster is edited. Source identity/order checks are mandatory.
"""
from pathlib import Path
import hashlib,json
import UnityPy
from PIL import Image,ImageDraw,ImageFont
WORK=Path(__file__).resolve().parents[1]
GAME=WORK.parents[3]/'GmodeArchivesPlus_kibu5'
BUNDLE='kibu5_Data/StreamingAssets/prefab/howtoplay'
SHA256='0b215230e8815860445ad11e7f4013915863dfcc05ac20d22be7242318b0904b'
SPRITE_IDS=[5980464366522226753,522648781589912355,7167562439772083365,4522541275093904280]
PAGES=[
 dict(title='操作说明',subtitle='〈侦探·癸生川凌介事件谭 第5卷《暗匣之上》〉',rows=[['START 按钮','选项'],['A 按钮','确认／推进文字'],['L 摇杆／方向键','移动光标'],['L 摇杆向下／方向键下','跳过文字'],['R','切换声音 ON／OFF']],footer='本游戏不支持自动保存。\n退出前，请使用游戏内的存档功能保存进度。'),
 dict(title='操作说明',subtitle='〈侦探·癸生川凌介事件谭 第5卷《暗匣之上》〉',rows=[['ESC','选项'],['Z / SPACE / L SHIFT / L CTRL','确认／推进文字'],['W A S D / ↑ ← ↓ →','移动光标'],['S / ↓','跳过文字'],['E','切换声音 ON／OFF']],footer='本游戏不支持自动保存。\n退出前，请使用游戏内的存档功能保存进度。'),
 dict(title='G-MODE 经典游戏复刻',body='“G-MODE 经典游戏复刻”是一项复刻计划，\n旨在忠实重现昔日功能手机上的游戏，\n让玩家再次体验它们当年的风貌。\n\n※ 从功能手机版移植时，为了让游玩更加舒适，\n我们对部分操作方式和功能进行了调整。\n\n※ 游戏内的操作说明及菜单仍保留原版内容。\n本作的实际操作方式，请参阅本菜单中的“游戏帮助”。'),
 dict(title='注意事项',body='为忠实重现当年的手机版游戏，\n游戏中可能仍会显示部分无法使用的菜单或按钮，\n例如“WEB（网站）”“目录”“背光”等。\n\n帮助等页面中可能保留了有关通信费用的说明，\n但游玩本作不会另行产生通信费用。')]

def build_help_pages():
 bundle=GAME/BUNDLE
 if hashlib.sha256(bundle.read_bytes()).hexdigest()!=SHA256:raise ValueError('Fifth-game help bundle hash mismatch')
 objects={o.path_id:o for o in UnityPy.load(str(bundle)).objects}
 refs=[]
 for obj in objects.values():
  if obj.type.name=='MonoBehaviour':
   tree=obj.read_typetree()
   if 'howToPlayImages' in tree:refs=[x['m_PathID'] for x in tree['howToPlayImages']]
 if refs!=SPRITE_IDS:raise ValueError('Fifth-game help page order mismatch: '+str(refs))
 out=WORK/'bepinex/build/plugin/images';out.mkdir(parents=True,exist_ok=True)
 previews=WORK/'images/zh-CN';previews.mkdir(parents=True,exist_ok=True)
 font_path=Path('C:/Windows/Fonts/msyh.ttc');font_hash=hashlib.sha256(font_path.read_bytes()).hexdigest()
 bounds=[];pages=[]
 for i,page in enumerate(PAGES):
  sprite=objects[SPRITE_IDS[i]].read_typetree();name='howtoplay_keyguide_steam_%02d'%i
  if sprite['m_Name']!=name:raise ValueError('Help sprite name mismatch')
  if [sprite['m_Rect'][k] for k in ('width','height')]!=[930,632]:raise ValueError('Help logical dimensions mismatch')
  im=Image.new('RGBA',(930,632),(32,41,66,255));d=ImageDraw.Draw(im)
  def text(value,x,y,size=27,fill='white',center=False,maxwidth=850):
   font=ImageFont.truetype(str(font_path),size)
   while d.textbbox((0,0),value,font=font)[2]>maxwidth and size>14:size-=1;font=ImageFont.truetype(str(font_path),size)
   box=d.textbbox((0,0),value,font=font)
   if center:x=(930-(box[2]-box[0]))/2
   y0=y-box[1]; actual=d.textbbox((x,y0),value,font=font)
   if actual[0]<0 or actual[1]<0 or actual[2]>930 or actual[3]>632:raise ValueError('Help text clipping: '+value)
   bounds.append(dict(page=i,text=value,bounds=list(actual),size=size))
   d.text((x,y0),value,font=font,fill=fill)
  text(page['title'],0,32,36,center=True)
  if 'rows' in page:
   text(page['subtitle'],0,84,25,center=True)
   for j,(left,right) in enumerate(page['rows']):
    y=132+j*61
    d.rectangle((36,y,449,y+56),fill='#5b6995');d.rectangle((453,y,894,y+56),fill='#b7bbcf')
    text(left,52,y+16,27,maxwidth=380);text(right,471,y+16,27,fill='#101524',maxwidth=407)
   for j,line in enumerate(page['footer'].splitlines()):text(line,0,548+j*31,23,center=True)
  else:
   for j,line in enumerate(page['body'].splitlines()):
    if line:text(line,0,172+j*39,27,center=True)
  target=out/('help-%02d.png'%i);im.save(target);(previews/target.name).write_bytes(target.read_bytes())
  pages.append(dict(name=name,sprite_path_id=SPRITE_IDS[i],png=str(target.relative_to(WORK)),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),translation=page))
 report=dict(page_count=4,translated_pages=4,source_bundle=BUNDLE,source_bundle_sha256=SHA256,pages=pages,static_source_images_reviewed=True,runtime_visual_tested=False,method='Newly typeset deterministic help diagrams; no original raster copied or edited',font_rendering=dict(font='Microsoft YaHei',source_sha256=font_hash,font_file_distributed=False),text_bounds=bounds)
 for name in ['reports/help-pages-report.json','bepinex/build/help-pages-report.json']:
  f=WORK/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return report
if __name__=='__main__':print(json.dumps(build_help_pages(),ensure_ascii=False))

