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
    entries = runtime_pack.load_ui(ui_path)
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
    report = dict(schema=1, smoke=bool(arguments.smoke), draft=str(draft.relative_to(p.WORK)),
                  scripts=len({entry['script'] for entry in pack['scripts']}), lines=len(pack['scripts']),
                  ui=len(pack['ui']), localization=len(pack['localization']),
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
