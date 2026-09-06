"""Compare click-unit text with a contextually reviewed baseline.

This does not infer fluency from punctuation. Changed units require renewed
source/target review before updating the baseline; builds never refresh it.
"""
import pipeline as p

BASELINE = p.WORK/'work/click_boundaries.reviewed.json'

def units(commands):
    result=[]; pending=[]; script=None
    def flush(end, opcode):
        if pending:
            result.append(dict(script=script, end=end, opcode=opcode,
                instructions=[x['instruction'] for x in pending],
                source=''.join((x['strings'][0] or '') for x in pending),
                target=''.join((x['expected'][0] or '') for x in pending)))
            pending.clear()
    for c in commands:
        if c['script'] != script:
            flush(-1, -1); script=c['script']
        op=c['opcode']
        if op==72: pending.append(c)
        elif op in (71,73,75,76,78,79) or 105<=op<130:
            flush(c['instruction'],op)
    flush(-1,-1)
    return result

def validate(commands):
    current=units(commands)
    reviewed=p.load(BASELINE)['units']
    changes=[]
    old={(x['script'],x['end']):x for x in reviewed}
    for u in current:
        key=(u['script'],u['end'])
        if old.pop(key,None)!=u: changes.append(u)
    report=dict(unit_count=len(current),changed_units=changes,removed_units=list(old.values()),
        scope='Static original click/clear boundaries; semantic review baseline, not a runtime playthrough.')
    p.save(p.WORK/'reports/click_boundaries.json',report)
    p.require(not changes and not old,'Click-unit text changed: review reports/click_boundaries.json against the original before updating the reviewed baseline.')
    return report
