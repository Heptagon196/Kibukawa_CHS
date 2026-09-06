"""Apply the user-approved Chinese pun name without changing source lookup keys."""
import pipeline as p

def main():
    cache=p.load(p.WORK/'work/cache.json')
    updates={x['text_index']:x['translated_text'].replace('音成','林居')
             for x in p.items(cache) if x['translation_status'] in (1,2) and '音成' in x['translated_text']}
    # Reuse the original five slots for dialogue, rather than leaving annotation
    # placeholders or changing script offsets when removing the translation note.
    updates.update({1211:'即使不在身边，',1212:'也是您的邻居！',1213:'我是林居刑警，',1214:'今后还请',1215:'多多关照！”'})
    changes=[dict(text_index=x['text_index'],before=x['translated_text'],translated_text=updates[x['text_index']],
                  reason='用户指定音成译为林居，保留孝一；删除该姓氏的译注，恢复角色自我介绍。')
             for x in p.items(cache) if x['text_index'] in updates and updates[x['text_index']]!=x['translated_text']]
    path=p.WORK/'work/linju_name_fixes.json';p.save(path,changes)
    p.apply_batch(path)
    actual=p.load(p.WORK/'work/cache.json')
    p.require(not any('音成' in x['translated_text'] for x in p.items(actual)), 'Old translated surname remains')
    for group,f in actual['files'].items():
        rows=[x for x in f['items'] if x['translation_status'] in (1,2)]
        if rows:(p.WORK/'translated_texts'/group).write_text('\n'.join('[%s] %s'%(x['text_index'],x['translated_text']) for x in rows),encoding='utf-8')
    glossary=p.load(p.WORK/'work/glossary.locked.json')
    def revise(value):
        if isinstance(value,dict):
            if value.get('canonical')=='音成孝一':
                value['render']='林居孝一'
                value['note']='用户指定谐音汉化姓氏：音成单独出现译林居，全名译林居孝一；中文与邻居同音，无须译注。'
            for child in value.values():revise(child)
        elif isinstance(value,list):
            for child in value:revise(child)
    revise(glossary)
    glossary['chinese_only_clue_rendering']['お隣']='译为邻居；音成已按用户指定译为林居，在中文里同音，删除该姓氏的解释译注。'
    p.save(p.WORK/'work/glossary.locked.json',glossary)
    p.save(p.WORK/'reports/linju_name_review.json',dict(changes=changes,old_name_remaining=0,source_keys_unchanged=True))
    print('Updated',len(changes),'text slots; original-name keys preserved.')

if __name__=='__main__':main()
