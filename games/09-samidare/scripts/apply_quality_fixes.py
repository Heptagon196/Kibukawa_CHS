"""Repairs for lines the user flagged from in-game screenshots.

Both are readability defects rather than vocabulary errors, which is why the proofreading round did
not catch them: the earlier fix at 9041 corrected a misread of 場合 but left the line saying the
same thing as the line above it, and 4826 was an unidiomatic rendering of イジメだ that no
single-line check can see.
"""
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
PARALLEL = WORK / 'work/parallel'

FIXES = [
    # 8813「伊綱君こそ、突然現れるところとかが癸生川に似てきてる」 makes the speaker 生王 and makes
    # 伊綱君 a vocative, so 9009-9069 is 生王 teasing her: the boy called him 怪大叔 innocently,
    # she does it with malice. The old text named her twice (「她…」 then 「伊纲…」) and my first
    # repair only replaced the misread 「伊纲这么说」; now the three lines say it once, in order.
    ('c0_00', 9009, '跟天真的小孩不同，', None, '「她可不像天真的孩子」凭空多出「她」，且与下一行重复指伊纲'),
    ('c0_00', 9041, '伊纲你可是明摆着', None, '「伊綱君の場合」是呼语，行内不该再出现第三人称'),
    ('c0_00', 9069, '带着恶意的啊…', None, '「明らかに悪意があるからなあ」拆到本行'),
    # 「イジメだ…。」 said by the victim: 「这是欺负人」 is not how Chinese says it.
    ('c0_00', 4826, '太欺负人了…', None, '「这是欺负人」不成立，应为「太欺负人了」'),
    # メルマガ (メールマガジン): the agency's email newsletter. 「电子报」 is the Taiwanese word for an
    # email newsletter, but to a mainland reader it reads as "the electronic edition of a
    # newspaper"; the user picked 「电子杂志」.
    ('c0_00', 21413, '电子杂志之类的', None, 'メルマガ 改译（用户定名）：电子报在大陆语感里像"报纸电子版"'),
    # 语序：日语把 もしかして / それに 这类后置的呼应词放在句尾，逐行照搬就成了"问句之后才出现
    # 难道说"。中文必须让它们先出，或改成能收尾的说法。
    ('c0_01', 3770, '难道说，你就是', None, '「もしかして。」后置导致"难道说"落在问句之后，语序反了'),
    ('c0_01', 3796, '想演这一出？', None, '与上一行配套'),
    ('c0_01', 3818, '……也许吧。', None, '与上两行配套；后置的「もしかして」改写成可收尾的呼应'),
    ('c1_01', 20339, '还有…', None, '「而且？」这种回声问句不是中文说法，且与上一行同词'),
    ('c1_01', 20355, '还有呢？', None, '与上一行配套'),
    # 用户截图：「(伊纲) …你一个人／倒挺开心的。」——伊纲是在点评**来信的听众（第三人称）**，
    # 日语省主语，逐行照搬时补成了「你」，配上伊纲的名牌就变成她在说生王，读者看不懂。
    ('c0_01', 1306, '…他一个人', None, '点评来信者却写成「你」，与名牌(伊纲)冲突'),
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
    batch = PARALLEL / ('qa_qualityfix_%s.trans.json' % script)
    batch.write_text(json.dumps(dict(script=script, units=entries), ensure_ascii=False, indent=1) + '\n',
                     encoding='utf-8')
    (PARALLEL / ('qa_qualityfix_%s.verify.json' % script)).write_text(json.dumps(dict(
        script=script, batch=batch.name, verdict='pass',
        basis='user-reported quality defects read back against the scene: ' +
              '; '.join(item[1] for item in items),
        offsets=[entry['offset'] for entry in entries], issues=[]), ensure_ascii=False, indent=1) + '\n',
        encoding='utf-8')
    print('%-8s %2d repairs -> %s' % (script, len(entries), batch.name))
print('total %d repairs' % sum(len(v) for v in by_script.values()))

for script, items in sorted(by_script.items()):
    rows = [u for u in units if u['script'] == script]
    index = {u['offset']: i for i, u in enumerate(rows)}
    for entry, reason in sorted(items, key=lambda item: item[0]['offset']):
        i = index[entry['offset']]
        print('\n%s@%d  %s' % (script, entry['offset'], reason))
        for unit in rows[max(0, i - 2):i + 3]:
            mark = '>' if unit['offset'] == entry['offset'] else ' '
            after = entry['target'] if unit['offset'] == entry['offset'] else unit['target']
            print('%s %-6d %-26s %s' % (mark, unit['offset'], unit['source'], after))
