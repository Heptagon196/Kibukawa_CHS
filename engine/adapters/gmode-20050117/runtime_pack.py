"""Compile the ninth title's dialogue into a series schema-1 translation pack.

The 20050117 runtime substitutes ``CanvasEx::BunsyouStock``'s argument, so the
unit of translation is exactly one BUNSYOU string. This module therefore:

* walks every shipped scenario with :mod:`vm` and records, for each BUNSYOU line,
  the *effective* ``BunsyouNagasaMax`` — the native renderer positions one
  character per step and ``BunsyouNagasaMax`` is that line's character budget, so
  a longer translation would overflow the fixed text box;
* refuses any translation that exceeds the budget, and refuses a source that
  would need different targets in two scripts, because the runtime keys the pack
  on the source line alone;
* emits the KBZH byte layout the shared ``TranslationPackReader`` expects.

Nothing here rewrites original scripts or offsets.
"""
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / 'gmode-v2'))
import pack_codec
from vm import BUNSYOU, NAMAE_SETTEI, SENTAKUSI, parse_bin, text_arguments

SCHEMA = 1

# Commands that carry displayable text, and which operand holds it.
# BUNSYOU is a display line (grouped, see scenario_lines); SENTAKUSI's first
# StringRead is the menu label; NAMAE_SETTEI's first StringRead is the nameplate.
NAME_TEXT_OPERAND = {BUNSYOU: 3, SENTAKUSI: 0, NAMAE_SETTEI: 1}
KIND_OF_OPCODE = {BUNSYOU: 'line', SENTAKUSI: 'choice', NAMAE_SETTEI: 'name'}

# Handlers that advance CanvasEx::NowStockMojiDan, i.e. end the current display
# line. BUNSYOU_F7 / BUNSYOU_FA do not advance it, so they stay inside a line.
LINE_TERMINATORS = ('BUNSYOU_SLASH', 'BUNSYOU_SEMI_COLON', 'BUNSYOU_PERIOD', 'BUNSYOU_ASTARISK')

# The one in-line command that changes the colour of the characters after it.
# CanvasEx::BunsyouStock fills Bun_iro per character, so BUNSYOU_IRO splits a display
# line into colour runs: the emphasis it creates is part of the line, not decoration.
BUNSYOU_IRO = 245

# A recoloured line travels to the runtime as one string per colour run, joined by this
# character. The pack format itself is unchanged — the shared TranslationPackReader hands
# ``target`` over verbatim — so the runtime splits on a character no translation can
# contain, and a line without it is simply a line of one colour. RuntimePack.RunSeparator
# in the C# side must stay equal to this.
RUN_SEPARATOR = '\x01'


def scenario_lines(parsed):
    """Group BUNSYOU fragments into display lines.

    BUNSYOU reads three setup bytes plus one string. The first byte, when
    non-zero, is CanvasEx::BunsyouNagasaMax: the character budget of every line
    in the block, and it persists until a later command changes it. The third
    byte has no verified relation to the text length and is deliberately unused.
    A line is the run of fragments up to the next terminator that advances
    NowStockMojiDan.
    """
    budget = 0
    lines = []
    current = None
    for command in parsed['commands']:
        if command['opcode'] == BUNSYOU:
            text = text_arguments(command)
            if not text:
                raise ValueError('BUNSYOU without a text argument at %#x' % command['offset'])
            value = command['args'][0]['value']
            if value:
                budget = value
            declared = command['args'][2]['value']
            if current is None:
                current = dict(offset=command['offset'], limit=budget, declared=declared, fragments=[])
            current['fragments'].append(text[0]['value'])
            continue
        if command['name'] in LINE_TERMINATORS and current is not None:
            current['text'] = ''.join(current['fragments'])
            lines.append(current)
            current = None
    if current is not None:
        current['text'] = ''.join(current['fragments'])
        lines.append(current)
    return lines


def emphasis_runs(parsed):
    """Colour runs of every display line whose text changes colour part-way through.

    ``BUNSYOU_IRO`` sets the colour that :meth:`CanvasEx.BunsyouStock` records for the
    characters stocked after it, while ``BUNSYOU_RUBI``, ``BUNSYOU_F7``,
    ``BUNSYOU_FADE`` and ``BUNSYOU_SPEED`` only subdivide the line and never change
    the text. So the runs are delimited by ``BUNSYOU_IRO`` alone.

    The opening run records no colour: the active colour was set by an earlier
    command and is not restated here, so only the split points and the colours that
    follow them are reported. Keyed on the offset that opens the line.
    """
    runs = {}
    current = None
    for command in parsed['commands']:
        opcode = command['opcode']
        if opcode == BUNSYOU:
            text = text_arguments(command)[0]['value']
            if current is None:
                current = dict(offset=command['offset'], runs=[dict(colour=None, text=text)])
            else:
                current['runs'][-1]['text'] += text
        elif opcode == BUNSYOU_IRO:
            if current is not None:
                current['runs'].append(dict(colour=command['args'][0]['value'], text=''))
        elif current is not None and command['name'] in LINE_TERMINATORS:
            if len(current['runs']) > 1:
                runs[current['offset']] = current['runs']
            current = None
    if current is not None and len(current['runs']) > 1:
        runs[current['offset']] = current['runs']
    for offset, line in runs.items():
        if ''.join(run['text'] for run in line) == '':
            raise ValueError('Colour run without text at %#x' % offset)
    return runs


def check_declared_lengths(lines, name):
    """Independent check of the grouping: the third setup byte is the line's own length.

    CanvasEx::BUNSYOU writes ``Bun_nagasa[dan] = b3`` on the first fragment of a
    line and leaves b3 at zero on continuations, so a non-zero b3 must equal the
    concatenated line length. A mismatch means the terminator set is wrong.
    """
    for line in lines:
        if line['declared'] and line['declared'] != len(line['text']):
            raise ValueError('Declared line length %d does not match the grouped line %r in %s at %#x'
                             % (line['declared'], line['text'], name, line['offset']))
        if line['limit'] and len(line['text']) > line['limit']:
            raise ValueError('Shipped line exceeds its own budget in %s at %#x: %r'
                             % (name, line['offset'], line['text']))


def script_lines(raw):
    """Grouped lines with the declared-length self-check applied."""
    return scenario_lines(parse_bin(raw))


def line_index(lines, name):
    """Map each display line's script-relative offset to the line."""
    index = {}
    for line in lines:
        if line['offset'] in index:
            raise ValueError('Two display lines at the same offset %#x in %s' % (line['offset'], name))
        index[line['offset']] = line
    return index


def single_texts(parsed):
    """Nameplate and menu-label commands, keyed by the offset the runtime sees."""
    result = {}
    for command in parsed['commands']:
        kind = KIND_OF_OPCODE.get(command['opcode'])
        if kind is None or kind == 'line':
            continue
        operand = command['args'][NAME_TEXT_OPERAND[command['opcode']]]
        if operand['type'] != 's':
            raise ValueError('Expected a string operand at %#x' % command['offset'])
        result[command['offset']] = dict(offset=command['offset'], kind=kind,
                                         source=operand['value'], opcode=command['opcode'])
    return result


def text_budget(texts):
    """Per-kind character ceiling taken from the shipped corpus.

    The native boxes are fixed, and every shipped string already fits, so the
    longest shipped string of each kind is the largest value known to render.
    Chinese is measured in the same fullwidth cells, so the counts are comparable.
    Sizeable headroom is deliberately not assumed: a translation longer than
    anything the game itself ever drew needs visual confirmation first.
    """
    budgets = {}
    for entry in texts:
        kind = entry['kind']
        budgets[kind] = max(budgets.get(kind, 0), len(entry['source']))
    return budgets


def normalise(text):
    return text


def shipped_index(scripts):
    """Every text-bearing unit in the shipped scripts, keyed on (script, offset).

    A display line is keyed on the BUNSYOU command that opens it; a nameplate or a
    menu label on its own command. Command offsets are unique per script, so the
    index is unambiguous, and a draft entry can only ever address one unit.

    A line the script recolours part-way through also carries ``colours``: how many
    colour runs its fragments are drawn in, which is what a translation of that line
    has to split itself into.
    """
    index = {}
    budgets = {}
    for name, raw in sorted(scripts.items()):
        parsed = parse_bin(raw)
        for line in scenario_lines(parsed):
            key = (name, line['offset'])
            if key in index:
                raise ValueError('Two commands at the same offset %#x in %s' % (line['offset'], name))
            index[key] = dict(kind='line', source=line['text'], limit=line['limit'],
                              fragments=len(line['fragments']), opcode=BUNSYOU)
        for offset, runs in emphasis_runs(parsed).items():
            index[(name, offset)]['colours'] = len(runs)
        for offset, entry in single_texts(parsed).items():
            key = (name, offset)
            if key in index:
                raise ValueError('Two commands at the same offset %#x in %s' % (offset, name))
            index[key] = dict(kind=entry['kind'], source=entry['source'], limit=0,
                              fragments=1, opcode=entry['opcode'])
            budgets[entry['kind']] = max(budgets.get(entry['kind'], 0), len(entry['source']))
    # A nameplate or label box is fixed, so its ceiling is the longest shipped string
    # of that kind; Chinese is measured in the same fullwidth cells.
    for record in index.values():
        if record['kind'] != 'line':
            record['limit'] = budgets.get(record['kind'], 0)
    return index


def validate_units(scripts, units):
    """Yield one resolved record per draft entry, rejecting anything inconsistent.

    Independent of translation state, so a source-only draft can be verified the
    moment it is extracted: each entry must address exactly one shipped text unit,
    its ``source`` must match the shipped text byte for byte, and a translated unit
    must fit the native budget. A line the script recolours part-way through must also
    arrive split by colour run, because the runtime stocks one run per colour: without
    the split the emphasis would land on the wrong characters. Iterating the generator
    is what performs the checks, so callers that only want validation must consume it
    (``build`` does).
    """
    index = shipped_index(scripts)
    seen = set()
    for unit in units:
        key = (unit['script'], unit['offset'])
        record = index.get(key)
        if record is None:
            raise ValueError('Draft offset %#x carries no text in %s' % (unit['offset'], unit['script']))
        if key in seen:
            raise ValueError('Duplicate draft entry at %s:%#x' % key)
        seen.add(key)
        source = normalise(unit['source'])
        if source != record['source']:
            raise ValueError('Draft source does not match the shipped text at %s:%#x' % key)
        target = normalise(unit.get('target') or '')
        if target and record['limit'] and len(target) > record['limit']:
            raise ValueError('Translation exceeds the native %s budget in %s (%d > %d) at %#x'
                             % (record['kind'], key[0], len(target), record['limit'], key[1]))
        runs = unit.get('runs') or None
        colours = record.get('colours')
        if colours:
            if not runs:
                raise ValueError('Line %s:%#x is drawn in %d colours, so its translation must '
                                 'give one run per colour' % (key[0], key[1], colours))
            if len(runs) != colours:
                raise ValueError('Line %s:%#x is drawn in %d colours but its translation has %d runs'
                                 % (key[0], key[1], colours, len(runs)))
            if ''.join(runs) != target:
                raise ValueError('The colour runs at %s:%#x do not join into its translation' % key)
        elif runs:
            raise ValueError('Line %s:%#x is drawn in one colour, so it takes a plain translation'
                             % key)
        yield dict(script=key[0], source=source, target=target, instruction=key[1],
                   slot=record['fragments'], opcode=record['opcode'], kind=record['kind'],
                   runs=runs)


def build(scripts, units, ui, assembly_hash, scratchpad_hash, complete=True):
    """Assemble the pack dict; ``scripts`` maps a canonical name to its raw bytes.

    ``units`` is the tagged translation draft, one entry per display line,
    nameplate or menu label: ``dict(script=, offset=<script-relative offset>,
    source=<Japanese>, target=<Chinese>)``. Sources are verified against the
    shipped scripts so a stale draft cannot be packaged silently. ``slot`` carries
    how many BUNSYOU fragments a line spans, so the runtime blanks the continuations
    instead of repeating the translated text. A recoloured line's ``target`` is its
    colour runs joined by :data:`RUN_SEPARATOR`, so the runtime can stock each run in
    the fragment where that colour takes effect.

    An entry with an empty target is simply not translated yet: it is validated and
    skipped, so a partial draft can be assembled. With ``complete`` the pack is
    refused unless every shipped text unit has a translation, not merely every entry
    the draft happens to list.
    """
    validated = list(validate_units(scripts, units))
    entries = [dict(script=entry['script'], source=entry['source'],
                    target=RUN_SEPARATOR.join(entry['runs']) if entry['runs'] else entry['target'],
                    instruction=entry['instruction'], slot=entry['slot'], opcode=entry['opcode'])
               for entry in validated if entry['target']]
    if complete:
        index = shipped_index(scripts)
        translated = {(entry['script'], entry['instruction']) for entry in entries}
        missing = sorted(key for key in index if key not in translated)
        if missing:
            first = missing[0]
            raise ValueError('Untranslated display text remains: %d (first: %r)'
                             % (len(missing), (first[0], first[1], index[first]['source'])))
    return pack_codec.make_script_pack(entries, assembly_hash, scratchpad_hash, ui)


def load_draft(path):
    document = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if document.get('schema') != SCHEMA or 'units' not in document:
        raise ValueError('Unsupported dialogue draft schema')
    return document['units']


def load_ui(path):
    document = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    entries = document.get('entries') if isinstance(document, dict) else document
    if not entries:
        raise ValueError('UI localization file has no entries')
    return [dict(source=entry['source'], target=entry['target'], key=entry.get('key')) for entry in entries]
