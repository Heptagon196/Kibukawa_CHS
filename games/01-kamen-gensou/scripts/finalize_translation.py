"""Serially commit the main agent's reviewed translation and build isolated resources."""
import collections, os, shutil, sys
from pathlib import Path
import pipeline as p

def main():
    skill=Path.home()/'.codex/skills/ainiee-translate/scripts'
    sys.path.insert(0,str(skill)); sys.dont_write_bytecode=True
    from ainiee_translate import batch,cache_io
    staged=p.load(p.WORK/'work/parallel/merged_cache.json')
    manifest=p.load(p.WORK/'work/manifest.json')
    p.validate_cache(staged,manifest)
    rows=p.items(staged)
    updates=[dict(text_index=x['text_index'],translated_text=x['translated_text']) for x in rows if x['translation_status'] in (1,2)]
    formal=p.WORK/'work/cache.json'
    # Native skill writer creates a timestamped backup before serial commit.
    applied=batch.write_back(str(formal),updates)
    p.require(applied==len(updates),'Incomplete cache writeback')
    actual=p.load(formal); by_id={x['text_index']:x for x in p.items(actual)}
    for x in rows:
        if x['text_index'] in (4541,6717):
            by_id[x['text_index']]['translation_status']=7
            by_id[x['text_index']]['extra']['note']='Pure source layout whitespace; kept unchanged.'
    actual['extra'].update(source_language='Japanese',target_language='Simplified Chinese',translation_completed=True,
                           style_approved=True,translation_review='reports/translation_review_decisions.json')
    p.save(formal,actual); p.validate_cache(actual,manifest)
    p.require(batch.read_batch(cache_io.load_cache(str(formal)),size=1)==[],'Untranslated entries remain')
    for group,f in actual['files'].items():
        final=[x for x in f['items'] if x['translation_status'] in (1,2)]
        if not final: continue
        dest=p.inside(p.WORK/'translated_texts'/group); dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text('\n'.join(f'[{x["text_index"]}] {x["translated_text"]}' for x in final),encoding='utf-8')
    final_out,build_report=p.build(out=p.WORK/'out'/('zh-CN_'+p.stamp()))
    collect=p.load(p.WORK/'reports/translation_collection.json')
    decisions=p.load(p.WORK/'reports/translation_review_decisions.json')
    verify_notes=dict(raw_name_warnings=208,empty_translation_warnings=0,
                      resolved_simplified_or_adjacent=207,
                      manually_resolved=[dict(index=2739,resolution='村崎先生的 occurs in 2742 within the same translated sentence; word order redistribution, no omitted name.')],
                      unresolved=0,
                      scan_stray_latin='ID/RPG/LAN are technical terms distributed across fragments; Tactical/Climax/Snowman/mini preserve wordplay and names.',
                      scan_merges='Two existing X placeholder strings in UI template descriptions; retained as original template text.',
                      remaining_kana='Original name readings, phone spelling もえな, clue words ぼく/ひとろし/お隣/オバキュー/みに, emoticons, and a historical service name.',
                      independent_review='All 6841 agent output records compared with the Japanese original across early, middle and late reviews.')
    p.save(p.WORK/'reports/translation_validation.json',verify_notes)
    summary=dict(source_records=len(rows),translated=collect['translated'],excluded=collect['excluded'],untranslated=0,
                 parallel_translation_tasks=len(collect['tasks']),independent_qa_findings=10,reviewed_index_corrections=21,
                 cache=str(formal),readable_texts=str(p.WORK/'translated_texts'),output=str(final_out),
                 original_game_unchanged=build_report['original_game_unchanged'],runtime_visual_tested=False,
                 font_replaced=False,utf8_decoder_patched=True)
    p.save(p.WORK/'reports/translation_summary.json',summary)
    print(summary)

if __name__=='__main__': main()
