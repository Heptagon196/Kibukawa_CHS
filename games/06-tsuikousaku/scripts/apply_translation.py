"""Apply one source-bound sixth-game draft, preserving all other entries."""
import argparse
import collections
import json
import re
import time
import pipeline as p


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('draft')
    args=parser.parse_args()
    draft_path=p.inside(args.draft)
    draft=p.load(draft_path)
    manifest=p.validate_sources()
    config=p.load(p.WORK/'project.json')
    cache_path=p.WORK/'work/cache.json'
    original=cache_path.read_bytes()
    cache=json.loads(original)
    rows={x['text_index']:x for f in cache['files'].values() for x in f['items']}
    sources={x['text_index']:x for x in manifest['entries']}
    p.require(draft['manifest_sha256']==p.sha((p.WORK/'work/manifest.json').read_bytes()),'Manifest changed')
    seen=set()
    for entry in draft['entries']:
        index=entry['id']; target=entry['target']; source=sources[index]; row=rows[index]
        p.require(index not in seen,'Duplicate ID');seen.add(index)
        p.require(not source['excluded'] and row['translation_status'] in (0,1),'Protected or reviewed entry')
        p.require(entry['source']==row['source_text']==source['source_text'],'Source mismatch')
        p.require(row['extra']['location']==source['location'],'Location mismatch')
        if row['translation_status']==1:
            p.require(row['translated_text']==target,'Existing translation differs; review separately')
        retained=config.get('approved_retained_text',{}).get(str(index),{})
        approved=retained.get('source')==entry['source'] and retained.get('target')==target and bool(retained.get('reason'))
        p.require(isinstance(target,str) and (not re.search(r'[ぁ-ゖァ-ヺｦ-ﾟ]',target) or approved),'Invalid target or unapproved kana')
        p.require('\x00' not in target,'NUL character')
        if source['location']['kind']=='script':
            p.require(not any(c in target for c in '\r\n\t'),'Script control character')
        else:
            p.require('\t' not in target and ('\n' not in target or '\n' in entry['source']),'Unexpected UI control character')
        layout=config.get('approved_layout_text',{}).get(str(index),{})
        p.require(target==target.strip() or (layout.get('source')==entry['source'] and layout.get('target')==target and bool(layout.get('reason'))),'Unexpected outer whitespace')
        if source['location']['kind']=='script':
            p.require(len(target.encode('utf-16-le'))//2<=20,'Conservative buffer limit exceeded: '+str(index))
        if not target:
            p.require(entry.get('empty_reason') and re.fullmatch(r'[\s()（）ｦ-ﾟァ-ヺぁ-ゖ・･ーｰ]+',entry['source']),'Unexplained empty source')
        tokens=lambda s:collections.Counter(re.findall(r'\{\d+(?:[^{}]*)\}|</?[A-Za-z][^>]*>',s))
        p.require(tokens(target)==tokens(entry['source']),'Placeholder mismatch')
        row.update(translated_text=target,translation_status=1,model='Codex')
        row['extra']['translation_batch']=draft_path.stem
        if entry.get('empty_reason'):row['extra']['empty_translation_reason']=entry['empty_reason']
    p.require(seen,'Empty draft')
    p.require(original==cache_path.read_bytes(),'Concurrent cache edit')
    backup=p.WORK/'work/backups'/('cache-'+str(time.time_ns())+'.json')
    backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(original)
    cache['extra']['translation_stage']='draft_in_progress'
    p.save(cache_path,cache)
    for name,group in cache['files'].items():
        done=[x for x in group['items'] if x['translation_status'] in (1,2)]
        if not done:continue
        out=p.inside(p.WORK/'translated_texts'/name);out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text('\n'.join(f'[{x["text_index"]}] {x["translated_text"]}' for x in done),encoding='utf-8')
    p.save(p.WORK/'reports'/('translation-'+draft_path.stem+'.json'),dict(count=len(seen),draft_sha256=p.sha(draft_path.read_bytes()),cache_sha256=p.sha(cache_path.read_bytes()),runtime_tested=False))
    p.status()

if __name__=='__main__':main()
