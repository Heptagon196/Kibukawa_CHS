"""Apply reviewed menu-only abbreviations; dialogue keeps the full names."""
import pipeline as p
from check_dialogue_width import half_cells

SHORT_NAMES = {
    '克罗什公司': '克罗什',
    '克罗什株式会社': '克罗什',
    '克罗什之后': '克罗什后',
    '塔克利马克斯': '塔克马克',
    '笔记本电脑': '笔记本',
    '村崎的房间': '村崎房间',
    '遗体的手臂': '遗体手臂',
    '笠见由纪乃的房间': '由纪乃家',
}

def main():
    cache=p.load(p.WORK/'work/cache.json')
    by_id={x['text_index']:x for x in p.items(cache)}
    manifest=p.load(p.WORK/'work/manifest.json')
    changes=[]; checked=0
    for entry in manifest['entries']:
        loc=entry['location']
        if loc['kind']!='script' or not 105<=loc['opcode']<130: continue
        checked+=1
        item=by_id[entry['text_index']]; before=item['translated_text']
        if half_cells(before)<=8: continue
        p.require(before in SHORT_NAMES,f'Unreviewed long menu option: {item["text_index"]} {before}')
        after=SHORT_NAMES[before]
        p.require(half_cells(after)<=8,'Abbreviation still too wide')
        changes.append(dict(text_index=item['text_index'],source_text=item['source_text'],before=before,
                            translated_text=after,reason='选项最多四个汉字宽度；保留可识别的名称或已有简称。'))
    path=p.WORK/'work/menu_option_fixes.json'
    if changes:
        p.save(path,changes)
        p.apply_batch(path)
    actual=p.load(p.WORK/'work/cache.json')
    for group,f in actual['files'].items():
        translated=[x for x in f['items'] if x['translation_status'] in (1,2)]
        if not translated: continue
        dest=p.inside(p.WORK/'translated_texts'/group)
        dest.write_text('\n'.join(f'[{x["text_index"]}] {x["translated_text"]}' for x in translated),encoding='utf-8')
    p.save(p.WORK/'reports/menu_option_review.json',dict(checked_options=checked,changed_options=len(changes),
                                                       limit_half_cells=8,changes=changes))
    print(f'Checked {checked} options; shortened {len(changes)} labels.')

if __name__=='__main__': main()
