"""Tenth-game source/target review candidates and strict stale-baseline gate.

The IL for BUNSYOU_PERIOD/COLON/SEMICOLON confirms 2E/3A/3B wait for
Key_select/aKey_down. PERIOD clears; COLON continues; SEMICOLON advances row.
Other control events remain in the reviewed payload but are not click breaks.
This module never writes reviewed files.
"""
import argparse
import hashlib
import html
import json
import re
import pipeline as p

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def candidates():
    doc=p.load(p.WORK/'work/dialogue-tagged.json')
    table={(u['script'],u['instruction']):u for u in doc['units'] if u['active']}
    replay=p.load(p.WORK/'research/source-replay.json')['scripts']
    clicks,colors=[],[]
    for script,commands in replay.items():
        if not any(k[0]==script for k in table): continue
        pending=[]
        def flush(boundary):
            if pending:
                value=dict(script=script,boundary=boundary,spans=list(pending))
                clicks.append(dict(id=script+':'+str(boundary),sha256=digest(value),**value))
                pending.clear()
        for c in commands['commands']:
            u=table.get((script,c['offset']))
            if c['opcode'] in (1,2,3,4,5,6,8,15,17,47,69,72,73,76):
                flush(str(c['offset'])+':opcode'+str(c['opcode']))
            if not u or 'argument' in u: continue
            src=re.split(r'(<[^>]+>)',u['source'])
            dst=re.split(r'(<[^>]+>)',u['target']) if u['target'] else ['']*len(src)
            if u['target'] and re.findall(r'<[^>]+>',u['source'])!=re.findall(r'<[^>]+>',u['target']):
                raise ValueError('Tag mismatch '+u['id'])
            color=None
            for index,(s,t) in enumerate(zip(src,dst)):
                if s.startswith('<color='): color=int(s[7:-1])
                elif s=='</color>': color=None
                elif s.startswith('<ctrl='):
                    pending.append(dict(id=u['id'],token=index,control=s))
                    if s in ('<ctrl=2E/>','<ctrl=3A/>','<ctrl=3B/>'):
                        flush(u['id'].split(':')[-1]+':token'+str(index))
                elif s.startswith('<'): pass
                elif s or t:
                    span=dict(id=u['id'],token=index,color=color,source=html.unescape(s),target=html.unescape(t))
                    pending.append(span)
                    if color not in (None,0):
                        colors.append(dict(id=u['id']+':token'+str(index),sha256=digest(span),**{k:v for k,v in span.items() if k!='id'}))
        flush('end')
    return dict(clicks=clicks,colors=colors)

def check(strict=False):
    current=candidates()
    overlay_path=p.WORK/'work/qa-fixes.reviewed.json'
    overlay=p.load(overlay_path) if overlay_path.exists() else None
    overlay_valid=bool(overlay and overlay.get('adapter')=='gmode-20050817-direct' and
        overlay.get('dialogue_sha256')==p.sha((p.WORK/'work/dialogue-tagged.json').read_bytes()) and
        overlay.get('integration_review_sha256')==p.sha((p.WORK/'work/fixes/integration-review.json').read_bytes()))
    reports={}
    for kind,path in [('clicks','work/click_boundaries.reviewed.json'),('colors','research/color-spans.reviewed.json')]:
        baseline=p.WORK/path
        reviewed=p.load(baseline) if baseline.exists() else {}
        records={u['id']:u for u in reviewed.get('units',[])}
        overlay_records={u['id']:u for u in overlay.get(kind,[])} if overlay_valid else {}
        unknown=sorted(set(overlay_records)-{u['id'] for u in current[kind]})
        if unknown: raise ValueError('Unknown QA review records: '+repr(unknown[:10]))
        records.update(overlay_records)
        changed=[u for u in current[kind] if records.pop(u['id'],None)!=u]
        passed=baseline.exists() and reviewed.get('adapter')=='gmode-20050817-direct' and not changed and not records
        report=dict(schema=1,adapter='gmode-20050817-direct',kind=kind,status='passed' if passed else 'review_required',
                    units=current[kind],changed_ids=[u['id'] for u in changed],removed_ids=list(records),
                    note='Candidate output is not approval. Review source, translation and context before recording baseline.')
        p.save(p.WORK/('reports/'+kind+'-review.json'),report)
        reports[kind]=dict(status=report['status'],total=len(current[kind]),changed=len(changed),removed=len(records),
                           qa_overlay=len(overlay_records) if overlay_valid else 0)
    if strict and any(r['status']!='passed' for r in reports.values()):
        raise ValueError('Missing/stale semantic review baselines: '+repr(reports))
    return reports

def export_scenes():
    """Write scene-sized materials only, never approval records."""
    current=candidates()
    scripts=sorted({u['script'] for u in current['clicks']})
    output=p.WORK/'reports/review-scenes'
    for script in scripts:
        p.save(output/(script.replace('/','__')+'.json'),dict(schema=1,script=script,
            clicks=[u for u in current['clicks'] if u['script']==script],
            colors=[u for u in current['colors'] if u['id'].split(':',1)[0]==script],
            note='Review material only. No semantic approval is implied.'))
    return dict(scenes=len(scripts),directory=str(output))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strict',action='store_true')
    parser.add_argument('--export-scenes',action='store_true')
    args=parser.parse_args()
    print(check(args.strict))
    if args.export_scenes: print(export_scenes())
