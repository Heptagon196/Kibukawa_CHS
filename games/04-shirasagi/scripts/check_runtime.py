"""Offline original-assembly hook checks and complete kibu4 text replay."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

BASE = Path(__file__).resolve().parents[1]
SERIES = BASE.parents[1]
BUILD = BASE / 'bepinex/build'
OUT = BUILD / 'plugin'
sys.path.insert(0, str(SERIES/'tools'))
from project_config import resolve

def run(args):
    result = subprocess.run([str(x) for x in args], capture_output=True, text=True, errors='replace')
    print(result.stdout, end='', flush=True)
    if result.returncode:
        print(result.stderr, flush=True)
        result.check_returncode()
    return result.stdout.strip()

def main():
    compiler = Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    tests = BASE / 'bepinex/tests'
    core = SERIES / 'engine/core'
    adapter = SERIES / 'engine/adapters/gmode-v1/src'
    pack = json.loads((OUT/'translations.json').read_text(encoding='utf-8-sig'))
    from check_text_layout import validate
    replay = json.loads((BUILD/'replay.json').read_text(encoding='utf-8-sig'))
    source_replay = json.loads((BASE/'research/source-replay.json').read_text(encoding='utf-8-sig'))
    original_commands = source_replay['commands']
    if len(replay['commands']) != len(original_commands) or len(original_commands) != 19469:
        raise ValueError('Fourth-game original command coverage mismatch')
    key = lambda command: (command['script'], command['instruction'])
    actual_by_address = {key(c): c for c in replay['commands']}
    original_by_address = {key(c): c for c in original_commands}
    if len(actual_by_address) != len(replay['commands']) or set(actual_by_address) != set(original_by_address):
        raise ValueError('Missing or duplicate replay command addresses')
    for script in {c['script'] for c in original_commands}:
        expected_order = [c['instruction'] for c in original_commands if c['script'] == script]
        actual_order = [c['instruction'] for c in replay['commands'] if c['script'] == script]
        if actual_order != expected_order:
            raise ValueError('Replay instruction order differs within script: '+script)
    for address, original in original_by_address.items():
        actual = actual_by_address[address]
        for field in ('script', 'instruction', 'opcode', 'nextCursor', 'strings'):
            if actual[field] != original[field]:
                raise ValueError('Replay differs from extracted original: '+str(original['script'])+':'+str(original['instruction'])+':'+field)
        if len(actual['expected']) != len(original['strings']):
            raise ValueError('Replay changed script string slot count')
    if pack['gameAssemblySha256'].lower() != '6c3b38a4cdd378061ff56945ed3752b56c59cc1226672633d911254d4ca4eee7':
        raise ValueError('Fourth-game pack fingerprint mismatch')
    layout = validate(replay['commands'], pack)
    (BUILD/'text-layout-report.json').write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding='utf-8')
    translated_addresses = {(e['script'], e['instruction']) for e in pack['scripts'] if e['source'] != e['target']}
    translated_failures = [f for f in layout['failures'] if (f['script'], f['instruction']) in translated_addresses]
    if translated_failures or layout['unclassified_string_commands']:
        raise ValueError('Text layout audit failed: '+str(translated_failures)+' '+str(layout['unclassified_string_commands']))
    def compile(name, sources, refs=()):
        exe = BUILD / (name + '.exe')
        run([compiler, '/nologo', '/target:exe', '/r:System.Web.Extensions.dll', *('/r:'+str(r) for r in refs), '/out:'+str(exe), *sources, tests/(name+'.cs')])
        return exe
    catalog = compile('CatalogTests', [core/'TranslationCatalog.cs', core/'TranslationPackReader.cs'])
    catalog_result = run([catalog, OUT/'translations.bin', BUILD/'replay.json', OUT/'translations.json'])
    reflow = compile('DialogueReflowTests', [adapter/'DialogueReflow.cs', BASE/'bepinex/src/FixedCardLayout.cs'])
    reflow_result = run([reflow, BUILD/'replay.json', BUILD/'dialogue-reflow-report.json'])
    hook_result = run([shutil.which('pwsh'), '-NoProfile', '-File', BASE/'scripts/validate_runtime.ps1'])
    lock = json.loads((SERIES/'engine/bepinex/locks/BepInEx-5.4.23.5-win-x64.json').read_text())
    frameworks = list((SERIES/'cache/bepinex').glob('*/framework_'+lock['sha256'][:16]+'/BepInEx/core/0Harmony.dll'))
    if len(frameworks) != 1:
        raise RuntimeError('Expected one verified BepInEx framework cache')
    harmony = frameworks[0]
    menu = compile('MenuHookTests', [], [harmony])
    shutil.copyfile(harmony, BUILD/'0Harmony.dll')
    game = resolve('kibu4', allow_disabled=True)['installation']
    menu_result = run([menu, game, OUT, harmony.parents[2]])
    dual = compile('DualRuntimeTests', [], [harmony])
    dual_result = run([dual, game, OUT, harmony.parents[2], BUILD/'read-fixtures.json', BUILD/'replay.json'])
    report = dict(game_runtime_tested=False, catalog=catalog_result, reflow=reflow_result,
                  menu_and_name_labels_checked=layout['speaker_string_slots']+layout['menu_string_slots'],
                  text_layout={k:v for k,v in layout.items() if k not in ('rows','menus','options')},
                  menu_initializer_transpiler=menu_result, dual_runtime=dual_result,
                  hooks=json.loads((BUILD/'hook_report.json').read_text(encoding='utf-8-sig')),
                  dialogue=json.loads((BUILD/'dialogue-reflow-report.json').read_text(encoding='utf-8-sig'))['summary'])
    (BUILD/'runtime-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS: fourth-game offline runtime validation; no game window opened.')

if __name__ == '__main__':
    main()
