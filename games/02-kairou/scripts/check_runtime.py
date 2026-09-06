"""Offline original-assembly hook checks and complete kibu2 text replay."""
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
    layout = validate(replay['commands'], pack)
    (BUILD/'text-layout-report.json').write_text(json.dumps(layout, ensure_ascii=False, indent=2), encoding='utf-8')
    if layout['failures'] or layout['unclassified_string_commands']:
        raise ValueError('Text layout audit failed: '+str(layout['failures'])+' '+str(layout['unclassified_string_commands']))
    def compile(name, sources, refs=()):
        exe = BUILD / (name + '.exe')
        run([compiler, '/nologo', '/target:exe', '/r:System.Web.Extensions.dll', *('/r:'+str(r) for r in refs), '/out:'+str(exe), *sources, tests/(name+'.cs')])
        return exe
    catalog = compile('CatalogTests', [core/'TranslationCatalog.cs', core/'TranslationPackReader.cs'])
    catalog_result = run([catalog, OUT/'translations.bin', BUILD/'replay.json', OUT/'translations.json'])
    reflow = compile('DialogueReflowTests', [adapter/'DialogueReflow.cs', BASE/'bepinex/src/FixedCardLayout.cs'])
    reflow_result = run([reflow, BUILD/'replay.json', BUILD/'dialogue-reflow-report.json'])
    floorplan = compile('FloorPlanOverlayTests', [BASE/'bepinex/src/FloorPlanOverlay.cs'])
    floorplan_result = run([floorplan])
    sentence = compile('SentencePuzzleTests', [BASE/'bepinex/src/SentencePuzzleLayout.cs'])
    sentence_result = run([sentence, BUILD/'replay.json'])
    hook_result = run([shutil.which('pwsh'), '-NoProfile', '-File', BASE/'scripts/validate_runtime.ps1'])
    lock = json.loads((SERIES/'engine/bepinex/locks/BepInEx-5.4.23.5-win-x64.json').read_text())
    frameworks = list((SERIES/'cache/bepinex').glob('*/framework_'+lock['sha256'][:16]+'/BepInEx/core/0Harmony.dll'))
    if len(frameworks) != 1:
        raise RuntimeError('Expected one verified BepInEx framework cache')
    harmony = frameworks[0]
    menu = compile('MenuHookTests', [], [harmony])
    shutil.copyfile(harmony, BUILD/'0Harmony.dll')
    game = resolve('kibu2', allow_disabled=True)['installation']
    menu_result = run([menu, game, OUT, harmony.parents[2]])
    report = dict(game_runtime_tested=False, catalog=catalog_result, reflow=reflow_result,
                  floor_plan_overlay=floorplan_result,
                  sentence_puzzle=sentence_result,
                  menu_and_name_labels_checked=layout['speaker_string_slots']+layout['menu_string_slots'],
                  text_layout={k:v for k,v in layout.items() if k not in ('rows','menus','options')},
                  menu_initializer_transpiler=menu_result,
                  hooks=json.loads((BUILD/'hook_report.json').read_text(encoding='utf-8-sig')),
                  dialogue=json.loads((BUILD/'dialogue-reflow-report.json').read_text(encoding='utf-8-sig'))['summary'])
    (BUILD/'runtime-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS: second-game offline runtime validation; no game window opened.')

if __name__ == '__main__':
    main()
