"""Repairs from the Chinese word-order round.

The user photographed one instance — `你就是想演／这一出吧？／难道说。` for
`それがやりたかったんじゃないですか？／もしかして。` — where a Japanese afterthought connective was
copied line by line and ended up stranded after the sentence it should introduce. This round asked
independent readers to find that class and its relatives across the whole work: postposed
connectives, sentences broken the wrong way, modifier/head inversions, and question frames landing
after the sentence.

Only the findings with a verified replacement are here; the rest are listed in _word_order_round.md.
"""
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
PARALLEL = WORK / 'work/parallel'

FIXES = [
    # ---- postposed connective / question frame ---------------------------------------------
    # 792: 「莫非」 stood in the middle of the question it frames, after 「那么，这座城…」.
    ('c0_00', 792, '莫非已经污浊到', None, '「莫非」被夹在问句中间；改后「那么，这座城…／莫非已经污浊到／不得不如此哭泣／的地步了吗？」'),
    ('c0_00', 938, '也不说明自己为何', None, '「为何」与其修饰的「那般悲伤」被行界拆散'),
    ('c0_00', 964, '如此悲伤…', None, '与上一行配套'),
    ('c0_01', 9040, '就是一个姓白鹭洲的', None, '「就是一个姓／戴眼镜的青年」被读成"姓戴眼镜"'),
    ('c0_01', 1762, '对吧？', None, '光杆「吧？」落在已收束的句子之后；上一行已说「有位老板」，不能重复'),
    ('c1_01', 5621, '偶尔回来，', None, '行尾句读把状语封成完结句，下一行才降格为状语'),
    ('c3_00', 4382, '是吧。', None, '光杆「吧。」落在「而已」之后'),
    ('c4_00', 137, '…不会吧。', None, '光杆「难道。」不成句'),
    ('c4_00', 19255, '难道说，母亲是骗子……', None, '后置的「もしかして」被照搬到句尾'),
    ('c5_01', 533, '对恋爱变得胆怯了', None, '体标记「了」吊在下一行行首'),
    ('c5_01', 561, '…', None, '与上一行配套'),
    # ---- modifier / head inversion ---------------------------------------------------------
    # (c3_01@2332 「还没有厚到／能让人看清／痕迹的程度」 reads correctly as one sentence across the
    # three lines, and the reviewer's one-line fix actually breaks the join — dropped.)
    ('c4_00', 22956, '不留痕迹地抹掉', ['不留痕迹地', '抹掉'], '把字句宾语已前置，动词后又多出一个「他」(runs 同步)'),
    # ---- verb / object or recipient split --------------------------------------------------
    ('c3_00', 7487, '那件事促成了', None, 'わけですね 的确认框架被搬到句尾后丢失，读成"劝人结婚"'),
    ('c3_00', 7513, '也就是说，你们', None, '与上一行配套'),
    ('c3_00', 7543, '结婚了。', None, '与上两行配套'),
    ('c3_01', 13946, '５００万日元可能', None, '「已经／可能」状语顺序颠倒'),
    ('c3_01', 13968, '已经回不来', None, '与上一行配套'),
    ('c3_01', 14048, '５００万日元可能', None, '同一句再现，同法处理'),
    ('c3_01', 14070, '已经回不来', None, '与上一行配套'),
    ('c1_01', 9476, '才发现', None, '时间状语被插在施事与谓语之间：「不知是谁昨天，」'),
    ('c1_01', 9504, '昨天，不知被谁全部取走', ['昨天，', '不知被谁全部取走'], '与上一行配套 (runs 同步)'),
    ('c1_00', 5326, '别看我这样，', None, '「打扫可是很拿手的」主谓被行界割开'),
    ('c1_00', 5350, '打扫可是很拿手的！', None, '与上一行配套'),
    ('c4_01', 5043, '就什么都别说了，', None, '光杆「…吧？」落在已用句号封死的句子之后'),
    ('c4_01', 5069, '好吗？', None, '与上一行配套'),
    ('c4_01', 2245, '所以…', None, '征询「好吗？」出现在被征询的内容之前'),
    ('c4_01', 2263, '我们分手吧，好吗？', None, '与上一行配套'),
    ('c2_00', 12886, '我和他说过晓正在', None, '行尾「晓正」被读成本作不存在的人名'),

    # ---- post-apply review of this round's own repairs --------------------------------------
    # 7543 is 「そうです。」 = the confirmation, so it must stay 「是的。」; the whole confirmed
    # clause goes on 7513 instead (11 = its ceiling).
    ('c3_00', 7513, '也就是说，你们结婚了。', None, 'review: 拆开会吞掉 7543 的答复'),
    ('c3_00', 7543, '是的。', None, 'review: 恢复对「そうです。」的答复'),
    # 9476 and 9504 are separate clicks, so 何者かによって may not move onto 9504's line.
    ('c1_01', 9476, '没想到，竟然有人', None, 'review: 施事留在本行，不跨点击'),
    ('c1_01', 9504, '昨天，把全部存款取走', ['昨天，', '把全部存款取走'], 'review: 施事回到上一行，色段随之收窄'),
    # 「难道说，母亲是骗子……」 copied 19227's clause verbatim.
    ('c4_00', 19255, '难道说，连母亲也……', None, 'review: 与上一行同一名词短语连出两次'),
]

_deduped = {}
for _item in FIXES:
    _key = (_item[0], _item[1])
    if _key in _deduped and _deduped[_key][2] != _item[2]:
        print('NOTE %s@%d listed twice; keeping the later %r' % (_item[0], _item[1], _item[2]))
    _deduped[_key] = _item
FIXES = list(_deduped.values())

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
            print('SKIP bad colour split %s@%d (emphasis %s)' % (script, offset, emphasis[(script, offset)]))
            continue
    elif runs:
        print('SKIP runs on a single-colour line %s@%d' % (script, offset))
        continue
    by_script.setdefault(script, []).append(
        (dict(offset=offset, target=target, **({'runs': runs} if runs else {})), reason))

for script, items in sorted(by_script.items()):
    entries = sorted((item[0] for item in items), key=lambda item: item['offset'])
    batch = PARALLEL / ('qa_wofix_%s.trans.json' % script)
    batch.write_text(json.dumps(dict(script=script, units=entries), ensure_ascii=False, indent=1) + '\n',
                     encoding='utf-8')
    (PARALLEL / ('qa_wofix_%s.verify.json' % script)).write_text(json.dumps(dict(
        script=script, batch=batch.name, verdict='pass',
        basis='Chinese word-order review (work/qa_full/_word_order_round.md): ' +
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
