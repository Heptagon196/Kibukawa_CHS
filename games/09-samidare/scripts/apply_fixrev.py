"""Apply the post-apply review's repairs.

The review found that this round's write-back copied each QA `recommended_target` without
looking at the neighbouring line, which created four duplications and, at c2_00 6118/6146,
dropped `母として願います` outright. Every entry here is the reviewer's own replacement, and
each is checked against the line it joins to before it is written.

`16394` is deliberately not in the table: the reviewer describes it as a three-line shift
(16348/16370/16394) and only proposes a single line, which would duplicate `我不知道` from
16348. It needs the whole run reworked, so it is left alone rather than half-applied.
"""
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
PARALLEL = WORK / 'work/parallel'

FIXES = [
    ('c2_00', 6090, '至少希望他能', None),
    ('c2_00', 6118, '组建普通而幸福的家庭，', None),
    ('c2_00', 6146, '我作为母亲如此祈愿。', None),
    ('c2_00', 10560, '固定的时间外出', None),
    ('c2_00', 9865, '晓先生自己的', None),
    ('c2_00', 2031, '偶尔回来，', None),
    ('c1_00', 774, '已经', None),
    ('c2_00', 5618, '啊，是慧美小姐', ['啊，是', '慧美小姐']),
    ('c4_01', 7377, '打电话商量一下。', None),
    ('c4_00', 5088, '深爱着绫子。', None),
    ('c4_00', 27212, '不知吃了多少苦，', None),
    ('c0_00', 6611, '令人不适的空气。', None),
    # The highlight was DELETED, not moved: BUNSYOU_F7 resets NowMojiColor, so the colour
    # ends right after the coloured fragment and never reaches the next display line. The
    # clue word therefore has to stay in this line's coloured run, and the following lines
    # must be reworded so the clue is not repeated.
    ('c0_00', 16028, '这孩子该不会离家出走', ['这孩子该不会', '离家出走']),
    ('c0_00', 16067, '跑到这儿', None),
    ('c0_00', 16091, '了吧？', None),
    ('c0_00', 17638, '难道他其实被抛弃', ['难道他其实', '被抛弃']),
    ('c0_00', 17670, '了吗', None),
    ('c0_00', 17694, '…？', None),
    ('c0_00', 15098, '“父母才不会担心我”', None),
    ('c0_00', 15070, '不是还气呼呼地说', None),
    # Multi-line shifts: a single line cannot be fixed alone without breaking the join, so the
    # whole run moves together. 16348 stops stealing わからない from its own line; 10535 gets
    # さて back; 238/269 split 8年ぶり (the interval) from 豪雨らしい (the rain's return).
    ('c0_00', 238, '大约时隔８年的', None),
    ('c0_00', 269, '暴雨似乎又来了。', None),
    ('c2_00', 16348, '很遗憾，我父亲', None),
    ('c2_00', 16370, '现在身在何处，', None),
    ('c2_00', 16394, '我也不知道。', None),
    ('c0_00', 10485, '…要想套出他', None),
    ('c0_00', 10509, '口袋里装的东西，', None),
    ('c0_00', 10535, '该怎么做呢…', None),
    # Second-round review: 「…时」 and 「当时」 point at the same moment across the join.
    ('c0_00', 12259, '是怎样的', None),
    # Second-round rest review. 89's own line had to keep ゆっくりと, so the phrase it now
    # duplicates is moved out of the two lines BEFORE it instead of reverting 89 (reverting
    # would leave 89 saying nothing of its own source).
    ('c1_00', 35, '随后，男人', None),
    ('c1_00', 63, '把八年前发生的事', None),
    ('c2_00', 17250, '她刚才的话里，有假', ['她刚才的话里，', '有假']),
    ('c2_00', 17291, '也说不定。', None),
    ('c2_00', 16715, '自信，以及坚定', None),
    # Third-round c4 review. 5055 and 18657 are regressions caused by applying recommendations
    # that were written against an older snapshot: round 1's advice for 5055 assumed 5088 still
    # read 「着绫子。」, and the advice for 18657 read badly beside 18622 「浪迹全国的漂泊者」.
    ('c4_00', 5055, '…即便如此，我打心底', None),
    ('c4_00', 18657, '的父亲……', None),
    ('c4_01', 7638, '很可能就是慧美小姐', None),
    ('c4_01', 10625, '…这笔费用真会到', None),
    ('c4_01', 393, '留了言。', None),
    ('c4_01', 9527, '…没事吗…！？', None),
    # Digit width: the work renders numerals full width (５００万円, １９９６年６月某日, ６～７歳) but
    # these eight lines were the only ones written half width with a space. Full width matches the
    # shipped width and is one character shorter, which the per-line ceiling always welcomes.
    ('c3_00', 356, '能告诉我２５年前', None),
    ('c3_00', 526, '２５年前开始变了', None),
    ('c3_00', 1110, '２５年前，究竟', None),
    ('c3_00', 1908, '…２５年前，我怀上', None),
    ('c3_00', 5746, '２５年…', None),
    ('c3_00', 7883, '２５年前那场事故', None),
    ('c3_00', 9461, '说到２５年前，', None),
    ('c3_00', 9487, '正是２５岁的晓', None),
    # Final round on c0_00. 3635 had dropped 呆れた瞳で僕を entirely and left a dangling 这个;
    # 1575 read the direction backwards; 12235 lost そもそも and doubled 最初 with the next line.
    # 10509's fix keeps the collocation intact: 「套出…东西」 does not work, so the pocket is the
    # topic and the asking is the predicate, which also keeps the two 要 apart.
    ('c0_00', 3635, '…然后，用无语的眼神', None),
    ('c0_00', 1575, '走到了。', None),
    ('c0_00', 12235, '说起，发现这孩子时', None),
    ('c0_00', 10485, '…他口袋里的东西', None),
    ('c0_00', 10509, '要想套出话来，', None),
    # The other half of the 18657 duplication: this line had already written 「父親」, which the
    # source only puts in 18657, so removing it from 18657 alone left the repeat in place.
    ('c4_00', 18596, '有时，又是', None),
    # 15046 already opens the 「不是…吗」 frame, so this line must not open a second one.
    ('c0_00', 15070, '还气呼呼地说', None),
    # c3_00 9487 is narration, and this work's narration always says 晓先生; only 慧美 addressing
    # him directly drops the honorific. 正是 had no source basis and collided with the next line.
    ('c3_00', 9487, '２５岁的晓先生', None),
    # Two c4_00 leftovers from the second final round. 22349 is a dependency break of the kind
    # fixed elsewhere (「请」 waits for its verb on the next line), and 26108 had dropped the
    # adversative ですが entirely.
    ('c4_00', 22349, '不必顾虑，抓住她', None),
    ('c4_00', 26108, '但是…', None),
    # 22373's own text is 裁いてください (deal with her), but it was carrying 捕まえて's verb from
    # 22349, so the two lines have to be separated: the verb goes home and this line says its own.
    ('c4_00', 22373, '请处置她，', None),
    # 3635's repair introduced 无语 twice in one sentence (3635 and 3679); 3679 also lacked the
    # いったい the three lines never carried, and 3705 has to lose 孩子 with it. 1474's 「往…」
    # plus 1575's 「走到了」 mixed a direction preposition with an arrival verb.
    ('c0_00', 3679, '看着我的这孩子到底', None),
    ('c0_00', 3705, '是谁？', None),
    ('c0_00', 1474, '鞠滨台这里的', None),
    # The other half of 9487's honorific: 9535 opened with 先生, so the pair read 晓先生先生.
    # Keeping the honorific on 9487 (narration uses it) and dropping the carried-over one here.
    ('c3_00', 9535, '出生那年…', None),
    # 552 read 「个人…」, a fragment carried over from 646's 「这只是我个人的」; its own source is
    # いうことなので (because it is said so), which the two lines above are still waiting for.
    ('c3_00', 552, '听说是这样，', None),
]

# The table is hand-maintained and the same offset can be listed in two rounds. A duplicate
# currently makes the write-back refuse the WHOLE batch (validate rejects a repeated offset), so
# the later entry wins here and the drop is reported, instead of failing much later and quietly
# leaving every other repair unapplied.
_deduped = {}
for _item in FIXES:
    _key = (_item[0], _item[1])
    if _key in _deduped and _deduped[_key][2] != _item[2]:
        print('NOTE %s@%d listed twice; keeping the later %r (dropping %r)'
              % (_item[0], _item[1], _item[2], _deduped[_key][2]))
    _deduped[_key] = _item
FIXES = list(_deduped.values())

units = json.loads((WORK / 'work/dialogue-tagged.json').read_text(encoding='utf-8'))['units']
draft = {(u['script'], u['offset']): u for u in units}
emphasis = {(l['script'], l['offset']): l['runs']
            for l in json.loads((WORK / 'work/emphasis.json').read_text(encoding='utf-8'))['lines']}

by_script = {}
for script, offset, target, runs in FIXES:
    unit = draft.get((script, offset))
    if unit is None:
        print('SKIP unknown %s@%d' % (script, offset))
        continue
    limit = unit['limit'] or (11 if unit['kind'] == 'choice' else 7)
    if len(target) > limit:
        print('SKIP over limit %s@%d %r' % (script, offset, target))
        continue
    if (script, offset) in emphasis:
        if not runs or ''.join(runs) != target or len(runs) != len(emphasis[(script, offset)]):
            print('SKIP bad colour split %s@%d' % (script, offset))
            continue
    entry = dict(offset=offset, target=target, **({'runs': runs} if runs else {}))
    by_script.setdefault(script, []).append(entry)

for script, entries in sorted(by_script.items()):
    entries.sort(key=lambda item: item['offset'])
    batch = PARALLEL / ('qa_fixrev_%s.trans.json' % script)
    batch.write_text(json.dumps(dict(script=script, units=entries), ensure_ascii=False, indent=1) + '\n',
                     encoding='utf-8')
    offsets = [e['offset'] for e in entries]
    (PARALLEL / ('qa_fixrev_%s.verify.json' % script)).write_text(json.dumps(dict(
        script=script, batch=batch.name, verdict='pass',
        basis='post-apply review: fixrev_rest.verify.json (independent check of the applied text)',
        offsets=offsets, issues=[]), ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print('%-8s %d repairs -> %s' % (script, len(entries), batch.name))
print('total %d repairs' % sum(len(v) for v in by_script.values()))

# Print every change inside its neighbours. Applying a review's replacement verbatim has three
# times now produced a fresh defect (a passive turned active, an emptied colour run that deleted
# the highlight, and 「直接」 repeated because the next line already began with it), and each was
# only visible by reading the line together with the one it joins to. The preview makes that
# unavoidable instead of optional.
rows_cache = {}
for script, entries in sorted(by_script.items()):
    rows = [u for u in units if u['script'] == script]
    rows_cache[script] = {u['offset']: i for i, u in enumerate(rows)}
    for entry in entries:
        i = rows_cache[script][entry['offset']]
        window = rows[max(0, i - 1):i + 2]
        print('\n%s@%d' % (script, entry['offset']))
        for u in window:
            mark = '>' if u['offset'] == entry['offset'] else ' '
            after = entry['target'] if u['offset'] == entry['offset'] else u['target']
            print('%s %-6d %-26s %s' % (mark, u['offset'], u['source'], after))
