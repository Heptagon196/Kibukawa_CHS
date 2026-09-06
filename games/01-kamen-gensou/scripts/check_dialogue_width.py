"""Validate joined dialogue using the game's half/full-width character cells."""
import pipeline as p

def half_cells(text):
    return sum(1 if 0x20 <= ord(c) <= 0x7e or 0xff66 <= ord(c) <= 0xff9f else 2 for c in text)

def validate(commands, pack):
    translated={(x['script'],x['instruction'],x['slot']):x['index'] for x in pack['scripts']}
    failures=[]; rows=[]; text=''; indices=[]; script=None
    def finish():
        nonlocal text,indices
        if indices:
            row=dict(script=script,indices=list(indices),half_cells=half_cells(text),text=text)
            rows.append(row)
            if row['half_cells'] > 20: failures.append(row)
        text=''; indices=[]
    for command in commands:
        if command['script'] != script: finish(); script=command['script']
        opcode=command['opcode']
        if opcode in (71,73,75,76,77,78) or 105<=opcode<=112 or 120<=opcode<=123: finish()
        if opcode==72:
            text += (command['expected'][0] or '') if command['expected'] else ''
            index=translated.get((script,command['instruction'],0))
            if index is not None: indices.append(index)
    finish()
    report=dict(checked_static_rows=len(rows),limit_half_cells=20,max_half_cells=max((r['half_cells'] for r in rows),default=0),
                overflow_count=len(failures),overflows=failures,
                scope='Historical source rows before runtime reflow; diagnostic only, these rows may be wider than the final layout. Actual body width/line/text conservation checks are in dialogue-reflow-report.json. Target: 20 half-cells, 240px canvas, 16px font, 44px left origin and 36px right gutter.')
    return report

if __name__=='__main__':
    root=p.WORK/'bepinex/build'
    report=validate(p.load(root/'replay.json')['commands'],p.load(root/'plugin/translations.json'))
    p.save(root/'width_report.json',report)
    p.require(report['overflow_count']==0,'Dialogue overflow: '+str(report['overflow_count'])+' rows; '+str(report['overflows'][:2]))
    print('PASS: '+str(report['checked_static_rows'])+' static dialogue rows fit the original character cells')
