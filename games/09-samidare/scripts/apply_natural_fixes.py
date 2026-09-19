"""Repairs from the full Chinese-readability round.

The proofreading round judged whether each line means what its source means; this round asked a
second set of readers one different question — does the Chinese read like Chinese — with the two
defects the user photographed as the yardstick ("她可不像天真的孩子 / 伊纲就不同了" naming the same
referent twice, and 「这是欺负人…」 for イジメだ…). Only defects a reader actually trips over are acted
on here; "I would have worded it differently" findings are listed in _natural_round.md instead.

`reason` names the reader's stumble and what the join looks like after the change.
"""
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
PARALLEL = WORK / 'work/parallel'

FIXES = [
    # ---- high ------------------------------------------------------------------------------
    # 「他口袋里的东西／要想套出话来」 made 东西 the subject of 要想.
    ('c0_00', 10485, '…他口袋里装了什么，', None,
     '主语被读成"东西"；改后「…他口袋里装了什么，／要想套出话来，／该怎么做呢…」'),
    # そもそも opens the topic; 「说起，」 alone is a half sentence in Chinese.
    ('c0_00', 12235, '话说，这孩子当初', None, '「说起，」单带逗号不成句，须接话题'),
    ('c0_00', 12259, '被发现时是', None, '「見つけた時は」与上一行配套'),
    ('c0_00', 12283, '什么情况？', None, '与上一行配套'),
    # 「随便插手／别人家的问题」 split verb and object, and 插手 takes 事 not 问题.
    ('c0_00', 16553, '别人家的事，', None, '「插手…问题」搭配不成立'),
    ('c0_00', 16581, '我们不能擅自过问', None, '动词与宾语被硬折行劈开；改后「别人家的事，／我们不能擅自过问／可是…」'),
    # The source has no indirect object: 「という旨を伝える」.
    ('c0_01', 9520, '若无其事地说，', None, '凭空多出「他」，读者要猜是谁'),
    # 「让屋内的状况／难受到了极点」: 难受 cannot take 状况.
    ('c1_00', 1139, '屋里闷得', None, '「状况难受」搭配不成立'),
    ('c1_00', 1167, '让人受不了。', None, '与上一行配套；改后「…屋里闷得／让人受不了。」'),
    # 「父亲对这个家所做的／一切，就是如此／过分。」 never lands on a predicate.
    ('c1_01', 12415, '父亲对这个家的', None, '「一切，就是如此／过分」没有谓语落点'),
    ('c1_01', 12441, '所作所为', None, '与上一行配套'),
    ('c1_01', 12467, '实在太狠了。', None, '与上两行配套'),
    # 「不论…都…」 split after the comma left the line without a predicate.
    ('c1_01', 19019, '不论遇到什么，您母亲', None, '逗号后无谓语；改后「不论遇到什么，您母亲／都会相信自己选定的／人…」'),
    # し adds a supporting reason; 「而且」 after a 承接语 has nothing to add to.
    ('c2_00', 10720, '毕竟这房间在二楼……', ['毕竟这房间在', '二楼……'],
     '「……这么说，而且…」中「而且」悬空'),
    # 出産 is giving birth: in a chapter about a factory, 「与生产有关吧？」 reads as manufacturing.
    ('c3_00', 1221, '与生育有关吧？', None, '选项里的「生产」会被读成"制造"'),
    ('c3_00', 1440, '与生育有关吧？', None, '同一句再现，须与选项一致'),
    ('c3_00', 6601, '如果勉强生育，', None, '「勉强生产」不成话'),
    ('c3_00', 9559, '果然，生育与此大有', ['果然，', '生育与此大有'], '同上，runs 同步'),
    ('c3_00', 9730, '她听到生育二字时', None, '同上'),
    # Two attributives without 的: the line reads as a finished sentence.
    ('c3_01', 5970, '这是一块约两厘米大的', None, '「约两厘米大／经过特殊加工的金属」缺「的」'),
    # 「……但对手／惹错了对手。」 says 对手 twice in two lines.
    ('c4_00', 15664, '不太好惹。', None, '与上一行撞「对手」；改后「……但对手／不太好惹。」'),
    # 「得知」 is not in the source and left the clause without a subject.
    ('c4_00', 22085, '…被遗弃的女儿', None, '「得知」凭空多出且无主语'),
    # 「才只到」 is not a Chinese collocation.
    ('c4_00', 27104, '事情才止步于此。', None, '「才只到」不成话，且「只到这一步」贬义相反'),
    # 「でも…でも」 is concessive; both amounts must stay.
    ('c4_01', 10757, '几百万也好，几千万也好', None, '两个数量名词没有落点'),
    # 「出たという…。」 lost its predicate, so 赔偿金 had nothing to attach to.
    ('c4_01', 16518, '已经发下来了…', None, '谓语「出た」丢失；改后「汽车保险赔偿金／已经发下来了…」'),
    # The split left "非常感谢你们" looking like a finished sentence.
    ('c5_00', 1310, '非常感谢你们，', None, '行末句号使硬折行读成两个残句'),

    # ---- medium ----------------------------------------------------------------------------
    # 「先不说」 needs its object: the work says 先不说这个 elsewhere.
    ('c1_00', 11498, '先不说这个，白鹭洲君，', None, '「先不说，」缺宾语，易读成祈使'),
    # Japanese inverted 「無関心な君が。」 becomes a hanging noun phrase in Chinese.
    ('c1_00', 12236, '你都漠不关心。', None, '「都漠不关心的你。」是没有谓语的名词短语'),
    # 「啊，是慧美小姐／说的是她吧。」 names the same referent twice.
    ('c2_00', 5663, '的事吧。', None, '与上一行撞指称；改后「啊，是慧美小姐／的事吧。」'),
    # 「不让他见自己父母」 makes 自己 bind to 他 — the opposite of the plot point.
    ('c2_00', 8733, '不让他见她的父母。', None, '「自己」被读成晓，与剧情相反'),
    # 「是这样啊。」 right before 「原来是这样…」.
    ('c4_00', 11762, '是啊。', None, '相邻两行同义重复'),
    # 「父亲竟然一直…」 right before 「一直在工作…」.
    ('c4_00', 13062, '父亲竟然那样…', None, '与下一行撞「一直」'),
    # 「留言说」 right after 「留了言。」.
    ('c4_01', 419, '…她说，会在', None, '相邻两次点击各出一次「留言」'),
    # 「决意自杀」 is not a word.
    ('c4_01', 15865, '她或许是下定决心自杀…', None, '「决意自杀」不成词，但須保留「決死の」'),
    # 「她」 has two possible antecedents across the wrap.
    ('c4_01', 15672, '慧美虽被送往医院，', None, '「她」的先行词被「车辆」隔开'),
    # 「这不是很美满吗」 mis-collocates and uses a full stop on a question.
    ('c5_00', 2932, '这不是很幸福吗？', None, '「美满」多指婚姻；问句误用句号'),
    # 系在 is not how Chinese puts 命運を賭ける.
    ('c3_01', 10314, '都赌在这件事上。', None, '「系在」搭配不成立'),
    # 「５００万円」 needs its unit, or readers take it for yuan.
    ('c3_01', 13946, '５００万日元已经', None, '货币单位被吞掉'),
    ('c3_01', 14048, '５００万日元已经', None, '同一句再现'),
    # 「您会下定决心」 leaves the next line's 「也」 without a referent.
    ('c3_00', 686, '您之所以会', None, '「…心に決めたのも」的「也」无所指'),
    # 「很遗憾」 attaches to the wrong subject after a bare noun phrase.
    ('c3_00', 14809, '不巧出门调查去了。', None, '「很遗憾」被挂到白鹭洲君身上'),
    # 動揺 is a false friend: 动摇 is about resolve.
    ('c3_00', 8911, '…她明显慌了。', ['…', '她明显慌了。'], '「动摇」无所指且是假朋友'),
    # 「或许我也该相信母亲」 reads as trusting the mother, not copying her faith.
    ('c1_01', 14076, '或许我也该学母亲，', None, '原文是"像母亲那样相信并等待"'),

    # ---- post-apply review of this round's own repairs --------------------------------------
    # 「让她的父母拿到了／汽车保险赔偿金／已经发下来了…。」 said 出た twice.
    ('c4_01', 16453, '让她的父母拿到了', None, '与下一行重复谓语；「出た」只留一处'),
    ('c4_01', 16518, '…', None, '谓语归上一行后本行只剩という的停顿'),
    # 「哎呀，这不是／这不是很幸福吗？」 said 这不是 twice.
    ('c5_00', 2932, '很好吗？', None, '与上一行行末「哎呀，这不是」撞词'),
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
    batch = PARALLEL / ('qa_natfix_%s.trans.json' % script)
    batch.write_text(json.dumps(dict(script=script, units=entries), ensure_ascii=False, indent=1) + '\n',
                     encoding='utf-8')
    (PARALLEL / ('qa_natfix_%s.verify.json' % script)).write_text(json.dumps(dict(
        script=script, batch=batch.name, verdict='pass',
        basis='full Chinese-readability review (work/qa_full/_natural_round.md): ' +
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
