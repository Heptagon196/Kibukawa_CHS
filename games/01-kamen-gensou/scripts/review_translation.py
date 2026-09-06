"""Record main-agent review decisions, preserving original agent artifacts."""
import pipeline as p
decisions=[]; corrections={}
for name in ('early','middle','late'):
    for issue in p.load(p.WORK/f'work/parallel/qa_{name}.json'):
        for item in issue['suggested']: corrections[item['text_index']]=item['translated_text']
        decisions.append(dict(section=name,indices=issue['indices'],decision='accepted',issue=issue['issue']))
# Preserve the kana contact spelling: matching it to 萌奈 is itself a clue.
corrections[1097]='もえな'; corrections[1113]='もえな'
corrections[1306]='的那位小姐呢……？”'
# Yesterday/today is deliberately general in the original; avoid inventing an event.
corrections[2692]='这才过了一天，'
decisions.append(dict(indices=[2692],decision='adjusted',issue='Keep short elapsed time without inventing an event or adding a specific interview.'))
p.save(p.WORK/'work/parallel/reviewed_corrections.json',[dict(text_index=k,translated_text=v) for k,v in sorted(corrections.items())])
p.save(p.WORK/'reports/translation_review_decisions.json',decisions)
g=p.load(p.WORK/'work/glossary.locked.json')
for c in g['characters']:
    if c['canonical']=='アイビス': c['note']='神秘网游账号。结尾6709–6712由癸生川自认；早期账号显示名仍译伊比斯，不提前揭示。'
g['terms'] += [dict(src='吉川線',dst='吉川线',category='clue'),dict(src='青酸中毒',dst='氰化物中毒',category='evidence'),dict(src='ショック死',dst='休克死亡',category='evidence'),dict(src='ｽｰﾊﾟｰｹﾞｰﾑﾗﾝﾁ',dst='ｽｰﾊﾟｰｹﾞｰﾑﾗﾝﾁ',keep_source=True,category='legacy_service')]
g['non_translate'] += [dict(marker=x,category='clue_or_pronunciation') for x in ['ぼく','ひとろし','もえな','お隣','オバキュー','みに','Tactical','Climax','Snowman']]
g['reviewed_note']='Names and role distinctions reviewed before parallel translation; later full-text QA corrected the Ibis ending note. Kana retained only for original readings, wordplay clues, emoticons and the historical service name.'
p.save(p.WORK/'work/glossary.locked.json',g)
print(f'Recorded {len(corrections)} index corrections across {len(decisions)-1} independent QA findings')
