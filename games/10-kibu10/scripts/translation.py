"""Authoritative tagged-draft audit and cache export; never approves reviews."""
import argparse
import html
import re
import pipeline as p
from runtime_pack import target_rows, fullwidth

def plain(value):
    return html.unescape(re.sub(r'<[^>]+>', '', value))

def audit():
    doc = p.load(p.WORK/'work/dialogue-tagged.json')
    active = [u for u in doc['units'] if u['active']]
    pending, findings = [], []
    for u in active:
        if not u['target']:
            pending.append(u['id'])
            continue
        if 'argument' in u:
            if re.search(r'<[^>]+>', u['target']):
                raise ValueError('Unexpected tag in argument '+u['id'])
            fullwidth(html.unescape(u['target']))
        else:
            target_rows(u['source'], u['target'])
        text = plain(u['target'])
        if re.search(r'[\u3041-\u3096\u30a1-\u30fa\uff66-\uff9d]', text):
            findings.append(dict(id=u['id'], rule='japanese_candidate', source=u['source'], target=u['target']))
        if any(0xe000 <= ord(c) <= 0xf8ff for c in text):
            findings.append(dict(id=u['id'], rule='private_use_glyph', target=u['target']))
    report = dict(total=len(doc['units']), active=len(active), inactive=len(doc['units'])-len(active),
                  translated=len(active)-len(pending), pending=len(pending), pending_ids=pending,
                  findings=findings, structure_valid=True, runtime_tested=False)
    p.save(p.WORK/'reports/translation-audit.json', report)
    return report

def collect():
    """Rebuild cache from current draft, preserving original manifest identities."""
    doc = p.load(p.WORK/'work/dialogue-tagged.json')
    manifest = p.load(p.WORK/'work/manifest.json')
    cache = p.load(p.WORK/'work/cache.json')
    lookup = {u['id']: u for u in doc['units']}
    files = {}
    for e in manifest['entries']:
        if e['location']['kind'] != 'script':
            continue
        u = lookup[e['location']['unit_id']]
        p.require(e['tagged_source'] == u['source'] and e['excluded'] == (not u['active']), 'Stale cache source')
        group = e['group']
        row = dict(text_index=e['text_index'], source_text=plain(u['source']), translated_text=plain(u['target']),
                   translation_status=7 if not u['active'] else (1 if u['target'] else 0), model='Codex parallel translation and review',
                   extra=dict(location=e['location'], tagged_source=u['source'], tagged_target=u['target'], active=u['active']))
        files.setdefault(group, dict(storage_path=group, encoding='utf-8', file_project_type='Txt', line_ending='\n',items=[],extra={}))['items'].append(row)
    # UI sources are owned by the UI pipeline and refreshed without rewriting its drafts.
    next_index=max((e['text_index'] for e in manifest['entries']),default=0)+1
    for path in sorted((p.WORK/'work').glob('ui-*.zh-CN.json')):
        data = p.load(path)
        if not isinstance(data,dict) or 'entries' not in data: continue
        rows=[]
        for i,e in enumerate(data['entries']):
            excluded = str(e.get('classification','')).startswith('excluded') or e.get('classification') == 'technical_sentinel'
            location=dict(kind='serialized' if 'asset_file' in e else ('csv' if 'key' in e else 'assembly'),
                          file=e.get('asset_file',data.get('source_asset')),catalog=path.name)
            location.update({k:e[k] for k in ('path_id','byte_offset','row','key','token','instruction','method') if k in e})
            rows.append(dict(text_index=next_index, source_text=e.get('source_text',''), translated_text=e.get('target_text',''),
                             translation_status=7 if excluded else (1 if e.get('target_text') else 0), extra=dict(classification=e.get('classification'), location=location)))
            next_index += 1
        files[path.stem+'.txt']=dict(storage_path=path.stem+'.txt',encoding='utf-8',file_project_type='Txt',line_ending='\n',items=rows,extra={})
    cache['files']=files
    cache['extra']=dict(authoritative_draft='work/dialogue-tagged.json',translation_stage='draft',semantic_release_review_complete=False)
    p.save(p.WORK/'work/cache.json',cache)
    return audit()

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['collect','check'])
    parser.add_argument('--complete',action='store_true')
    args=parser.parse_args()
    result=collect() if args.action=='collect' else audit()
    print({k:result[k] for k in ('active','inactive','translated','pending')})
    if args.complete and (result['pending'] or result['findings']):
        raise SystemExit('Missing translations or unresolved audit findings')
