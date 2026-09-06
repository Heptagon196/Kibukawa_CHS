"""Preserve the source distinction between Snowman and ordinary snowmen."""
import pipeline as p
from check_click_boundaries import units

# These describe shape, clothing, merchandise or the ordinary noun 雪だるま.
ORDINARY={3144,3150,4486,4499,4505,4551,4556,4577,4640,4652,4789,4795,5165,5171,5705,5721}

def main():
    cache=p.load(p.WORK/'work/cache.json');changes=[]
    for x in p.items(cache):
        idx=x['text_index'];before=x['translated_text'];after=before
        if idx not in ORDINARY:after=after.replace('雪人','Snowman')
        if idx==2274:after='Snow'
        if idx==2275:after='man，'
        if before!=after:changes.append(dict(text_index=idx,before=before,translated_text=after))
    path=p.WORK/'work/snowman_name_fixes.json';p.save(path,changes);p.apply_batch(path)
    cache=p.load(p.WORK/'work/cache.json')
    for group,f in cache['files'].items():
        rows=[x for x in f['items'] if x['translation_status'] in (1,2)]
        if rows:(p.WORK/'translated_texts'/group).write_text('\n'.join('[%s] %s'%(x['text_index'],x['translated_text']) for x in rows),encoding='utf-8')
    # Only approved slots are changed in the already-reviewed original units.
    replay=p.load(p.WORK/'bepinex/build/replay.json')['commands']
    baseline=p.load(p.WORK/'work/click_boundaries.reviewed.json')
    p.require(baseline['units']==units(replay),'Existing click baseline differs before renaming')
    modified={x['text_index']:x['translated_text'] for x in changes}
    locations={}
    for e in p.load(p.WORK/'work/manifest.json')['entries']:
        loc=e['location']
        if e['text_index'] in modified and loc['kind']=='script':
            name=loc.get('member') or 'subscn_'+str(loc['part']+1)
            locations[(name,loc['instruction'])]=modified[e['text_index']]
    for c in replay:
        if c['opcode']==72 and (c['script'],c['instruction']) in locations:c['expected']=[locations[c['script'],c['instruction']]]
    baseline['units']=units(replay);baseline['version']='1.0.29'
    p.save(p.WORK/'work/click_boundaries.reviewed.json',baseline)
    glossary=p.load(p.WORK/'work/glossary.locked.json')
    for term in glossary['terms']:
        if term['src'] in ('スノーマン','ｽﾉｰﾏﾝ'):term['dst']='Snowman'
        if term['src']=='スノーマンシステム':term['dst']='Snowman系统'
    glossary['snowman_distinction']='用户指定：怪物专名和引用此名的邮件/留言统一为Snowman，系统名为Snowman系统；雪だるま所指的普通雪人、玩偶服、周边保持雪人，保留推理歧义。'
    p.save(p.WORK/'work/glossary.locked.json',glossary)
    guide=p.WORK/'work/STYLE_GUIDE.md';text=guide.read_text(encoding='utf-8')
    guide.write_text(text+'\n- Snowman是怪物专名，系统名译Snowman系统；相关邮件与留言保留Snowman。普通雪人、雪人服装和周边仍译雪人，禁止把专名和形状名合并。\n',encoding='utf-8')
    p.save(p.WORK/'reports/snowman_name_review.json',dict(changes=changes,ordinary_snowman_preserved=sorted(ORDINARY),source_keys_unchanged=True))
    readme=p.WORK/'README.md';readme.write_text(readme.read_text(encoding='utf-8').replace('当前插件为 1.0.28。','当前插件为 1.0.29。怪物专名Snowman与普通雪人分开，邮件、留言、系统名及推理说明同步。'),encoding='utf-8')
    print('Updated',len(changes),'slots; ordinary snowman descriptions preserved.')

if __name__=='__main__':main()
