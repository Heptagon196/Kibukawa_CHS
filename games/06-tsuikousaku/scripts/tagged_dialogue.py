"""Tagged translation exchange: color and executable boundaries are structural, never prose."""
import argparse
import html
import re
import pipeline as p
from review_units import current
from click_boundaries import units
DOCUMENT=p.WORK/'work/dialogue-tagged.json'

def layouts(commands, lookup):
    palette={(c['script'],c['instruction']):c.get('integers',[]) for c in p.load(p.WORK/'research/color-commands.json')}
    active=None; regions={}; fence=0; script=None
    for c in commands:
        key=(c['script'],c['instruction'])
        if script!=c['script']:active=None;fence+=1;script=c['script']
        if c['opcode']==80:
            values=c.get('integers',palette.get(key,[]))
            p.require(values,'Missing original color operand: '+str(key))
            active=values[0];fence+=1
        elif c['opcode']==81:active=None;fence+=1
        elif c['opcode']==72:regions[key]=(active,fence)
        elif c['opcode']!=77:fence+=1
    for u in sorted(units(commands), key=lambda u:(u['script'],u['end'])):
        groups=[]
        for address in u['instructions']:
            key=(u['script'],address);e=lookup[key];color,f=regions[key]
            if not groups or groups[-1]['fence']!=f:
                groups.append(dict(color=color,fence=f,ids=[],source=''))
            groups[-1]['ids'].append(e['text_index']);groups[-1]['source']+=e['source_text']
        yield dict(script=u['script'],end=u['end'],groups=groups)

def markup(layout, texts):
    parts=[]
    for j,(g,text) in enumerate(zip(layout['groups'],texts)):
        # An explicit boundary prevents moving words through dynamic values or controls.
        if j:parts.append('<boundary='+str(g['ids'][0])+'/>')
        t=html.escape(text,quote=False)
        if g['color'] is not None:t='<color='+{2:'YELLOW',5:'RED',6:'GREEN'}.get(g['color'],str(g['color']))+'>'+t+'</color>'
        parts.append(t)
    return ''.join(parts)

def decode(layout, text):
    p.require(isinstance(text,str),'Tagged target must be text')
    template=markup(layout,['TOKEN'+str(i)+'END' for i in range(len(layout['groups']))])
    pattern=re.escape(template)
    for i in range(len(layout['groups'])):pattern=pattern.replace('TOKEN'+str(i)+'END','([^<>]*)')
    m=re.fullmatch(pattern,text)
    p.require(m is not None,'Color/boundary tags changed at '+str((layout['script'],layout['end'])))
    result={}
    for g,raw in zip(layout['groups'],m.groups()):
        t=html.unescape(raw);n=len(g['ids'])
        p.require(not any(x in t for x in '\r\n\t\0'),'Invalid text controls')
        p.require(len(t.encode('utf-16-le'))//2<=20*n,'Color segment capacity exceeded')
        for j,i in enumerate(g['ids']):
            piece=t[len(t)*j//n:len(t)*(j+1)//n]
            p.require(len(piece.encode('utf-16-le'))//2<=20,'Text slot capacity exceeded')
            result[i]=piece
    return result

def export_document(commands=None):
    cs,lookup=current()
    if commands is not None:cs=commands
    cache=p.load(p.WORK/'work/cache.json');rows={r['text_index']:r for f in cache['files'].values() for r in f['items']}
    return dict(schema=1,units=[dict(script=u['script'],end=u['end'],source=markup(u,[g['source'] for g in u['groups']]),target=markup(u,[''.join(rows[i]['translated_text'] for i in g['ids']) for g in u['groups']])) for u in layouts(cs,lookup)])

def validate(commands=None):
    actual=export_document(commands);reviewed=p.load(DOCUMENT)
    p.require(actual==reviewed,'Tagged dialogue differs from cache/source; edit tagged dialogue and import it before building')
    cs,lookup=current()
    for layout,row in zip(layouts(commands or cs,lookup),reviewed['units']):decode(layout,row['target'])
    return len(actual['units'])

def import_document():
    cs,lookup=current();document=p.load(DOCUMENT);current_doc=export_document();ls=list(layouts(cs,lookup))
    p.require(set(document)=={'schema','units'} and document['schema']==1,'Unsupported tagged document schema')
    p.require(len(document['units'])==len(ls),'Missing tagged units')
    edits={}
    for layout,entry,original in zip(ls,document['units'],current_doc['units']):
        p.require(set(entry)==set(original),'Unexpected tagged unit fields')
        p.require(all(entry[k]==original[k] for k in ('script','end','source')),'Tagged source/order changed')
        edits.update(decode(layout,entry['target']))
    cache=p.load(p.WORK/'work/cache.json');config=p.load(p.WORK/'project.json');approved={}
    for f in cache['files'].values():
        for row in f['items']:
            i=row['text_index']
            if i not in edits:continue
            row['translated_text']=edits[i]
            if not edits[i]:
                reason='同一颜色与执行指令区间内的中文合并；完整文字保存在带标签译稿中'
                approved[str(i)]=dict(source=row['source_text'],target='',reason=reason)
                row['extra']['empty_translation_reason']=reason
    config['approved_empty_layout_text']=approved
    p.save(p.WORK/'work/cache.json',cache);p.save(p.WORK/'project.json',config)
    validate()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['extract','import','check']);parser.add_argument('--output');args=parser.parse_args()
    if args.action=='extract':
        p.require(args.output,'Extraction requires --output; never overwrite reviewed translations implicitly')
        p.save(p.inside(p.WORK/args.output),export_document())
    elif args.action=='import':import_document()
    else:print('PASS tagged dialogue:',validate())
