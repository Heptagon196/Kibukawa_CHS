"""Second-pass repairs: what the post-apply review of this round's own changes found.

The full-scan repairs were written by this side from the proofreaders' findings; this round is the
independent check of those repairs. Only the objections that survive reading the join are acted on
here; the rest are recorded in work/qa_full/_proof_round.md with the reason they were dismissed.
"""
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
PARALLEL = WORK / 'work/parallel'

FIXES = [
    # Review 0: 「而且这里在二楼」 — 「この部屋は」 compressed to 「这里」. The connective is kept (し
    # does list a reason) but the noun is restored.
    ('c2_00', 10720, '而且这房间在二楼……', ['而且这房间在', '二楼……'],
     'fixreview_0: 「この部屋は」被压成「这里」'),
    # Review 1: five of the six 裏社会 / 裏の世界 lines now say 地下世界; this one still said 黑道.
    ('c5_00', 6942, '搭档，连地下世界', None,
     'fixreview_1: 「裏社会」唯一残留的另一种译法'),
    # Read the scene, not the line: 17733「今の推理を、伊綱君に話して確認してみよう」→ 伊纲
    # 「はい、なんですか？」→ this aside → 伊纲's side of a call to the child's family
    # (18111「お子さんが今、うちに」/ 18207「住所は、鞠浜台の…」). 生王 is remarking that she has
    # already got someone on the line. 「話を聞ける状態」 is "in a state where one can be talked
    # with" — the eighth work uses the identical phrase for 「入院中で、話を聞けるような状態じゃねえ」 —
    # and the trailing か is 生王's own aside, not a question put to anyone, so the 「吗」 goes and
    # the direction (聞ける, not 話す) comes right.
    ('c0_00', 18055, '能说上话了。', None,
     '看上下文：伊纲已在通话中，「聞ける」是"能对话"而非"能说话"'),
]

units = json.loads((WORK / 'work/dialogue-tagged.json').read_text(encoding='utf-8'))['units']
draft = {(u['script'], u['offset']): u for u in units}
emphasis = {(l['script'], l['offset']): l['runs']
            for l in json.loads((WORK / 'work/emphasis.json').read_text(encoding='utf-8'))['lines']}

by_script = {}
for script, offset, target, runs, reason in FIXES:
    unit = draft.get((script, offset))
    if unit is None:
        print('SKIP unknown %s@%d' % (script, offset))
        continue
    if unit['target'] == target:
        print('SKIP already in place %s@%d' % (script, offset))
        continue
    limit = unit['limit'] or (11 if unit['kind'] == 'choice' else 7)
    if len(target) > limit:
        print('SKIP over limit %s@%d %r %d > %d' % (script, offset, target, len(target), limit))
        continue
    if (script, offset) in emphasis:
        if not runs or ''.join(runs) != target or len(runs) != len(emphasis[(script, offset)]):
            print('SKIP bad colour split %s@%d' % (script, offset))
            continue
    elif runs:
        print('SKIP runs on a single-colour line %s@%d' % (script, offset))
        continue
    by_script.setdefault(script, []).append(
        (dict(offset=offset, target=target, **({'runs': runs} if runs else {})), reason))

for script, items in sorted(by_script.items()):
    entries = sorted((item[0] for item in items), key=lambda item: item['offset'])
    batch = PARALLEL / ('qa_proofrev_%s.trans.json' % script)
    batch.write_text(json.dumps(dict(script=script, units=entries), ensure_ascii=False, indent=1) + '\n',
                     encoding='utf-8')
    (PARALLEL / ('qa_proofrev_%s.verify.json' % script)).write_text(json.dumps(dict(
        script=script, batch=batch.name, verdict='pass',
        basis='post-apply review of this round\'s own repairs: ' +
              ', '.join(sorted({item[1] for item in items})),
        offsets=[entry['offset'] for entry in entries], issues=[]), ensure_ascii=False, indent=1) + '\n',
        encoding='utf-8')
    print('%-8s %2d revisions -> %s' % (script, len(entries), batch.name))
print('total %d revisions' % sum(len(v) for v in by_script.values()))

for script, items in sorted(by_script.items()):
    rows = [u for u in units if u['script'] == script]
    index = {u['offset']: i for i, u in enumerate(rows)}
    for entry, reason in sorted(items, key=lambda item: item[0]['offset']):
        i = index[entry['offset']]
        print('\n%s@%d  %s' % (script, entry['offset'], reason))
        for unit in rows[max(0, i - 1):i + 2]:
            mark = '>' if unit['offset'] == entry['offset'] else ' '
            after = entry['target'] if unit['offset'] == entry['offset'] else unit['target']
            print('%s %-6d %-26s %s' % (mark, unit['offset'], unit['source'], after))
