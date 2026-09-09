"""Author-reviewed experimental puzzle rewrite. Run once on checkpoint 550918d.
Does not install, launch, change source instructions, or approve click baselines.
"""
import json
import sys
import pipeline as p
p.require(not (p.WORK/'work/dialogue-tagged.json').exists(), 'Legacy untagged materialization is disabled. Edit work/dialogue-tagged.json and run tagged_dialogue.py import.')
from review_units import current
sys.path.insert(0, str(p.SERIES / 'tools'))
from click_boundaries import units

# Whole click units, authored as dialogue, not translation annotations.
REWRITES = {
3875: '那么，遗体上刻的数字，应该就是25！',
3957: '“……确认过了，遗体上刻下的数字，确实是25。”',
3967: '“意思就是，还剩25……',
3969: '如果下一个代表25的人被杀……数字就会归零。',
4168: '但松井小姐是25的话，就再也不会错了。”',
4175: '“先从200开始，看看相邻两个数字之间，分别减少了多少。”',
4182: '这些差值，跟名字有关系？！”',
4185: '每次减少的数，都对应那个人的姓或名。想想手机上的字母。”',
4199: '各自对应差值的，到底是姓还是名吧。”',
4203: '“第一位，田中广美。差值是37，对应的是……”',
4208: '“第二位，内野玛雅。差值是19，对应的是……”',
4213: '“第三位，楢原康司。楢念‘由’，差值是48……”',
4218: '“第四位，夏目政隆。差值是29，对应的是……”',
4223: '“最后，松井爱香。差值是42，对应的是……”',
4232: '广美，',
4235: '夏目，',
4236: '松井……',
4237: '这些部分的全拼，都能按同一条规则，变成刚才的差值。”',
4252: '似乎是从200开始，依次减去每个人所代表的数。”',
4260: '“从200开始？',
4262: '“田中广美身上刻的是163。',
4265: '200减去163，是37……',
4271: '也就是说，广美的全拼GUANGMEI，所代表的数是37。',
4278: '接下来，内野玛雅是144……',
4282: '用163减去144，得到的19，就是MAYA所代表的数，对吗？”',
4291: '……同样算下来，YOUYUAN是48，',
4295: 'XIAMU是29，',
4298: 'SONGJING是42……',
4304: '选出的姓或名，要换成完整的拼音啊……”',
4306: '“关键就在于字母。',
4337: '就是手机九键拼音输入时，字母所在的按键。',
4340: '不计声调，每个字母都按一次，把键上的数字相加……',
4343: '就是名字的数。重复字母也要重复算。”',
4348: '您刚才说还剩25，原来是这个意思。',
4357: '姓或名的全拼，按键数字之和是25的人，就有危险。”',
4401: '先求相邻数字的差，再看姓名的全拼。',
4403: '对照九键拼音上每个字母所在的键，把数字加起来试试。”',
4965: '在尚未遇害的人里，姓或名的全拼按键数字之和是25的，',
4990: '原来如此，YUAN是9、8、2、6，相加确实是25。',
5184: '再找名字合计为25的原问问吧。',
6209: '西野的全拼，是XIYE，',
6216: '9加4加9加3……',
6218: '啊，是25！',
7095: '【发件人】amiami【主题】给床子亲【正文】我在桥町的这里，快来哦(⌒▽⌒「９８２２」',
7106: '“９８２２……？',
7113: '发到手机里的，９８２２……”',
7121: '每个数字，都代表九键拼音上同一键里的一个字母。”',
7125: '也就是说，这四个字母连起来，是一个地点的拼音。”',
7130: '“没错。',
7131: '从选项里找出对应的字母……”',
7132: '第一个数字，９是……',
7143: '８是……',
7153: '２是……',
7163: '２是……',
7207: '啊，YUBA，就是鱼吧！！',
7211: '“可是，这附近有叫鱼吧的地方吗……？”',
7213: '“呵呵，就是那家热带鱼店啦，大家都叫它鱼吧！',
}

# Fixed runtime slots: keep original choice IDs/branches, changing their labels.
# Original successful indices: name quiz [0,1,0,1,1], opening [4,1,4,6].
SLOTS = {
4206:'广美',4207:'田中',4221:'政隆',4222:'夏目',4227:'爱香',4228:'松井',
4310:'GUANGMEI＝37',4311:'MAYA＝19',4312:'YOUYUAN＝48',4313:'XIAMU＝29',4314:'SONGJING＝42',
4326:'九键拼音输入',4327:'字母表中的序号',8287:'鱼吧',
}
LETTER_OPTIONS = ['DFHLYNOP', 'EUHJKMRS', 'DEGHBKLM', 'DEGHJKAL']
for options, menu, echo in zip(LETTER_OPTIONS, [7135,7145,7155,7165], [7174,7182,7190,7198]):
    for j, letter in enumerate(options):
        SLOTS[menu+j] = letter
        SLOTS[echo+j] = letter
for ids in [[1416,1419,1422,1425],[2880,2883,2886,2889],[4412,4415,4418,4421]]:
    for i, text in zip(ids, ['①田中广美…１６３','②内野玛雅…１４４','③楢原康司…９６','④夏目政隆…６７']):
        SLOTS[i] = text
SLOTS[4424] = '⑤松井爱香…２５'

def main():
    commands, lookup = current()
    cache = p.load(p.WORK/'work/cache.json')
    rows = {r['text_index']:r for f in cache['files'].values() for r in f['items']}
    p.require(not rows[4203]['extra'].get('pinyin_experiment'), 'Experiment already applied')
    before = {i:r['translated_text'] for i,r in rows.items()}
    seen = set()
    for u in units(commands):
        ids = [lookup[(u['script'],i)]['text_index'] for i in u['instructions'] if (u['script'],i) in lookup]
        if not ids: continue
        target = REWRITES.get(ids[0], u['target']).replace('滨川','西野')
        if ids[0] in REWRITES: seen.add(ids[0])
        if target == u['target']: continue
        # Keep originally empty reading lines empty. Preserve single-click text.
        active = [i for i in ids if before[i]]
        p.require(len(active) <= len(target) <= len(active)*20, 'Unit capacity '+str(ids))
        pos = 0
        weights = [len(before[i]) for i in active]
        total = sum(weights); acc = 0
        for j,i in enumerate(active):
            acc += weights[j]
            end = len(target) if j == len(active)-1 else max(pos+1,len(target)-20*(len(active)-j-1),min(round(len(target)*acc/total),pos+20,len(target)-(len(active)-j-1)))
            rows[i]['translated_text'] = target[pos:end]; pos=end
    p.require(seen == set(REWRITES), 'Unmatched rewrite unit')
    for i,r in rows.items():
        if r['translation_status'] != 7:
            r['translated_text'] = r['translated_text'].replace('滨川','西野')
    for i,t in SLOTS.items(): rows[i]['translated_text'] = t
    changes=[]
    for i,r in rows.items():
        if r['translated_text'] != before[i]:
            r['extra']['pinyin_experiment'] = 'Chinese nine-key adaptation; original source and branch IDs retained.'
            changes.append(dict(id=i,before=before[i],after=r['translated_text']))
    p.save(p.WORK/'work/cache.json',cache)
    p.save(p.WORK/'reports/pinyin-changes.json',changes)
    print('Changed',len(changes),'slots; click review still required.')

if __name__ == '__main__': main()
