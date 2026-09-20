"""Direct-container variant of the eighth-game display compiler.

Only routing, original-table decoding and subtitle opcode differ. The KBZH
codec and tagged row/segment semantics remain the shared implementations.
"""
import base64
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import struct
from vm import parse_bin

_path = Path(__file__).resolve().parents[1] / 'gmode-20050817/runtime_pack.py'
_spec = importlib.util.spec_from_file_location('_eighth_runtime_pack', _path)
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
target_rows = base.target_rows
plain_segments = base.plain_segments
fullwidth = base.fullwidth
make_translation_pack = base.make_translation_pack
encode_translation_pack = base.encode_translation_pack


def codec_for(game):
    doc = json.loads((Path(game)/'research/kibu10-assembly.json').read_text(encoding='utf-8-sig'))
    return struct.unpack('<65537H', base64.b64decode(doc['codec_base64']))


def compile_pack(game, smoke=False):
    game = Path(game)
    from pipeline import row_markup
    document = json.loads((game/'work/dialogue-tagged.json').read_text(encoding='utf-8-sig'))
    inventory = json.loads((game/'research/container-inventory.json').read_text(encoding='utf-8-sig'))
    active = {x['script'] for x in inventory if x['active']}
    groups = {}
    for unit in document['units']:
        if unit['active'] != (unit['script'] in active):
            raise ValueError('Active routing changed: '+unit['id'])
        if unit['active']:
            groups.setdefault(unit['script'], []).append(unit)
    codec = codec_for(game)
    scripts, hashes = [], {}
    report = dict(units=0, inactive_units=sum(not u['active'] for u in document['units']),
                  displays=0, strings=0, rows=0, ruby_rows=0, ruby_groups=0, scripts=[],
                  smoke=smoke, missing_targets=[], ruby_policy='Disable original ruby on translated rows; metadata retained.')
    for item in inventory:
        name = item['script']
        raw = (game/'raw'/(name+'.bin')).read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('Raw scenario changed: '+name)
        parsed = parse_bin(raw, codec)
        digest = hashlib.sha256(raw[parsed['script_offset']:]).digest()
        if name not in active:
            continue
        commands = {c['offset']: c for c in parsed['commands']}
        record = dict(hash=digest, displays=[], strings=[])
        for unit in groups.pop(name, []):
            c = commands[unit['instruction']]
            if c['opcode'] != unit['opcode'] or c['end'] != unit['end']:
                raise ValueError('Stale command: '+unit['id'])
            target = unit['target']
            if not target:
                report['missing_targets'].append(unit['id'])
                if not smoke:
                    raise ValueError('Missing target: '+unit['id'])
                target = unit['source']
            if 'argument' in unit:
                index = unit['argument']
                arg = c['args'][index]
                if not (c['opcode'] == 8 and index == 0 or c['opcode'] in (17,73) and index == 1):
                    raise ValueError('Non-display argument: '+unit['id'])
                if html.escape(arg['value'], quote=False) != unit['source']:
                    raise ValueError('Stale string: '+unit['id'])
                record['strings'].append(dict(offset=arg['offset'], opcode=c['opcode'], source=arg['value'], target=fullwidth(html.unescape(target))))
            else:
                source = '<row/>'.join(row_markup(r) for r in c['rows'])
                if source != unit['source']:
                    raise ValueError('Stale display: '+unit['id'])
                rows = target_rows(source, target)
                segments = plain_segments(source, target)
                if len(rows) != len(c['rows']):
                    raise ValueError('Row count changed: '+unit['id'])
                for row, original, spans in zip(rows, c['rows'], segments):
                    if [v for v in row['controls'] if v] != [v for v in original['controls'] if v]:
                        raise ValueError('Control events changed: '+unit['id'])
                    row.update(source=original['text'], segments=spans,
                               ruby=dict(indices=original['ruby_indices'], groups=original['rubies'], cells=original['cells']))
                    report['ruby_rows'] += bool(original['rubies'])
                    report['ruby_groups'] += len(original['rubies'])
                base.normalize_added_quote_colors(rows)
                record['displays'].append(dict(offset=c['offset'], opcode=c['opcode'], rows=rows))
                report['rows'] += len(rows)
            report['units'] += 1
        report['displays'] += len(record['displays'])
        report['strings'] += len(record['strings'])
        report['scripts'].append(dict(name=name, sha256=digest.hex(), displays=len(record['displays']), strings=len(record['strings'])))
        if digest in hashes:
            if hashes[digest] != record:
                raise ValueError('Conflicting aliases: '+name)
        else:
            hashes[digest] = record
            scripts.append(record)
    if groups:
        raise ValueError('Missing raw scenarios: '+repr(list(groups)))
    report.update(unique_scripts=len(scripts), packed_displays=sum(len(s['displays']) for s in scripts),
                  packed_strings=sum(len(s['strings']) for s in scripts),
                  max_row_slots=max(len(r['text']) for s in scripts for d in s['displays'] for r in d['rows']))
    return scripts, report
