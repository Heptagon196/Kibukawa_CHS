"""Finalize the reviewed first draft without touching source data or game files."""
import time

import pipeline as p
import translation_batches as batches


def main():
    cache_path = p.WORK/'work/cache.json'
    cache = p.load(cache_path)
    rows = {x['text_index']: x for group in cache['files'].values() for x in group['items']}
    draft_path = batches.DRAFTS/'scn3.json'
    draft = p.load(draft_path)
    old = '“……这种小事受到夸奖，'
    revised = '“……为这点小事夸我，'
    p.require(rows[3220]['translated_text'] in (old, revised), 'Later revision exists at 3220; do not overwrite')
    p.require(draft['translations']['3220'] in (old, revised), 'Later draft revision exists at 3220')
    if rows[3220]['translated_text'] != revised or draft['translations']['3220'] != revised:
        p.save(p.WORK/'work/backups'/('cache-before-final-wording-'+str(time.time_ns())+'.json'), cache)
        rows[3220]['translated_text'] = revised
        draft['translations']['3220'] = revised
        p.save(draft_path, draft)
        p.save(cache_path, cache)
    report_path = p.WORK/'reports/first-pass-review.json'
    report = p.load(report_path)
    if not any(x['id'] == 3220 and x['after'] == revised for x in report['changes']):
        report['changes'].append(dict(id=3220, batch='scn3', before=old, after=revised, reason='主控连读修订自然中文'))
        p.save(report_path, report)
    glossary_path = p.WORK/'work/glossary.locked.json'
    glossary = p.load(glossary_path)
    if not any(x['canonical'] == '菜緒' for x in glossary['characters']):
        glossary['characters'].append(dict(canonical='菜緒', render='菜绪', aliases=[], note='第二作后段姓名；保留出现时的叙述知识范围。'))
    extras = [('会長', '董事长'), ('役員', '高管'), ('パスケース', '证件夹'), ('定期', '定期乘车票'),
              ('ニルギリ', '尼尔吉里'), ('捜査中断', '中断调查'), ('場所移動', '移动'), ('見回す', '环顾')]
    known = {x['canonical'] for x in glossary['terms']}
    glossary['terms'] += [dict(canonical=source, render=target) for source, target in extras if source not in known]
    p.save(glossary_path, glossary)
    batches.merge()


if __name__ == '__main__':
    main()
