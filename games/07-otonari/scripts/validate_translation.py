"""Read-only seventh-game source, translation, tag and reviewed-boundary checks."""
import base64
import collections
import io
import itertools
import json
import re
import struct
import sys
import zipfile
import pipeline as p
sys.path.insert(0,str(p.SERIES/'tools'))
import dialogue_tags as tags
import click_boundaries
from check_text_style import audit

def main():
    manifest=p.validate_sources();config=p.load(p.WORK/'project.json');cache=p.load(p.WORK/'work/cache.json')
    rows={x['text_index']:x for f in cache['files'].values() for x in f['items']}
    p.require(len(rows)==len(manifest['entries']),'Coverage mismatch')
    excluded={e['text_index'] for e in manifest['entries'] if e['excluded']}|{int(i) for i in config['reviewed_exclusions']}
    for e in manifest['entries']:
        r=rows[e['text_index']]
        p.require(r['source_text']==e['source_text'] and r['extra']['location']==e['location'],'Source mapping differs')
        p.require(r['translation_status']==7 if e['text_index'] in excluded else r['translation_status'] in (1,2),'Unreviewed status')
        if r['translation_status'] in (1,2) and re.search('[\u3040-\u30ff\uff66-\uff9f]',r['translated_text']):
            p.require(e['text_index']==5613 and r['translated_text']=='ｽｰﾊﾟｰｹﾞｰﾑﾗﾝﾁ','Untranslated kana')
        if r['translation_status'] in (1,2) and not r['translated_text']:
            p.require(str(e['text_index']) in config['approved_empty_layout_text'],'Unapproved empty slot')
    assets=p.text_assets(p.GAME/(p.STREAM+'file'));defs=p.definitions(assets['define']);table=struct.unpack('<65537H',base64.b64decode(manifest['codec_base64']))
    p.require({str(k):v for k,v in defs.items()}==manifest['definitions'],'Original definitions changed')
    archive=zipfile.ZipFile(io.BytesIO(p.text_assets(p.GAME/(p.STREAM+'scratchpad'))['otonari.res']))
    scripts=[(n,archive.read(n)) for n in ('scn0','scn1','scn2','scn3')]+[(f'subscn_{i+1}',d) for i,d in enumerate(p.sub_parts(assets['subscn']))]
    original=[];jump_targets={}
    for name,data in scripts:
        commands=p.parse_script(data,defs);jump_targets[name]={a['value'] for c in commands for a in c['args'] if a['kind']==4 and a['value']!=65535}
        for c in commands:
            original.append(dict(script=name,instruction=c['offset'],opcode=c['opcode'],nextCursor=c['end'],strings=[p.decode(a['value'],table) if a['value'] else None for a in c['args'] if a['kind']==3],integers=[a['value'] if a['value']<2147483648 else a['value']-4294967296 for a in c['args'] if a['kind']!=3]))
    p.require(original==p.load(p.WORK/'research/source-replay.json')['commands'],'Raw replay differs')
    cs,lookup,_=tags.current(p.WORK,original)
    byid={e['text_index']:e for e in manifest['entries']}
    for l in tags.layouts(cs,lookup,tags.hard_breaks(p.WORK)):
        for g in l['groups']:
            for i in g['ids'][1:]:p.require(byid[i]['location']['instruction'] not in jump_targets[l['script']],'Branch join merged into preceding text')
    p.require(p.load(p.WORK/'research/color-spans.reviewed.json')==p.load(p.WORK/'review/color-spans.reviewed.json'),'Color approval copies differ')
    tagged=tags.validate(p.WORK,original);click=click_boundaries.validate(cs,p.WORK,strict=True)
    def text(i):return rows[i]['translated_text']
    first=[text(a)+text(b)+text(2665) for a,b in itertools.product((2661,2662),(2663,2664))]
    second=[text(a)+text(b)+text(c)+text(2738) for a,b,c in itertools.product(range(2726,2730),range(2730,2734),range(2734,2738))]
    for phrase in first+second:p.require(phrase.count('“')==phrase.count('”')==1,'Dynamic quote mismatch')
    p.require(any(c['script']=='scn3' and c['instruction']==8212 and c['integers']==[7933] for c in original),'Correct-route join changed')
    correct=text(2677)+text(2678)+text(2665)
    p.require(correct==first[1],'Correct answer fails shared suffix composition')
    # Published baseline remains unchanged; validate every new seventh-game provenance record directly.
    public=p.load(p.SERIES/'series/glossary.json');local=p.load(p.WORK/'work/glossary.locked.json');ref=public['source_tables']['kibu7']
    p.require(ref['sha256']==p.sha((p.WORK/'work/glossary.locked.json').read_bytes()),'Local glossary hash stale')
    refs=[]
    for section in ('characters','terms','non_translate'):
        for record in public[section]:
            for source_ref in record['source_refs']:
                if not source_ref.startswith('kibu7/'):continue
                _,sec,index=source_ref.split('/');r=local[sec][int(index)]
                p.require(sec==section and (r['canonical'],r['render'])==(record['canonical'],record['render']),'New glossary reference differs')
                p.require(set(r.get('aliases',[]))<=set(record.get('aliases',[])),'Lost alias');refs.append(source_ref)
    p.require(len(refs)==sum(r.get('status')=='confirmed_local' for sec in ('characters','terms','non_translate') for r in local[sec]),'Unmerged confirmed seventh-game term')
    style=audit('kibu7');reviewed=p.load(p.WORK/'review/text-style.reviewed.json')
    # Shared checker emits candidates; compare exact reviewed source/target/rule tuples, not broad suppressions.
    normalize=lambda findings:[{k:v for k,v in x.items() if k!='review_reason'} for x in findings]
    p.require(normalize(style['findings'])==normalize(reviewed['findings']),'New style review candidates')
    report=dict(game='kibu7',translated_entries=len(rows)-len(excluded),excluded_entries=len(excluded),pending_entries=0,raw_instructions=len(original),click_units=click['unit_count'],color_spans=tagged['colors'],dynamic_combinations=len(first)+len(second),glossary_references_verified=len(refs),reviewed_style_candidates=len(style['findings']),runtime_tested=False,scope='Offline raw source/slot/markup/review consistency; no Unity execution or visual verification.',cache_sha256=p.sha((p.WORK/'work/cache.json').read_bytes()))
    p.save(p.WORK/'reports/translation-validation.json',report)
    p.save(p.WORK/'reports/dynamic-combinations.json',dict(key_combinations=first,action_combinations=second,correct_backjump=correct))
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
