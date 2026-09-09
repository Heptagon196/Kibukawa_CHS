"""Prepare current source/target click units without approving them."""
import argparse
import copy
import sys
import pipeline as p
sys.path.insert(0,str(p.SERIES/'tools'))
from click_boundaries import units

def current():
    p.validate_sources()
    manifest=p.load(p.WORK/'work/manifest.json')
    cache=p.load(p.WORK/'work/cache.json')
    rows={x['text_index']:x for f in cache['files'].values() for x in f['items']}
    commands=copy.deepcopy(p.load(p.WORK/'research/source-replay.json')['commands'])
    lookup={}
    for e in manifest['entries']:
        loc=e['location']
        if loc['kind']!='script':continue
        name=loc.get('member') or 'subscn_'+str(loc['part']+1)
        lookup[(name,loc['instruction'])]=e
    for c in commands:
        c['expected']=c['strings'][:]
        e=lookup.get((c['script'],c['instruction']))
        if e and c['opcode']==72:
            row=rows[e['text_index']]
            p.require(row['source_text']==e['source_text'] and row['extra']['location']==e['location'],'Source/position mismatch')
            p.require(c['strings'][0]==e['source_text'],'Replay mismatch')
            c['expected'][0]=row['translated_text'] if row['translation_status'] in (1,2) else row['source_text']
    return commands,lookup

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--script',required=True);parser.add_argument('--export',action='store_true');args=parser.parse_args()
    commands,lookup=current()
    if args.export:p.save(p.WORK/'bepinex/build/replay.json',dict(commands=commands))
    for u in units(commands):
        if u['script']!=args.script:continue
        ids=[lookup[(u['script'],i)]['text_index'] for i in u['instructions'] if (u['script'],i) in lookup]
        print(','.join(map(str,ids))+'|'+u['source'])
        if u['target']!=u['source']:print('ZH|'+u['target'])
