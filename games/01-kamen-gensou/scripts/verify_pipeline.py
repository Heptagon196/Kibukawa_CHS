"""Real-resource integration checks. Never edits the translation cache or game."""
import copy, io, json, struct, zipfile
from pathlib import Path
import pipeline as p

def main():
    manifest=p.load(p.WORK/'work/manifest.json'); cache=p.load(p.WORK/'work/cache.json')
    table=struct.unpack('<65537H',__import__('base64').b64decode(manifest['codec_base64']))
    defs={int(k):v for k,v in manifest['definitions'].items()}
    file=p.text_objects(p.UnityPy.load(str(p.WORK/'originals'/ (p.STREAM+'file'))))
    scratch=p.text_objects(p.UnityPy.load(str(p.WORK/'originals'/(p.STREAM+'scratchpad'))))
    z=zipfile.ZipFile(io.BytesIO(p.raw_text(scratch['kamen.res'])))
    scripts={n:z.read(n) for n in z.namelist() if n.startswith('scn')}
    scripts.update({f'subscn_{i+1}':b for i,b in enumerate(p.sub_parts(p.raw_text(file['subscn'])))})
    for name,raw in scripts.items():
        rebuilt,_=p.rebuild_script(raw,defs,{},table)
        p.require(rebuilt==raw,f'Identity script rebuild failed: {name}')
        before=p.parse_script(raw,defs)
        # Replace one actual string and compare branch destinations by instruction ordinal.
        arg=next(a for c in before for a in c['args'] if a['kind']==3)
        edited,_=p.rebuild_script(raw,defs,{arg['offset']:'中'},table)
        after=p.parse_script(edited,defs)
        old_ord={c['offset']:i for i,c in enumerate(before)}
        new_ord={c['offset']:i for i,c in enumerate(after)}
        for old,new in zip(before,after):
            p.require(old['opcode']==new['opcode'],'Opcode changed')
            for a,b in zip(old['args'],new['args']):
                if a['kind']==4:
                    p.require((a['value']==65535 and b['value']==65535) or old_ord.get(a['value'])==new_ord.get(b['value']),'Branch changed its logical destination')
                elif a['kind']!=3: p.require(a['value']==b['value'],'Nontext parameter changed')
    # Exercise UTF8 text growth/shrinkage, every scenario, subscenario lengths,
    # ZIP repack, Unity aligned string lengths, CSV quoting and managed IL strings.
    test=copy.deepcopy(cache); by_id={x['text_index']:x for x in p.items(test)}
    chosen=[]; seen=set()
    for e in manifest['entries']:
        if e['excluded']: continue
        loc=e['location']; kind=loc['kind']
        key=(kind,loc.get('member'),loc.get('part')) if kind=='script' else (kind,loc['file'])
        if key in seen: continue
        if kind=='script' and loc['opcode'] not in (70,72,105,106,107,108,109,110,111,112): continue
        if '{' in e['source_text'] or '<' in e['source_text']: continue
        seen.add(key); chosen.append(e['text_index'])
        x=by_id[e['text_index']]; x['translation_status']=1
        x['translated_text']='中文测试' if kind=='script' else '中文测试，"引用"'
    temp=p.WORK/'reports'/'integration_cache.json'; p.save(temp,test)
    output,report=p.build(temp,p.WORK/'out'/('verification_'+p.stamp()))
    # Confirm invalid cache input is rejected before output creation.
    def rejected(c):
        try: p.validate_cache(c,manifest)
        except ValueError: return True
        raise AssertionError('Invalid cache accepted')
    bad=copy.deepcopy(cache); p.items(bad)[0]['source_text']='bad'; rejected(bad)
    bad=copy.deepcopy(cache); p.items(bad)[0].update(translation_status=1,translated_text=''); rejected(bad)
    bad=copy.deepcopy(cache); p.items(bad)[0].update(translation_status=1,translated_text='中'*21); rejected(bad)
    bad=copy.deepcopy(cache); p.items(bad)[0].update(translation_status=1,translated_text='中\0文'); rejected(bad)
    try: p.inside(p.GAME/'kibu1_Data/unsafe')
    except ValueError: pass
    else: raise AssertionError('Game output location accepted')
    result=dict(script_identity_roundtrips=len(scripts),script_branch_semantics_checks=len(scripts),integration_changed_indices=chosen,integration_output=str(output),
                rejection_checks=['edited source','empty translation','line overflow','NUL','outside workspace'],original_game_unchanged=report['original_game_unchanged'])
    p.save(p.WORK/'reports/verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
