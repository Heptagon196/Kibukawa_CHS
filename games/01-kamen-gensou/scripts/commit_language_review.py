"""Commit the main agent's reviewed language decisions, retaining a full audit trail."""
import pipeline as p
from stage_language_review import main as stage

ROOT=p.WORK/'work/language_review'

def main():
    stage()
    baseline=p.load(ROOT/'baseline_cache.json')
    live=p.load(p.WORK/'work/cache.json')
    decisions=p.load(ROOT/'main_decisions.json')
    staged=p.load(ROOT/'proposal_cache.json')
    original={x['text_index']:x for x in p.items(baseline)}
    target={x['text_index']:x for x in p.items(staged)}
    p.require(live==baseline,'Cache changed after review; rebase decisions before committing')
    notes={x['text_index']:[dict(task=x['task'],reason=x['reason'],group=x['group'])]
           for x in p.load(ROOT/'proposals.json')}
    for change in decisions['overrides']:
        idx=change['text_index']
        p.require(target[idx]['translation_status'] in (1,2),'Protected override')
        target[idx]['translated_text']=change['translated_text']
        notes.setdefault(idx,[]).append(dict(task='main_review',reason=change['reason']))
    # Only these reviewed scn6 continuation slots carry old one-space line indents.
    # Credits, clue layout, separator rows, emoticons and protected blanks are excluded.
    for idx in decisions['chat_indent_indices']:
        item=target[idx]
        p.require(item['source_text'].startswith('\u3000') and item['translated_text'].startswith('\u3000'),
                  f'Unexpected chat indent at {idx}')
        item['translated_text']=item['translated_text'][1:]
        notes.setdefault(idx,[]).append(dict(task='main_review',reason='取消网聊续行的原全角缩进，避免重排后插在中文词组中。'))
    p.validate_cache(staged,p.load(p.WORK/'work/manifest.json'))
    changes=[]
    for idx,before in original.items():
        after=target[idx]
        p.require({k:v for k,v in before.items() if k!='translated_text'}==
                  {k:v for k,v in after.items() if k!='translated_text'},f'Non-text mutation at {idx}')
        if before['translated_text']!=after['translated_text']:
            changes.append(dict(text_index=idx,source_text=before['source_text'],before=before['translated_text'],
                                translated_text=after['translated_text'],review=notes[idx]))
    p.save(ROOT/'final_changes.json',changes)
    p.save(ROOT/'reviewed_cache.json',staged)
    p.apply_batch(ROOT/'final_changes.json')
    p.require(p.load(p.WORK/'work/cache.json')==staged,'Committed cache differs from reviewed cache')
    for group,f in staged['files'].items():
        rows=[x for x in f['items'] if x['translation_status'] in (1,2)]
        if not rows: continue
        dest=p.inside(p.WORK/'translated_texts'/group);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text('\n'.join(f'[{x["text_index"]}] {x["translated_text"]}' for x in rows),encoding='utf-8')
    report=dict(checked_records=len(p.load(ROOT/'coverage.json')['translated_indices']),
                reviewed_proposal_groups=213,changed_records=len(changes),
                chat_indent_records=len(decisions['chat_indent_indices']),
                source_indices_status_and_protected_records_unchanged=True,
                source_ambiguities_and_decisions=decisions['issue_decisions'],
                changes=changes,game_runtime_tested=False,
                scope='Full contextual Japanese/Chinese review by eight script reviewers plus main UI/name review; all proposed groups reviewed by main agent. Not a guarantee of error-free translation.',
                baseline_sha256=p.sha((ROOT/'baseline_cache.json').read_bytes()),
                final_cache_sha256=p.sha((p.WORK/'work/cache.json').read_bytes()))
    p.save(p.WORK/'reports/language_review.json',report)
    print('Language review committed:',len(changes),'records; full coverage:',report['checked_records'])

if __name__=='__main__': main()
