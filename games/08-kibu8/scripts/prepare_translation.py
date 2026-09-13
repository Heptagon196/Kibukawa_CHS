"""Build tagged eighth-game drafts from the validated VM, preserving source positions."""
import html
import sys
from pathlib import Path
from translation_io import WORK, load, save, digest, plain

SERIES = WORK.parents[1]
sys.path.insert(0, str(SERIES/'engine/adapters/gmode-20050817'))
from vm import parse_bin


def row_markup(row):
    result = []
    text = ''
    color = None
    def flush():
        nonlocal text
        if text:
            result.append('<color=' + str(color) + '>' + html.escape(text, quote=False) + '</color>')
            text = ''
    for i, cell in enumerate(row['cells']):
        next_color = row['colors'][i]
        if color != next_color:
            flush()
            color = next_color
        # FFFF denotes unused glyph slots. Original planes remain in source-replay.json.
        text += cell.replace('\uf8f3', '')
        control = row['controls'][i] if row['controls'] else 0
        if control:
            flush()
            result.append('<ctrl=' + format(control, '02X') + '/>')
    flush()
    return ''.join(result)


def main():
    document_path = WORK/'work/dialogue-tagged.json'
    if document_path.exists():
        raise ValueError('Draft already exists; refusing to overwrite translation')
    units, replay = [], {}
    for path in sorted((WORK/'raw').rglob('*.bin')):
        script = path.parent.name + '/' + path.stem
        parsed = parse_bin(path.read_bytes())
        replay[script] = parsed
        for command in parsed['commands']:
            op = command['opcode']
            if command['rows']:
                source = '<row/>'.join(row_markup(row) for row in command['rows'])
                if plain(source).strip():
                    units.append(dict(id=script+':'+str(command['offset']), script=script,
                        instruction=command['offset'], end=command['end'], opcode=op,
                        kind='dialogue' if op==255 else 'display', source=source, target='', translation_status='pending'))
            for index, arg in enumerate(command['args']):
                visible = op in (5, 8, 80) and arg['type']=='s' or op==17 and index==1
                if visible and arg['value'].strip():
                    units.append(dict(id=script+':'+str(command['offset'])+':arg'+str(index), script=script,
                        instruction=command['offset'], end=command['end'], opcode=op, argument=index,
                        kind={5:'menu_prompt',8:'choice',17:'name',80:'bookmark'}[op],
                        source=html.escape(arg['value'],quote=False),target='',translation_status='pending'))
    save(WORK/'research/source-replay.json', dict(schema=2, scripts=replay))
    document = dict(schema=2, adapter='gmode-20050817', source_digest=digest([{k:v for k,v in u.items() if k not in ('target','translation_status')} for u in units]), units=units)
    save(document_path, document)
    save(WORK/'texts/dialogue-tagged.json', document)
    # Batches never split a scene. Duplicated support scenes remain explicitly located.
    groups = {}
    for unit in units:
        groups.setdefault(unit['script'], []).append(unit)
    batches = []
    current = []
    size = 0
    for scene in groups.values():
        length = sum(len(plain(u['source'])) for u in scene)
        if current and size + length > 19000:
            batches.append(current)
            current, size = [], 0
        current.extend(scene)
        size += length
    if current:
        batches.append(current)
    for n, batch in enumerate(batches, 1):
        save(WORK/'work/batches'/f'{n:02d}.source.json', dict(schema=1, batch=n,
            units=[dict(id=u['id'],kind=u['kind'],source=u['source'],target='') for u in batch]))
    save(WORK/'reports/translation-inventory.json', dict(units=len(units), source_characters=sum(len(plain(u['source'])) for u in units),
         batches=[dict(batch=n,units=len(b),characters=sum(len(plain(u['source'])) for u in b),scenes=list(dict.fromkeys(u['script'] for u in b))) for n,b in enumerate(batches,1)]))
    print(len(units), 'translation units;', len(batches), 'batches')


if __name__ == '__main__':
    main()
