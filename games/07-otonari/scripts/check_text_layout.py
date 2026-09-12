"""Audit every non-dialogue script string without applying dialogue reflow to menus.

Dialogue is checked separately by DialogueReflowTests using the runtime adapter.
Unity UI is not a 240px legacy text grid; its fonts/rectangles have separate checks.
"""
from collections import Counter
import json
from pathlib import Path

def half_cells(text):
    return sum(1 if " " <= c <= "~" or "\uff66" <= c <= "\uff9f" else 2 for c in text)


def validate(commands, pack):
    rows, menus, failures, unclassified, options = [], [], [], [], []
    counts = Counter()
    for command in commands:
        op = command['opcode']
        values = command['expected']
        counts[op] += len(values)
        location = dict(script=command['script'], instruction=command['instruction'], opcode=op)
        if op == 72:
            continue  # Real coroutine replay checks these, including original untranslated slots.
        if op == 70:
            rendered = [values[0] or '']
            kind = 'speaker'
        elif 105 <= op < 130:
            # The unchanged CanvasEx Script iterator uses padded paired columns for
            # 105..119 but one full row per label for 120..129. The latter must
            # not inherit a four-glyph limit from a different game's wording.
            option_limit = 8 if op < 120 else 20
            for slot, value in enumerate(values):
                text = value or ''
                option = dict(**location, slot=slot, text=text, half_cells=half_cells(text), limit_half_cells=option_limit)
                options.append(option)
                if option['half_cells'] > option_limit:
                    failures.append(dict(option, reason='menu option exceeds its column width'))
            # Original two-column menus pad their left cell to five full-width glyphs.
            if op < 120:
                rendered = []
                for i in range(0, len(values), 2):
                    left = values[i] or ''
                    rendered.append(left + ' ' * max(0, 10-half_cells(left)) +
                                    ((values[i+1] or '') if i+1 < len(values) else ''))
            else:
                rendered = [value or '' for value in values]
            kind = 'menu'
            menus.append(dict(**location, rows=len(rendered), text=rendered))
            # Audit with the stricter speaker-present budget even when no speaker is active.
            if len(rendered) > 4:
                failures.append(dict(**location, reason='menu exceeds four body rows'))
        else:
            if values:
                unclassified.append(dict(**location, strings=values))
            continue
        for text in rendered:
            row = dict(**location, kind=kind, text=text, half_cells=half_cells(text), characters=len(text))
            rows.append(row)
            if row['half_cells'] > 20 or row['characters'] > 20:
                failures.append(dict(row, reason='row exceeds width or character buffer'))
    # Seventh-game reviewed title/location/credits lines must stay in their
    # original slots. This is independent of sixth-game puzzle card content.
    review = json.loads((Path(__file__).resolve().parents[1] / 'review/fixed-page-review.json').read_text(encoding='utf-8'))
    by_index = {str(entry['index']): entry for entry in pack['scripts']}
    fixed_rows = []
    for index, approved in review['slot_targets'].items():
        entry = by_index.get(index)
        actual = entry['target'] if entry else None
        row = dict(index=int(index), text=actual, half_cells=half_cells(actual or ''))
        fixed_rows.append(row)
        if actual != approved:
            failures.append(dict(row, reason='reviewed fixed-page slot changed'))
        if row['half_cells'] > 20:
            failures.append(dict(row, reason='fixed-page line exceeds native text width'))
    return dict(checked_script_string_slots=sum(counts.values()),
                dialogue_string_slots=counts[72], speaker_string_slots=counts[70],
                menu_string_slots=sum(v for op,v in counts.items() if 105 <= op < 130),
                menu_commands=len(menus), checked_non_dialogue_rows=len(rows),
                checked_menu_options=len(options), menu_option_limit_half_cells={'two_column':8,'single_column':20},
                max_menu_option_half_cells=max((o['half_cells'] for o in options), default=0),
                max_menu_rows=max((m['rows'] for m in menus), default=0),
                max_non_dialogue_half_cells=max((r['half_cells'] for r in rows), default=0),
                limit_half_cells=20, limit_characters=20, menu_row_limit=4,
                checked_fixed_page_rows=len(fixed_rows), fixed_page_rows=fixed_rows,
                failure_count=len(failures), failures=failures,
                unclassified_string_commands=unclassified, rows=rows, menus=menus, options=options,
                unity_ui=dict(strings=len(pack['ui']), localization_keys=len(pack['localization']),
                              literals=len(pack['literals']),
                              scope='Separate Unity UI layout, not subject to the legacy dialogue row limit; checked by existing UI/font/help builders.'),
                scope='Every script string slot is classified; body strings are replayed by DialogueReflowTests. Menu padding and all speaker names are checked here.')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1] / 'bepinex/build'
    load = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
    report = validate(load(root/'replay.json')['commands'], load(root/'plugin/translations.json'))
    (root/'text-layout-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if report['failures'] or report['unclassified_string_commands']:
        raise ValueError('Text layout audit failed: '+str(report['failures'])+' '+str(report['unclassified_string_commands']))
    print('PASS: all script slots classified; menu options, padded rows, row counts and speaker names fit.')
