"""Shared static click-unit review gate. Never creates or updates approval baselines."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

PROFILES = {
    name: dict(text=72, boundaries={71,73,75,76,78,79}, menu_min=105, menu_max=130)
    for name in ('gmode-v1','gmode-dual-v1')
}
def load(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def units(commands, adapter='gmode-v1'):
    if adapter not in PROFILES: raise ValueError('Unreviewed click-boundary adapter: '+adapter)
    profile=PROFILES[adapter]; result=[];pending=[];script=None;seen=set()
    def flush(end,opcode):
        if pending:
            result.append(dict(script=script,end=end,opcode=opcode,
                instructions=[c['instruction'] for c in pending],
                source=''.join((c['strings'][0] or '') for c in pending),
                target=''.join((c['expected'][0] or '') for c in pending)))
            pending.clear()
    for c in commands:
        key=(c['script'],c['instruction'])
        if key in seen: raise ValueError('Duplicate replay instruction: '+str(key))
        seen.add(key)
        if c['script']!=script: flush(-1,-1);script=c['script']
        op=c['opcode']
        if op==profile['text']:
            if not c['strings'] or not c['expected']: raise ValueError('Missing dialogue slot')
            pending.append(c)
        elif op in profile['boundaries'] or profile['menu_min']<=op<profile['menu_max']:
            flush(c['instruction'],op)
    flush(-1,-1)
    return result

def compare(current, reviewed):
    previous={}
    for u in reviewed:
        key=(u['script'],u['end'])
        if key in previous: raise ValueError('Duplicate baseline unit: '+str(key))
        previous[key]=u
    changed=[];unchanged=0
    for u in current:
        prior=previous.pop((u['script'],u['end']),None)
        if prior==u: unchanged+=1
        else: changed.append(dict(current=u,reviewed=prior))
    return changed,list(previous.values()),unchanged

def validate(commands, project, adapter=None, strict=True):
    project=Path(project).resolve();config=load(project/'project.json')
    adapter=adapter or config['adapter'];current=units(commands,adapter)
    baseline=project/'work/click_boundaries.reviewed.json'
    exists=baseline.is_file();reviewed=load(baseline) if exists else None
    if exists and reviewed.get('adapter',adapter)!=adapter: raise ValueError('Baseline adapter mismatch')
    changed,removed,unchanged=compare(current,reviewed['units'] if exists else [])
    passed=exists and not changed and not removed
    report=dict(schema=1,game=config['id'],adapter=adapter,profile='legacy-click-units-v1',
        status='passed' if passed else ('baseline_missing' if not exists else 'review_required'),
        unit_count=len(current),unchanged_units=unchanged,changed_units=[x['current'] for x in changed],
        comparisons=changed,removed_units=removed,baseline_sha256=sha(baseline) if exists else None,
        cache_sha256=sha(project/'work/cache.json'),
        scope='Static source click/clear/speaker/menu units; opcode77 is visual wrapping, not a click. Does not prove semantic accuracy or reproduce all runtime branches; review each unit against source and context. Baselines are never automatically accepted.')
    out=project/'reports/click_boundaries.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if strict and not passed:
        raise ValueError(f"{config['id']}: {report['status']}; {len(changed)} units need source/target review. See {out}. Do not accept current text automatically.")
    return report

def audit_project(project, strict=False):
    """Use extracted/build replay structure, but always overlay the current cache.
    This report command never builds binaries, mutates translations or blesses text.
    Production builds pass freshly parsed actual-byte commands directly to validate.
    """
    project=Path(project);manifest=load(project/'work/manifest.json');cache=load(project/'work/cache.json')
    replay=project/'bepinex/build/replay.json'
    if not replay.exists(): raise ValueError('No extracted build replay; generate the project export first: '+str(replay))
    commands=copy.deepcopy(load(replay)['commands']);table={(c['script'],c['instruction']):c for c in commands}
    if len(table)!=len(commands): raise ValueError('Duplicate replay command')
    rows={x['text_index']:x for f in cache['files'].values() for x in f['items']};expected=set()
    for e in manifest['entries']:
        loc=e['location']
        if loc['kind']!='script' or loc['opcode']!=72: continue
        name=loc.get('member') or 'subscn_'+str(loc['part']+1)
        key=(name,loc['instruction']);c=table.get(key);row=rows[e['text_index']]
        if c is None or c['opcode']!=72 or c['strings'][0]!=e['source_text'] or row['source_text']!=e['source_text'] or row['extra']['location']!=loc:
            raise ValueError('Replay/cache/source mismatch: '+str(key))
        c['expected'][0]=row['translated_text'] if row['translation_status'] in (1,2) else e['source_text'];expected.add(key)
    actual={k for k,c in table.items() if c['opcode']==72 and c['strings'] and c['strings'][0]}
    if not actual.issubset(expected): raise ValueError('Replay dialogue missing from manifest')
    return validate(commands,project,strict=strict)

def main():
    from project_config import resolve,read
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--game',default='all');parser.add_argument('--strict',action='store_true');args=parser.parse_args()
    failed=False
    for game in read()['games'] if args.game=='all' else [args.game]:
        try:
            report=audit_project(resolve(game,allow_disabled=True)['project'])
            print(f"{game}: {report['status']}; {report['unit_count']} units, {len(report['changed_units'])} pending")
            failed |= report['status']!='passed'
        except (ValueError,FileNotFoundError,KeyError) as error:
            failed=True;print(f'{game}: ERROR: {error}')
    if failed and args.strict: raise SystemExit(1)
if __name__=='__main__': main()
