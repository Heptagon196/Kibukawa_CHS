"""Shared tagged dialogue codec for reviewed gmode-v1 and gmode-dual-v1 scripts."""
import argparse
import copy
import hashlib
import html
import json
import re
from pathlib import Path
from click_boundaries import units
from project_config import resolve

def require(ok,message):
    if not ok:raise ValueError(message)
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def current(project,commands=None):
    project=Path(project);manifest=load(project/'work/manifest.json');cache=load(project/'work/cache.json')
    rows={r['text_index']:r for f in cache['files'].values() for r in f['items']}
    lookup={}
    for e in manifest['entries']:
        loc=e['location']
        if loc['kind']!='script':continue
        key=(loc.get('member') or 'subscn_'+str(loc['part']+1),loc['instruction'])
        if loc['opcode']==72:lookup[key]=e
    replay_path=project/'bepinex/build/replay.json'
    if not replay_path.exists():replay_path=project/'research/source-replay.json'
    cs=copy.deepcopy(commands if commands is not None else load(replay_path)['commands'])
    seen=set()
    for c in cs:
        key=(c['script'],c['instruction']);require(key not in seen,'Duplicate command');seen.add(key)
        c['expected']=c['strings'][:]
        if key in lookup:
            e=lookup[key];r=rows[e['text_index']]
            require(r['source_text']==e['source_text'] and r['extra']['location']==e['location'] and c['strings'][0]==e['source_text'],'Source/slot mismatch: '+str(key))
            c['expected'][0]=r['translated_text'] if r['translation_status'] in (1,2) else r['source_text']
    require(set(lookup)<=seen,'Missing source commands')
    return cs,lookup,rows

def hard_breaks(project):
    path=Path(project)/"research/hard-breaks.json"
    return load(path) if path.exists() else {}

def layouts(commands, lookup, breaks=None):
    breaks=breaks or {}
    active=None; regions={}; fence=0; script=None; hard=False
    for c in commands:
        key=(c['script'],c['instruction'])
        if script!=c['script']:active=None;fence+=1;script=c['script']
        if c['opcode']==80:
            values=c.get('integers',[])
            require(values,'Missing original color operand: '+str(key))
            active=values[0];fence+=1
        elif c['opcode']==81:active=None;fence+=1
        elif c['opcode']==72:regions[key]=(active,fence,hard);hard=False
        elif c['opcode']==77 and c['instruction'] in breaks.get(c['script'],[]):fence+=1;hard=True
        elif c['opcode']!=77:fence+=1
    for u in sorted(units(commands), key=lambda u:(u['script'],u['end'])):
        groups=[]
        for address in u['instructions']:
            key=(u['script'],address);e=lookup[key];color,f,hard=regions[key]
            if not groups or groups[-1]['fence']!=f:
                groups.append(dict(color=color,fence=f,hard=hard,ids=[],source=''))
            groups[-1]['ids'].append(e['text_index']);groups[-1]['source']+=e['source_text']
        yield dict(script=u['script'],end=u['end'],groups=groups)

def markup(layout, texts):
    parts=[]
    for j,(g,text) in enumerate(zip(layout['groups'],texts)):
        # An explicit boundary prevents moving words through dynamic values or controls.
        if j:parts.append(('<br=' if g.get('hard') else '<boundary=')+str(g['ids'][0])+'/>')
        t=html.escape(text,quote=False)
        if g['color'] is not None:t='<color='+{2:'YELLOW',5:'RED',6:'GREEN'}.get(g['color'],str(g['color']))+'>'+t+'</color>'
        parts.append(t)
    return ''.join(parts)

def decode(layout, text):
    require(isinstance(text,str),'Tagged target must be text')
    template=markup(layout,['TOKEN'+str(i)+'END' for i in range(len(layout['groups']))])
    pattern=re.escape(template)
    for i in range(len(layout['groups'])):pattern=pattern.replace('TOKEN'+str(i)+'END','([^<>]*)')
    m=re.fullmatch(pattern,text)
    require(m is not None,'Color/boundary tags changed at '+str((layout['script'],layout['end'])))
    result={}
    for g,raw in zip(layout['groups'],m.groups()):
        t=html.unescape(raw);n=len(g['ids'])
        require(not any(x in t for x in '\r\n\t\0'),'Invalid text controls')
        require(len(t.encode('utf-16-le'))//2<=20*n,'Color segment capacity exceeded')
        for j,i in enumerate(g['ids']):
            piece=t[len(t)*j//n:len(t)*(j+1)//n]
            require(len(piece.encode('utf-16-le'))//2<=20,'Text slot capacity exceeded')
            result[i]=piece
    return result

def document(project,commands=None):
    cs,lookup,rows=current(project,commands)
    return dict(schema=1,units=[dict(script=u['script'],end=u['end'],source=markup(u,[g['source'] for g in u['groups']]),target=markup(u,[''.join(rows[i]['translated_text'] for i in g['ids']) for g in u['groups']])) for u in layouts(cs,lookup,hard_breaks(project))])

def spans(project,commands=None):
    cs,lookup,rows=current(project,commands);result=[];active=None;script=None
    for c in cs:
        if script!=c['script']:active=None;script=c['script']
        if c['opcode']==80:
            active=dict(script=script,start=c['instruction'],color=c['integers'][0],source='',target='');result.append(active)
        elif c['opcode']==81:active=None
        elif c['opcode']==72 and active is not None:
            active['source']+=c['strings'][0] or '';active['target']+=c['expected'][0] or ''
    return sorted(result,key=lambda x:(x['script'],x['start']))

def validate(project,commands=None):
    project=Path(project);actual=document(project,commands);reviewed=load(project/'work/dialogue-tagged.json')
    require(actual==reviewed,'Tagged source/target differs: '+str(project))
    cs,lookup,_=current(project,commands)
    for layout,row in zip(layouts(cs,lookup,hard_breaks(project)),reviewed['units']):decode(layout,row['target'])
    expected=sorted(load(project/'research/color-spans.reviewed.json'),key=lambda x:(x['script'],x['start']))
    require(spans(project,commands)==expected,'Color semantics require review: '+str(project))
    return dict(units=len(actual['units']),colors=len(expected))

def import_document(project):
    project=Path(project);draft=load(project/'work/dialogue-tagged.json');before=document(project)
    require(set(draft)=={'schema','units'} and draft['schema']==1,'Unsupported tagged schema')
    require(len(draft['units'])==len(before['units']),'Missing tagged units')
    cs,lookup,rows=current(project);edits={}
    for layout,entry,original in zip(layouts(cs,lookup,hard_breaks(project)),draft['units'],before['units']):
        require(set(entry)==set(original) and all(entry[k]==original[k] for k in ('script','end','source')),'Source/order changed')
        decoded=decode(layout,entry['target'])
        for g in layout['groups']:
            if ''.join(decoded[i] for i in g['ids'])!=''.join(rows[i]['translated_text'] for i in g['ids']):
                edits.update({i:decoded[i] for i in g['ids']})
    cache=load(project/'work/cache.json');config=load(project/'project.json')
    approved=config.setdefault('approved_empty_layout_text',{})
    for f in cache['files'].values():
        for row in f['items']:
            i=row['text_index']
            if i not in edits:continue
            row['translated_text']=edits[i];row['translation_status']=1
            if not edits[i]:
                reason='带标签译稿在同色及执行指令区间内合并中文；不删除原始指令'
                approved[str(i)]=dict(source=row['source_text'],target='',reason=reason);row['extra']['empty_translation_reason']=reason
            else:approved.pop(str(i),None)
    save(project/'work/cache.json',cache);save(project/'project.json',config)
    require(document(project)==draft,'Import roundtrip mismatch')
    # Deliberately do not bless click/color review baselines.

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['extract','import','check']);parser.add_argument('--game',required=True);parser.add_argument('--output');args=parser.parse_args()
    project=resolve(args.game)['project']
    if args.action=='extract':
        path=(project/(args.output or 'texts/dialogue-tagged.json')).resolve()
        require(path.is_relative_to(project) and path!=project/'work/dialogue-tagged.json','Extraction may not overwrite reviewed tagged dialogue')
        save(path,document(project))
    elif args.action=='import':import_document(project)
    else:print(args.game,validate(project))
if __name__=='__main__':main()
