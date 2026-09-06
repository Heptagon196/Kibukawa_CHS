"""Validate original-row layout of credits and the final title card."""
import pipeline as p
from check_dialogue_width import half_cells

def validate(commands):
    cards=[]
    for start,end,limit in ((6690,7123,5),(7474,7529,9)):
        rows=['']
        def finish():
            if any(rows):
                p.require(len(rows)<=limit,'Fixed card exceeds available rows')
                for row in rows:
                    p.require(len(row)<=20 and half_cells(row)<=20,'Fixed card row too wide: '+row)
                cards.append(list(rows))
        for c in commands:
            if c['script']!='scn11' or not start<=c['instruction']<=end:continue
            if c['opcode'] in (73,75):finish();rows=['']
            elif c['opcode']==77:rows.append('')
            elif c['opcode']==72:rows[-1]+=c['expected'][0] or ''
        finish()
    p.require(len(cards)==10,'Expected nine credits cards and one final title card')
    report=dict(cards=cards,card_count=len(cards),width_limit_half_cells=20,original_linebreaks_preserved=True)
    p.save(p.WORK/'reports/fixed_cards.json',report)
    return report
