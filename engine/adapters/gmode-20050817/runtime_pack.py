"""Compile translated display buffers; never rewrite original VM bytes or offsets."""
import hashlib
import html
import json
from pathlib import Path
import re
import struct
import sys
from vm import parse_bin

sys.path.append(str(Path(__file__).resolve().parents[1] / 'gmode-v2'))
import pack_codec as shared_codec

TAG = re.compile(r'<[^>]+>')


def normalize_added_quote_colors(rows):
    """Keep added outer dialogue punctuation outside source highlighting."""
    if not rows or not rows[0]['text'].startswith('“') or rows[0]['colors'][0] == 0:
        return
    original_quote = rows[0]['source'].startswith(('「', '『', '“', '‘'))
    if original_quote and not rows[0]['text'].startswith('“‘'):
        return
    rows[0]['colors'][0] = 0
    for row in rows:
        close = row['text'].find('”')
        if close >= 0:
            row['colors'][close] = 0
            break

def fullwidth(text):
    result = ''.join(chr(ord(c)+0xfee0) if '!' <= c <= '~' else '\u3000' if c == ' ' else c for c in text)
    if any(ord(c) < 32 or ord(c) > 0xffff or 0xd800 <= ord(c) <= 0xdfff for c in result):
        raise ValueError('Runtime slots require printable BMP characters')
    return result

def target_rows(source, target):
    if TAG.findall(source) != TAG.findall(target):
        raise ValueError('Translated tags differ from source')
    rows = [dict(text='', colors=[], controls=[])]
    color = None
    last_color = 0
    for token in re.split(r'(<[^>]+>)', target):
        row = rows[-1]
        if not token:
            continue
        if token == '<row/>':
            if color is not None: raise ValueError('Unclosed color at row boundary')
            rows.append(dict(text='', colors=[], controls=[]))
        elif token == '</color>':
            if color is None: raise ValueError('Unexpected color close')
            color = None
        elif re.fullmatch(r'<color=\d+>', token):
            if color is not None: raise ValueError('Nested color')
            color = int(token[7:-1])
            last_color = color
            if not 0 <= color <= 255: raise ValueError('Color outside byte range')
        elif re.fullmatch(r'<ctrl=[0-9A-F]{2}/>', token):
            if not row['controls'] or row['controls'][-1]:
                row['text'] += '\u3000'
                row['colors'].append(last_color)
                row['controls'].append(0)
            row['controls'][-1] = int(token[6:8], 16)
        elif token.startswith('<'):
            raise ValueError('Unknown tag '+token)
        else:
            if color is None: raise ValueError('Text outside color')
            text = fullwidth(html.unescape(token))
            row['text'] += text
            row['colors'].extend([color]*len(text))
            row['controls'].extend([0]*len(text))
    if color is not None: raise ValueError('Unclosed color')
    return rows


def plain_segments(source, target):
    """Align plain spans at the original VM's color and control boundaries.

    Formatting is recovered from the original script at runtime. A control with
    no preceding glyph span still gets an empty slot, so consecutive controls
    and deliberately empty translations retain their original event positions.
    """
    if TAG.findall(source) != TAG.findall(target):
        raise ValueError('Translated tags differ from source')
    original = re.split(r'(<[^>]+>)', source)
    translated = re.split(r'(<[^>]+>)', target)
    rows = [[]]
    active = None
    controlled = False
    for src, dst in zip(original, translated):
        if src == '<row/>':
            if active is not None:
                raise ValueError('Unclosed color at row boundary')
            rows.append([])
            controlled = False
        elif re.fullmatch(r'<color=\d+>', src):
            if active is not None:
                raise ValueError('Nested color')
            active = dict(source='', target='')
        elif src == '</color>':
            if active is None:
                raise ValueError('Unexpected color close')
            rows[-1].append(active)
            active = None
            controlled = False
        elif re.fullmatch(r'<ctrl=[0-9A-F]{2}/>', src):
            if active is not None:
                raise ValueError('Control inside color block')
            if not rows[-1] or controlled:
                rows[-1].append(dict(source='', target=''))
            controlled = True
        elif src.startswith('<'):
            raise ValueError('Unknown tag '+src)
        elif src or dst:
            if active is None:
                raise ValueError('Text outside color')
            active['source'] += html.unescape(src)
            active['target'] += fullwidth(html.unescape(dst))
    if active is not None:
        raise ValueError('Unclosed color')
    return rows

def compile_pack(game):
    game = Path(game)
    sys.path.insert(0, str(game/'scripts'))
    from prepare_translation import row_markup
    document = json.loads((game/'work/dialogue-tagged.json').read_text(encoding='utf-8-sig'))
    groups = {}
    for unit in document['units']:
        groups.setdefault(unit['script'], []).append(unit)
    scripts, hashes = [], {}
    report = dict(units=0, displays=0, strings=0, rows=0, ruby_rows=0, ruby_groups=0,
                  ruby_policy='Original Japanese ruby disabled at runtime; original metadata preserved verbatim.', scripts=[])
    for path in sorted((game/'raw').rglob('*.bin')):
        name = path.parent.name+'/'+path.stem
        raw = path.read_bytes()
        parsed = parse_bin(raw)
        digest = hashlib.sha256(raw[parsed['script_offset']:]).digest()
        commands = {c['offset']: c for c in parsed['commands']}
        record = dict(hash=digest, displays=[], strings=[])
        for unit in groups.pop(name, []):
            c = commands[unit['instruction']]
            if c['opcode'] != unit['opcode'] or c['end'] != unit['end']:
                raise ValueError('Stale command '+unit['id'])
            if not unit['target']: raise ValueError('Missing target '+unit['id'])
            if 'argument' in unit:
                arg = c['args'][unit['argument']]
                visible = c['opcode'] in (5,8,80) and arg['type']=='s' or c['opcode']==17 and unit['argument']==1
                if not visible or html.escape(arg['value'], quote=False) != unit['source']:
                    raise ValueError('Stale/non-display argument '+unit['id'])
                record['strings'].append(dict(offset=arg['offset'], opcode=c['opcode'], source=arg['value'], target=fullwidth(html.unescape(unit['target']))))
            else:
                source = '<row/>'.join(row_markup(r) for r in c['rows'])
                if source != unit['source']: raise ValueError('Stale display '+unit['id'])
                rows = target_rows(source, unit['target'])
                segments = plain_segments(source, unit['target'])
                for row, original, spans in zip(rows, c['rows'], segments):
                    if [x for x in row['controls'] if x] != [x for x in original['controls'] if x]:
                        raise ValueError('Control event sequence changed '+unit['id'])
                    row['source'] = original['text']
                    row['segments'] = spans
                    row['ruby'] = dict(indices=original['ruby_indices'], groups=original['rubies'], cells=original['cells'])
                    report['ruby_rows'] += bool(original['rubies'])
                    report['ruby_groups'] += len(original['rubies'])
                normalize_added_quote_colors(rows)
                record['displays'].append(dict(offset=c['offset'], opcode=c['opcode'], rows=rows))
                report['rows'] += len(rows)
            report['units'] += 1
        report['displays'] += len(record['displays'])
        report['strings'] += len(record['strings'])
        report['scripts'].append(dict(name=name, sha256=digest.hex(), displays=len(record['displays']), strings=len(record['strings'])))
        if digest in hashes:
            if hashes[digest] != record: raise ValueError('Conflicting translations for identical Script SHA256: '+name)
        else:
            hashes[digest] = record
            scripts.append(record)
    if groups: raise ValueError('Missing raw scripts: '+str(list(groups)))
    report['unique_scripts'] = len(scripts)
    report['packed_displays'] = sum(len(s['displays']) for s in scripts)
    report['packed_strings'] = sum(len(s['strings']) for s in scripts)
    report['max_row_slots'] = max(len(r['text']) for s in scripts for d in s['displays'] for r in d['rows'])
    return scripts, report

def row_target_markup(row):
    """Lossless row text using compact color runs and inline control events."""
    if len(row['text']) != len(row['colors']) or len(row['text']) != len(row['controls']):
        raise ValueError('Mismatched row text/color/control lengths')
    result, color = [], None
    for glyph, next_color, control in zip(row['text'], row['colors'], row['controls']):
        if not 0 <= next_color <= 255 or not 0 <= control <= 255:
            raise ValueError('Row color/control outside byte range')
        if color != next_color:
            if color is not None:
                result.append('</color>')
            result.append('<color=%d>' % next_color)
            color = next_color
        result.append(html.escape(glyph, quote=False))
        if control:
            result.append('<ctrl=%02X/>' % control)
    if color is not None:
        result.append('</color>')
    return ''.join(result)


def make_translation_pack(scripts, assembly_hash, scratch_hash, ui, localization=None, literals=None,
                          script_names=None):
    """Export the series schema-1 pack with short names and plain text slots.

    Display slots enumerate spans across all rows of a display. Slot -1 denotes
    a direct string argument. Colors, controls and ruby stay in the game script.
    """
    pack = dict(schema=1, gameAssemblySha256=assembly_hash,
                scratchpadSha256=scratch_hash, scripts=[], ui=list(ui),
                localization=list(localization or []), literals=list(literals or []))
    seen = set()
    def append(script, instruction, slot, opcode, source, target):
        identity = (script, instruction, slot)
        if identity in seen:
            raise ValueError('Duplicate translation slot: '+str(identity))
        seen.add(identity)
        pack['scripts'].append(dict(index=len(pack['scripts']), instruction=instruction,
                                    slot=slot, opcode=opcode, script=script,
                                    source=source, target=target))
    for script in scripts:
        digest = script['hash'].hex()
        if not script_names or digest not in script_names:
            raise ValueError('Missing canonical short script name: '+digest)
        name = script_names[digest]
        for display in script['displays']:
            slot = 0
            for row in display['rows']:
                for span in row['segments']:
                    append(name, display['offset'], slot, display['opcode'],
                           span['source'], span['target'])
                    slot += 1
        for value in script['strings']:
            append(name, value['offset'], -1, value['opcode'], value['source'], value['target'])
    if not pack['scripts'] or not pack['ui']:
        raise ValueError('Translation pack requires scripts and UI entries')
    return pack


def encode_translation_pack(pack):
    """Same KBZH schema-1 byte layout as the shared TranslationPackReader.

    The codec moved to the shared layer (gmode-v2/pack_codec.py) so both version
    adapters write the pack the same way; kept here so existing callers and the
    eighth-game build entry keep their imports.
    """
    return shared_codec.encode_translation_pack(pack)


def main():
    raise SystemExit(
        'Build translations.json / translations.bin through the shared build entry: '
        'python games/08-kibu8/scripts/build_bepinex.py'
    )


if __name__ == '__main__': main()
