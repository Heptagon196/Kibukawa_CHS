import json, collections, io, zipfile
import pipeline as p

g=p.load(p.WORK/'work/glossary_proposal.json')
g['locked']=True
g['source']='Reviewed against local story and confirmed opening style; provisional names here are project choices, not claimed official translations.'
g['terms'] += [dict(src='オバキュー',dst='尾Q',category='nickname'),dict(src='話す',dst='交谈',category='menu'),dict(src='見回す',dst='环顾',category='menu'),dict(src='調べる',dst='调查',category='menu'),dict(src='捜査中断',dst='中断调查',category='menu')]
g['non_translate']=[dict(marker='{0}',category='placeholder')]
p.save(p.WORK/'work/glossary.locked.json',g)
cache=p.load(p.WORK/'work/cache.json'); manifest=p.load(p.WORK/'work/manifest.json')
defs={int(k):v for k,v in manifest['definitions'].items()}
file=p.text_objects(p.UnityPy.load(str(p.WORK/'originals'/(p.STREAM+'file'))))
scratch=p.text_objects(p.UnityPy.load(str(p.WORK/'originals'/(p.STREAM+'scratchpad'))))
z=zipfile.ZipFile(io.BytesIO(p.raw_text(scratch['kamen.res'])))
script_bytes={n+'.txt':z.read(n) for n in z.namelist() if n.startswith('scn')}
script_bytes.update({f'subscn_{i+1}.txt':b for i,b in enumerate(p.sub_parts(p.raw_text(file['subscn'])))})
line_map={}
for group,data in script_bytes.items():
    line=0
    for c in p.parse_script(data,defs):
        if c['opcode'] in (71,73,75,76,77,78) or 105<=c['opcode']<=112 or 120<=c['opcode']<=123: line+=1
        for a in c['args']:
            if a['kind']==3: line_map[(group,a['offset'])]=f'{group}:{line}' if c['opcode']==72 else f'{group}:option:{a["offset"]}'
groups={}; tasks=[]
for name,f in cache['files'].items():
    rows=[]
    for x in f['items']:
        if x['translation_status']!=0: continue
        loc=x['extra']['location']
        rows.append(dict(text_index=x['text_index'],source_text=x['source_text'],display_line=line_map.get((name,loc.get('offset'))),kind=loc['kind'],opcode=loc.get('opcode')))
    if rows: groups[name]=rows
tail=[]
for name,rows in groups.items():
    if not name.startswith('scn') or name=='scn10.txt': tail+=rows; continue
    chunks=2 if len(rows)>650 else 1
    cut=len(rows)//2
    if chunks==2:
        while cut<len(rows) and rows[cut]['display_line']==rows[cut-1]['display_line']: cut+=1
    parts=[rows] if chunks==1 else [rows[:cut],rows[cut:]]
    for i,part in enumerate(parts):
        task=name[:-4]+(f'_{i+1}' if chunks>1 else '')
        p.save(p.WORK/f'work/parallel/input/{task}.json',part)
        tasks.append(dict(task=task,group=name,count=len(part),first=part[0]['text_index'],last=part[-1]['text_index'],context=f'texts/{name}'))
p.save(p.WORK/'work/parallel/input/ui_subscripts.json',tail)
tasks.append(dict(task='ui_subscripts',group='UI / subscn / scn10',count=len(tail),first=tail[0]['text_index'],last=tail[-1]['text_index'],context='texts/subscn_1.txt and UI groups'))
(p.WORK/'work/parallel/output').mkdir(parents=True,exist_ok=True)
p.save(p.WORK/'work/parallel/tasks.json',tasks)
print(json.dumps(tasks,ensure_ascii=False,indent=2))
