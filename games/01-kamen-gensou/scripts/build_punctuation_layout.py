"""Audit punctuation-only rows and join stranded closing marks where they fit."""
import json
import unicodedata
import pipeline as p
from check_dialogue_width import half_cells

ROOT = p.WORK/'bepinex'

# Reviewed in source context: these are deliberate visual/acting pauses.
RETAIN = {
    ('scn6', 1169): ('：', 'The indented colon continues a vertically arranged player list.'),
    ('scn8', 1578): ('…………。', 'Two punctuation-only rows depict sustained silence while searching a phone.'),
}

def punctuation_only(text):
    value = text.strip()
    return bool(value) and all(unicodedata.category(ch).startswith('P') for ch in value)

def build_punctuation_layout(commands):
    rows = []
    current = None
    def finish():
        nonlocal current
        if current is not None:
            rows.append(current)
            current = None
    script = None
    boundary = None
    for command in commands:
        if command['script'] != script:
            finish(); script = command['script']; boundary = None
        op = command['opcode']
        if op in (71,73,75,76,77,78) or 105 <= op <= 112 or 120 <= op <= 123:
            finish(); boundary = command
            continue
        if current is None:
            current = dict(script=script, boundary=boundary, text='', source='', commands=[])
        current['commands'].append(command)
        if op == 72:
            current['text'] += (command['expected'][0] or '') if command['expected'] else ''
            current['source'] += (command['strings'][0] or '') if command['strings'] else ''
    finish()
    joins = []
    audited = []
    for i, row in enumerate(rows):
        if not punctuation_only(row['text']): continue
        previous = rows[i-1] if i else None
        b = row['boundary']
        item = dict(script=row['script'], text=row['text'], source=row['source'],
                    boundary_opcode=b['opcode'] if b else None, instruction=b['instruction'] if b else None,
                    previous=previous['text'] if previous and previous['script']==row['script'] else '')
        audited.append(item)
        # Restrict this to newline-only commands. Pause/clear semantics remain intact.
        if not (previous and previous['script']==row['script'] and previous['text'] and b and b['opcode']==77
                and previous['commands'][-1]['nextCursor']==b['instruction']):
            item.update(action='retain', reason='Independent utterance, page/pause boundary or nonadjacent text.')
            continue
        merged = previous['text'] + row['text']
        item['merged_half_cells'] = half_cells(merged)
        exception = RETAIN.get((row['script'],b['instruction']))
        if exception:
            p.require(row['text'].strip()==exception[0], 'Reviewed punctuation exception changed; recheck its context')
            item.update(action='retain',reason=exception[1])
            continue
        if half_cells(merged)>24 or len(merged)>20:
            item.update(action='retain',reason='Insufficient space on the previous line.')
            continue
        p.require(not punctuation_only(previous['text']), 'Punctuation-only acting pause needs contextual review')
        p.require(all(c['opcode'] in (72,80,81) for c in row['commands']), 'Dynamic punctuation row needs review')
        item.update(action='join',reason='Stranded punctuation fits the preceding text row.')
        joins.append(dict(script=row['script'], instruction=b['instruction'], nextCursor=b['nextCursor'], before=previous['text'], after=merged))
    conditions = ['(script == '+json.dumps(j['script'])+' && nextCursor == '+str(j['nextCursor'])+')' for j in joins]
    source = '''// Generated from the original command replay and current translations.
namespace Kibu1ZhCN {
    public static class PunctuationLayout {
        public static bool ShouldSuppressNewline(string script, int nextCursor) {
            return ''' + (' ||\n                '.join(conditions) if conditions else 'false') + ''';
        }
    }
}
'''
    p.inside(ROOT/'src/PunctuationLayout.cs').write_text(source, encoding='utf-8-sig')
    report = dict(punctuation_only_rows=len(audited), joined_rows=len(joins), joins=joins, audited_rows=audited,
                  punctuation_scope='Unicode punctuation, including sentence marks, quotes, brackets and ellipses',
                  comma_ending_rows_unchanged=True, text_and_colors_unchanged=True, waits_unchanged=True, script_bytes_unchanged=True)
    p.save(ROOT/'build/punctuation-layout-report.json', report)
    return report
