"""Run the ainiee-translate skill's checks over the ninth work's draft.

The skill ships a glossary *enforcer* (``verify``) and a *discovery* pass (``scan``).
They are written against its own cache format, but every check only needs an item's
``text_index``/``source_text``/``translated_text``/``translation_status``, so the draft is
handed to them directly instead of being round-tripped through that format.

The skill pairs a name with its ``render`` and ``aliases``; for a Japanese source the
name as it appears in the *source* is the glossary's ``canonical``, so it is added to the
aliases here. Without that the enforcer would look for Chinese names inside Japanese
source lines and report nothing at all.
"""
import json
import re
import sys
from pathlib import Path

SKILL = Path(r"C:\Users\hepta\.dsh\skills\ainiee-translate\scripts")
if str(SKILL) not in sys.path:
    sys.path.insert(0, str(SKILL))

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK / 'scripts'))
import pipeline as p

from ainiee_translate import scan, verify


def items():
    draft = p.load(WORK / 'work/dialogue-tagged.json')['units']
    return [dict(text_index=index + 1, script=unit['script'], offset=unit['offset'],
                 source_text=unit['source'], translated_text=unit['target'],
                 translation_status=1 if unit['target'] else 0)
            for index, unit in enumerate(draft)]


def locked():
    """The work's glossary in the shape the skill's checks read.

    The series table is merged in first: it carries the project-locked entries inherited
    from earlier works, including the real-identity renders that only exist there (the
    ninth work's own table has no 音成孝一 entry, yet 音成 must come out as 林居).
    """
    work = p.load(WORK / 'work/glossary.locked.json')
    public = p.load(p.SERIES / 'series/glossary.json')
    characters = []
    seen = set()
    for source in (public, work):
        for entry in source.get('characters') or []:
            canonical = entry.get('canonical')
            if canonical in seen:
                continue
            seen.add(canonical)
            aliases = list(entry.get('aliases') or [])
            for extra in (canonical, entry.get('source')):
                if extra and extra not in aliases:
                    aliases.append(extra)
            characters.append(dict(canonical=canonical, render=entry.get('render'),
                                   aliases=aliases, category=entry.get('category'),
                                   status=entry.get('status'), table=source is work and 'work' or 'series'))
    terms = []
    for source in (public, work):
        terms.extend(source.get('terms') or [])
    return dict(characters=characters, terms=terms,
                non_translate=work.get('non_translate') or [])


def name_render_check(rows, table):
    """The rule the skill's own enforcer cannot express for a Japanese source.

    ``verify`` looks for the *same string* in source and translation, which is right for
    Latin names kept verbatim but wrong here: the source carries 伊綱 and the translation
    伊纲, so every simplified form reads as "not preserved". The rule that actually holds
    in this project is the glossary's own: where a character's ``canonical`` appears in
    the source line, the line's translation must carry that entry's ``render``.

    Two guards keep the result usable, both learned from the first run:

    * a name may legitimately sit on the neighbouring display line, because Chinese word
      order moves it across the hard-wrapped break, so the render is looked for across the
      line and its immediate neighbours;
    * an entry whose canonical is a short run of kana matches inside ordinary words — the
      series glossary's みに fires on 人並みに, 巧みに, ちなみに — so those are skipped.
    """
    kana_only = re.compile(r'^[\u3041-\u309F\u30A0-\u30FF\u30FC]+$')
    pairs = [(entry.get('canonical'), entry.get('render'), entry.get('category'))
             for entry in table['characters']]
    pairs = [(src, dst, category) for src, dst, category in pairs
             if src and dst and src != dst
             and not (kana_only.match(src) and len(src) <= 3)]
    skipped = sorted({entry['canonical'] for entry in table['characters']
                      if entry.get('canonical') and entry.get('render')
                      and entry['canonical'] != entry['render']
                      and kana_only.match(entry['canonical']) and len(entry['canonical']) <= 3})
    if skipped:
        print('   (skipped short kana entries that match inside ordinary words: %s)'
              % ', '.join(skipped))
    by_script = {}
    for row in rows:
        by_script.setdefault(row.get('script'), []).append(row)
    found = []
    for script, script_rows in by_script.items():
        for index, row in enumerate(script_rows):
            if row['translation_status'] != 1:
                continue
            source, target = row['source_text'], row['translated_text'] or ''
            window = ''.join((r['translated_text'] or '')
                             for r in script_rows[max(0, index - 1):index + 2])
            for src, dst, category in pairs:
                if src in source and dst not in window:
                    found.append(dict(kind='render_missing', script=script,
                                      offset=row['offset'], name=src, expected=dst,
                                      category=category, source=source, target=target))
    return found


def show(name, found):
    if isinstance(found, dict):
        for key, value in found.items():
            print('\n== %s.%s == %d finding(s)' % (name, key, len(value or [])))
            for entry in (value or [])[:20]:
                print('   ' + json.dumps(entry, ensure_ascii=False))
        return
    print('\n== %s == %d finding(s)' % (name, len(found)))
    for entry in found[:20]:
        print('   ' + json.dumps(entry, ensure_ascii=False))
    if len(found) > 20:
        print('   ... and %d more' % (len(found) - 20))


def main():
    rows = items()
    table = locked()
    translated = sum(1 for row in rows if row['translation_status'] == 1)
    print('items %d (%d translated), glossary %d characters / %d terms'
          % (len(rows), translated, len(table['characters']), len(table['terms'])))

    report = {}
    sections = [
        ('render_missing', lambda: name_render_check(rows, table)),
        ('verify', lambda: verify.check_items(rows, table)),
        ('discover', lambda: scan.discover_proper_nouns(rows, table)),
        ('terms', lambda: scan.find_untranslated_terms(rows, table)),
        ('strays', lambda: scan.find_stray_latin(rows, table)),
        ('merges', lambda: scan.find_merged_tokens(rows)),
    ]
    for name, run in sections:
        try:
            found = run()
        except Exception as error:                     # a check that cannot run must say so
            print('\n== %s == FAILED: %s: %s' % (name, type(error).__name__, error))
            report[name] = dict(error='%s: %s' % (type(error).__name__, error))
            continue
        report[name] = found
        show(name, found)

    p.save(WORK / 'reports/ainiee-checks.json', report)
    print('\nwrote reports/ainiee-checks.json')


if __name__ == '__main__':
    main()
