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
    """
    pairs = [(entry.get('canonical'), entry.get('render'), entry.get('category'))
             for entry in table['characters']]
    pairs = [(src, dst, category) for src, dst, category in pairs
             if src and dst and src != dst]
    found = []
    for row in rows:
        if row['translation_status'] != 1:
            continue
        source, target = row['source_text'], row['translated_text'] or ''
        for src, dst, category in pairs:
            if src in source and dst not in target:
                found.append(dict(kind='render_missing', script=row['script'],
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
