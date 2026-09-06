"""Apply the user-approved spelling, preserving each reviewed click boundary."""
import pipeline as p

def rename(text):
    return text.replace('塔克利马克斯','Taclimax').replace('塔克马克','Taclimax')

def main():
    cache=p.load(p.WORK/'work/cache.json')
    changes=[]
    for x in p.items(cache):
        before=x['translated_text'];after=rename(before)
        # These adjacent same-click source slots split the title itself.
        if x['text_index']==2145: after=after.replace('塔克利','Tacli')
        if x['text_index']==2146: after=after.replace('马克斯','max')
        if before!=after:changes.append(dict(text_index=x['text_index'],before=before,translated_text=after))
    path=p.WORK/'work/taclimax_name_fixes.json';p.save(path,changes);p.apply_batch(path)
    cache=p.load(p.WORK/'work/cache.json')
    p.require(not any(any(s in x['translated_text'] for s in ('塔克','马克斯')) for x in p.items(cache)), 'Old title fragment remains')
    for group,f in cache['files'].items():
        rows=[x for x in f['items'] if x['translation_status'] in (1,2)]
        if rows:(p.WORK/'translated_texts'/group).write_text('\n'.join('[%s] %s'%(x['text_index'],x['translated_text']) for x in rows),encoding='utf-8')
    glossary=p.load(p.WORK/'work/glossary.locked.json')
    for term in glossary['terms']:
        if term['src'] in ('タクリマクス','ﾀｸﾘﾏｸｽ','タクマク'):
            term['dst']='Taclimax'
    def revise(value):
        if isinstance(value,dict):
            for k,v in value.items():
                if isinstance(v,str) and '塔克利马克斯是音译' in v:
                    value[k]='用户指定统一写作Taclimax；简称也写Taclimax。名称由Tactical Climax缩合，保留原有词源解释。此拼写为用户选定汉化写法。'
                elif isinstance(v,(dict,list)):revise(v)
        elif isinstance(value,list):
            for x in value:revise(x)
    revise(glossary);p.save(p.WORK/'work/glossary.locked.json',glossary)
    # Only the explicitly approved title substitution is allowed in the baseline.
    baseline=p.load(p.WORK/'work/click_boundaries.reviewed.json')
    for unit in baseline['units']:unit['target']=rename(unit['target'])
    baseline['version']='1.0.21'
    baseline['title_change']='User requested Taclimax; exact title substitution within existing units.'
    p.save(p.WORK/'work/click_boundaries.reviewed.json',baseline)
    p.save(p.WORK/'reports/taclimax_name_review.json',dict(changes=changes,old_title_remaining=0,
        menu_width_half_cells=8,source_keys_unchanged=True,click_boundaries_preserved=True))
    guide=p.WORK/'work/STYLE_GUIDE.md';text=guide.read_text(encoding='utf-8')
    text=text.replace('塔克利马克斯用已有简称塔克马克；正文仍用全称。','游戏名统一写Taclimax，八个ASCII字母恰好占8半格，菜单无需另取简称。')
    text=text.replace('タクリマクス→塔克利马克斯；タクマク→塔克马克；','タクリマクス／タクマク→Taclimax（用户指定，正文、简称及菜单统一）；')
    guide.write_text(text,encoding='utf-8')
    readme=p.WORK/'README.md';text=readme.read_text(encoding='utf-8')
    text=text.replace('当前插件为 1.0.20。','当前插件为 1.0.21。游戏名按用户指定统一为Taclimax，菜单、简称与标题简介同步更新。')
    readme.write_text(text,encoding='utf-8')
    print('Updated',len(changes),'slots; Taclimax fits the eight-half-cell menu limit.')

if __name__=='__main__':main()
