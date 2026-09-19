"""Compile the ninth game's translation draft into translations.json / translations.bin.

Reads the work's own scenarios from ``raw/`` and the tagged draft, validates every
line against the native per-line character budget, and writes the schema-1 pack the
shared reader expects. Nothing rewrites original scripts or offsets.

``--smoke`` builds from the labelled runtime smoke fixture instead of the
authoritative draft and relaxes completeness; such a pack is for offline
verification only and must never be published.
"""
import argparse
import json
import sys
from pathlib import Path

import pipeline as p

sys.path.insert(0, str(p.PROJECT['adapter_path']))
import runtime_pack

DRAFT = 'work/dialogue-tagged.json'
SMOKE_DRAFT = 'work/smoke-lines.json'
SMOKE_UI = 'work/smoke-ui.json'
UI = 'work/ui-localization.zh-CN.json'
SHELL_UI = 'work/shell-ui-localization.zh-CN.json'


def display_character(c):
    if '０' <= c <= '９' or 'Ａ' <= c <= 'Ｚ' or 'ａ' <= c <= 'ｚ':
        return chr(ord(c) - 0xfee0)
    return c


def narrow(c):
    c = display_character(c)
    return '0' <= c <= '9' or 'A' <= c <= 'Z' or 'a' <= c <= 'z'


def han(c):
    return '\u3400' <= c <= '\u9fff' or '\uf900' <= c <= '\ufaff' or c == '〇'


def boundaries(text, blank):
    return sum(blank for left, right in zip(text, text[1:])
               if han(left) and narrow(right) or narrow(left) and han(right))


def dialogue_width(text):
    return sum(9 if narrow(c) or c in ' \u3000' else 17 for c in text) + boundaries(text, 9)


def choice_width(text):
    # Kibu9 has no 12px UI atlas; choices use the same 16px atlas as dialogue.
    return dialogue_width(text)


def validate_visual_widths(units):
    widest_line = widest_choice = 0
    for unit in units:
        text = unit.get('target') or ''
        # The deliberately tiny smoke fixture predates kind tags and contains only
        # width-safe examples; the authoritative release draft always carries kind.
        kind = unit.get('kind', 'line')
        width = choice_width(text) if kind == 'choice' else dialogue_width(text)
        if kind == 'line':
            widest_line = max(widest_line, width)
            budget_width = unit.get('limit', 0) * 17
            if budget_width and width > budget_width:
                raise ValueError('line visual width %d exceeds its stable %dpx block at %s:%s: %s' %
                                 (width, budget_width, unit['script'], unit['offset'], text))
        elif kind == 'choice':
            widest_choice = max(widest_choice, width)
        if kind in ('line', 'choice') and width > 240:
            raise ValueError('%s visual width %d exceeds 240px at %s:%s: %s' %
                             (kind, width, unit['script'], unit['offset'], text))
    return widest_line, widest_choice


def scenario_scripts():
    root = p.WORK / 'raw'
    scripts = {}
    for name in sorted(root.rglob('*.bin')):
        if name.name == 'scn0.bin':
            continue
        scripts[name.stem] = name.read_bytes()
    if not scripts:
        raise ValueError('No extracted scenarios; run the extract step first')
    return scripts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--output')
    arguments = parser.parse_args()
    manifest = p.validate_sources()
    draft = p.WORK / (SMOKE_DRAFT if arguments.smoke else DRAFT)
    ui_path = p.WORK / (SMOKE_UI if arguments.smoke else UI)
    if not draft.is_file():
        raise SystemExit('Missing translation draft: ' + str(draft.relative_to(p.WORK)))
    if not ui_path.is_file():
        raise SystemExit('Missing UI localization: ' + str(ui_path.relative_to(p.WORK)))
    if not arguments.smoke:
        # A release answers every key the game ships; the smoke fixture is a subset on
        # purpose, so only the release path is held to the whole table.
        import check_ui
        found = check_ui.run()
        if found:
            raise SystemExit('UI localization is not release ready:\n   ' + '\n   '.join(found))
    units = runtime_pack.load_draft(draft)
    widest_line, widest_choice = validate_visual_widths(units)
    entries = runtime_pack.load_ui(ui_path)
    shell_path = p.WORK / SHELL_UI
    if not shell_path.is_file():
        raise SystemExit('Missing shell UI localization: ' + SHELL_UI)
    entries.extend(runtime_pack.load_ui(shell_path))
    # Entries carrying a Localize key drive Steezy.Localize.Localization::Get; the rest
    # replace literals the game hard-codes in its own arrays.
    ui = [entry for entry in entries if not entry.get('key')]
    localization = [entry for entry in entries if entry.get('key')]
    if not ui:
        raise SystemExit('The UI file needs at least one literal entry without a key')
    scripts = scenario_scripts()
    pack = runtime_pack.build(scripts, units, ui,
                              manifest['source_hashes']['kibu9_Data/Managed/Assembly-CSharp.dll'],
                              manifest['source_hashes']['kibu9_Data/StreamingAssets/scratchpad'],
                              complete=not arguments.smoke)
    if localization:
        seen = set()
        for entry in localization:
            if entry['key'] in seen:
                raise SystemExit('Duplicate localization key: ' + entry['key'])
            seen.add(entry['key'])
            pack['localization'].append(dict(source=entry['source'], target=entry['target'], key=entry['key']))
    encoded = runtime_pack.pack_codec.encode_translation_pack(pack)
    output = p.inside(Path(arguments.output) if arguments.output else p.WORK / 'bepinex/build/pack')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'translations.json').write_text(json.dumps(pack, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (output / 'translations.bin').write_bytes(encoded)
    import dialogue_layout
    dialogue_layout.build(scripts, units, encoded, output)
    report = dict(schema=1, smoke=bool(arguments.smoke), draft=str(draft.relative_to(p.WORK)),
                  scripts=len({entry['script'] for entry in pack['scripts']}), lines=len(pack['scripts']),
                  ui=len(pack['ui']), localization=len(pack['localization']),
                  widest_dialogue_px=widest_line, widest_choice_px=widest_choice,
                  json_bytes=len(json.dumps(pack, ensure_ascii=False).encode('utf-8')), bin_bytes=len(encoded),
                  bin_sha256=p.sha(encoded), release_ready=not arguments.smoke, runtime_tested=False)
    p.save(output / 'pack-report.json', report)
    # A caller may request an isolated smoke fixture while assembling a release.
    # Only the canonical output updates the work's latest-pack report.
    if arguments.output is None:
        p.save(p.WORK / 'reports/pack_latest.json', report)
    print('PACK READY %d lines, %d UI, %d bytes -> %s' % (report['lines'], report['ui'], len(encoded), output))


if __name__ == '__main__':
    main()
