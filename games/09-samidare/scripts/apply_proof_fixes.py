"""Apply the repairs the full proofreading scan produced.

Every entry was read back against the live draft before it was written here: the reviewer's
`recommended_target` is never copied blindly, because a recommendation is written against one
line and the display lines are hard-wrapped, so a line that reads better alone can duplicate its
neighbour or leave it dangling. The join preview at the end prints previous / this / next for
exactly that reason.

Round attribution (each report lives in work/qa_full/proof/):
  A shape       the c3_00 half-width-numeral batch left its c3_01 twins wearing an ASCII space
  B meaning     mistranslations, wrong referents, a locked term used with a different render
  C omission    a content word dropped from the line and its neighbours
  D addition    information the source and its neighbours do not carry
  E shift       content moved wholesale across a display line
"""
import json
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
PARALLEL = WORK / 'work/parallel'
PROOF = WORK / 'work/qa_full/proof'

# (script, offset, target, runs, reason, source report)
FIXES = [
    # --- A. shape: an ASCII space inside a full-width numeral -------------------------------
    # The eight c3_00 lines written "25 年前" were converted to full width in an earlier round;
    # c3_01's five twins were never touched, so they still carry U+0020 between the digits and
    # the counter, which the game draws as a visible gap.
    ('c3_01', 11308, '可５００万这种巨款', None, 'ASCII 空格夹在全角数字与量词之间', 'probe:_probe_context'),
    ('c3_01', 13946, '５００万已经', None, '同上', 'probe:_probe_context'),
    ('c3_01', 14048, '５００万已经', None, '同上', 'probe:_probe_context'),
    ('c3_01', 15577, '７０岁的男性。', None, '同上', 'probe:_probe_context'),
    ('c3_01', 15663, '５０多年。', None, '同上', 'probe:_probe_context'),

    # --- B. meaning wrong -------------------------------------------------------------------
    # 場合 read as 言う: 9009「無邪気な子供と違って」/9041「伊綱君の場合、明らかに」/9069
    # 「悪意があるからなあ」 is a contrast, and 「这么说」 turned it into reported speech.
    ('c0_00', 9041, '伊纲就不同了，', None, '「場合」误作「言う」', 'proof_c0_00_0.report.json'),
    # いづみ is the reading of 泉: the scene guesses the name from the kana and the payoff is
    # 4211「…螻川内泉、か…」, which 「伊兹米」 cannot be connected to. The colour run lands on the
    # guessed name, so putting 泉 there also restores the highlight's content.
    ('c5_00', 4148, '…是泉吧？', ['…', '是泉吧？'], '假名推理链：いづみ＝泉', 'proof_c5_00_0.report.json'),
    # 「とことんお願いできますか」 asks a favour; 「查到底吗？」 moved とことん onto the depth of
    # the investigation and turned the request into a question about scope.
    ('c3_00', 19450, '事到如今，我就彻底', None, '「とことん」挂错，请求被译成询问', 'proof_c3_00_2.report.json'),
    ('c3_00', 19478, '拜托你们了。', None, '「お願いできますか」是请求，非「查到底」', 'proof_c3_00_2.report.json'),
    # 「その事情」 is the family's money trouble, not housework; every other 「家の事情」 in the
    # work is 「家里的事」.
    ('c2_01', 8253, '只是最近受那件事', None, '「その事情」所指被换成「家事」', 'proof_c2_01_1.report.json'),
    # 少し is "a little"; 「颇为」 turns a small surprise into a large one.
    ('c1_00', 8445, '超过二十岁，我有些', None, '「少し」被放大成「颇为」', 'proof_c1_00_1.report.json'),
    # 「…帰って来ませんでしたが…。」 trailing adversative; 「就是了」 closes instead of opening.
    ('c2_00', 14090, '不过……', None, '「が…」逆接被译成收束', 'proof_c2_00_1.report.json'),
    # 「２階ですし」 adds a reason; 「又在二楼」 can only be read as "again".
    ('c2_00', 10720, '而且这里在二楼……', ['而且这里在', '二楼……'], '「し」表并列理由，「又」误', 'proof_c2_00_1.report.json'),
    # The series table locks 場所移動 -> 移动; this menu label alone said 移动地点, and c3_01:529
    # renders the same label as 移动.
    ('c3_00', 995, '移动', None, '锁定术语「場所移動」＝移动', 'proof_c3_00_0.report.json'),
    # 裏社会 is 地下世界 in the same scene (c3_01:15315) and in c4_00:15690; 黑道 reads as the
    # organised underworld, which the wandering con man in this scene is not.
    ('c3_01', 17720, '也就是说，地下世界里', None, '「裏社会」与同场别处译法不一致', 'proof_c3_01_1.report.json'),
    # 543「いやあ、旦那さんには」 has no time word, and 589 already opens with 「当年」: the two
    # adjacent lines said it twice.
    ('c5_00', 543, '哎呀，您丈夫', None, '相邻两行连出两次「当年」', 'proof_c5_00_0.report.json'),
    # いつ来ても満席だということはない denies the universal claim (not always full); 「从来不会」
    # asserts the opposite universal.
    ('c2_01', 8791, '这里并非每次都', None, '否定辖域被加强成「从未」', 'proof_c2_01_1.report.json'),
    # なんですか is "what", not なんで "why".
    ('c0_01', 1573, '咦？什么？', None, '「なんですか」读成「なんで」', 'proof_c0_01_0.report.json'),
    # それ refers to the matter, not to the grandmother the previous line named.
    ('c1_00', 12661, '跟那个无关。', None, '指代由事变成人', 'proof_c1_00_1.report.json'),
    # 「模様」 is the news anchor's hedge; the line stated it as fact.
    ('c4_01', 15126, '疑似已经身亡。', None, '推测「模様」被译成断定', 'proof_c4_01_1.report.json'),
    # 「まだ３ヶ月と、日が浅いということ。」 had 浅い pulled up into 8528, leaving 8559 with only
    # the nominaliser ("这一点"), so 8559 no longer carried its own content word. 浅い goes home and
    # 8528 keeps 「日」, which is also the word the source colours there.
    ('c2_00', 8528, '才三个月，日子', ['才三个月，', '日子'], '「浅い」被整块挪到本行，8559 只剩「こと」', 'proof_c2_00_0.report.json'),
    ('c2_00', 8559, '尚浅。', None, '本行的「浅い」落地（与 8528 配套）', 'proof_c2_00_0.report.json'),
    # 「すでに話を聞ける状態か」 asks whether she can talk yet; 「联系上对方了」 states a different
    # fact (and invents the other party) in a line whose own か makes it a question.
    ('c0_00', 18055, '能说话了吗。', None, '「話を聞ける状態か」被译成陈述且行为被换', 'proof_c0_00_1.report.json'),
    # 「このお礼は、改めて…」 has neither 一定 nor 登门.
    ('c0_00', 20271, '改日再好好道谢…', None, '凭空添加「一定」「登门」', 'proof_c0_00_1.report.json'),
    # 「決死の自殺」 carries the desperation; 「她或许是自杀」 drops the modifier.
    ('c4_01', 15865, '她或许是决意自杀…', None, '漏译修饰语「決死の」', 'proof_c4_01_1.report.json'),

    # --- C. omission ------------------------------------------------------------------------
    # 「言われて来た」 — the coming is the point: 癸生川 is deducing that he was talked into
    # making the trip, which is why the next line is 13748「うっ…。」.
    ('c3_00', 13669, '…听人这么说才来的吧', None, '漏译谓语「来た」', 'proof_c3_00_1.report.json'),
    # 不機嫌 is "sullen", and the line only kept 無口.
    ('c1_01', 7156, '他总沉着脸不说话，', None, '漏译「不機嫌」', 'proof_c1_01_0.report.json'),
    # 「言ってたよね？」 is "you told me, right?"; 「对吧？」 drops who said it.
    ('c2_01', 7718, '你说过吧？', None, '漏译「言ってた」', 'proof_c2_01_1.report.json'),
    # 11860/11888: 気持ち had been moved onto the second line and 「どうにか…なる」 was left out
    # entirely, so 「光凭」 had no predicate to lean on.
    ('c4_01', 11860, '偶尔有些事光凭心意', None, '「光凭」缺谓语，成分两行对调', 'proof_c4_01_1.report.json'),
    ('c4_01', 11888, '也能办成…', None, '补回「どうにか なる」', 'proof_c4_01_1.report.json'),
    # 「聞いているようだった」 is a simile: 「聆听」 states it as fact and 1092 has no predicate.
    ('c0_00', 1048, '仿佛聆听着泪水奏出的', None, '比况「ようだった」丢失', 'proof_c0_00_0.report.json'),

    # --- D. addition ------------------------------------------------------------------------
    # 全国を旅して回っている has no frequency word.
    ('c2_00', 13984, '在全国四处旅行，', None, '凭空添加频率「终年」', 'proof_c2_00_1.report.json'),
    # 返済をしないといけない has no suddenness; 実は is "actually".
    ('c4_00', 10959, '我有了必须提前', None, '「実は」被译成「忽然」', 'proof_c4_00_1.report.json'),
    # どう転んでも is "whichever way it turns out"; the line supplied a choice the source lacks.
    ('c4_01', 2145, '不论怎样，', None, '凭空添加「选择」', 'proof_c4_01_0.report.json'),
    # ことがあります closes 「聞いた」; the line said 「听她提过的」, a second 听 in two lines.
    ('c1_01', 6143, '的事了。', None, '「聞いた」在相邻两行译出两次', 'proof_c1_01_0.report.json'),

    # --- E. shift ---------------------------------------------------------------------------
    # 「泣きついている」 belongs to 17945; putting 「哭着说」 on 17895 took the third line's
    # content and left 17945 with nothing of its own.
    ('c1_01', 17895, '她也说，能依靠的', None, '「哭着」被从 17945 提前到本行', 'proof_c1_01_2.report.json'),
    ('c1_01', 17945, '所以哭着来求我…', None, '本行的「泣きついている」落地', 'proof_c1_01_2.report.json'),
    # 「思い詰める」 is brooding to the point of despair, which the next scene's accident turns
    # on; 「钻牛角尖」 is stubbornness about a small thing.
    ('c4_01', 7752, '她或许正想不开，', None, '「思い詰める」程度被削弱', 'proof_c4_01_0.report.json'),
    ('c4_01', 7838, '也说不定。', None, '与 7752 配套', 'proof_c4_01_0.report.json'),
]

# A duplicate offset makes the write-back refuse the whole batch, so the later entry wins loudly.
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
for script, offset, target, runs, reason, report in FIXES:
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
    entry = dict(offset=offset, target=target, **({'runs': runs} if runs else {}))
    by_script.setdefault(script, []).append((entry, reason, report))

for script, items in sorted(by_script.items()):
    entries = [item[0] for item in items]
    entries.sort(key=lambda item: item['offset'])
    batch = PARALLEL / ('qa_prooffix_%s.trans.json' % script)
    batch.write_text(json.dumps(dict(script=script, units=entries), ensure_ascii=False, indent=1) + '\n',
                     encoding='utf-8')
    (PARALLEL / ('qa_prooffix_%s.verify.json' % script)).write_text(json.dumps(dict(
        script=script, batch=batch.name, verdict='pass',
        basis='full-scan proofreading: ' + ', '.join(sorted({item[2] for item in items})),
        offsets=[entry['offset'] for entry in entries], issues=[]), ensure_ascii=False, indent=1) + '\n',
        encoding='utf-8')
    print('%-8s %2d repairs -> %s' % (script, len(entries), batch.name))
print('total %d repairs' % sum(len(v) for v in by_script.values()))

# Every change inside its neighbours. Applying a recommendation verbatim has repeatedly produced
# a fresh defect that was only visible in the join, so the preview is not optional.
for script, items in sorted(by_script.items()):
    rows = [u for u in units if u['script'] == script]
    index = {u['offset']: i for i, u in enumerate(rows)}
    for entry, reason, report in sorted(items, key=lambda item: item[0]['offset']):
        i = index[entry['offset']]
        print('\n%s@%d  [%s]  %s' % (script, entry['offset'], report, reason))
        for unit in rows[max(0, i - 1):i + 2]:
            mark = '>' if unit['offset'] == entry['offset'] else ' '
            after = entry['target'] if unit['offset'] == entry['offset'] else unit['target']
            print('%s %-6d %-26s %s' % (mark, unit['offset'], unit['source'], after))
