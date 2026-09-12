"""Offline kibu7 catalog, native managed reader, hooks and text-buffer replay.

Never installs, launches, or edits a game. Reports distinguish managed-method
execution from a Unity playthrough and from the bounded reflow fixture.
"""
import base64
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile

import pipeline as p
from check_text_layout import validate

BASE=p.WORK
SERIES=p.SERIES
BUILD=BASE/'bepinex/build'
OUT=BUILD/'plugin'


def run(args):
    result=subprocess.run([str(x) for x in args],capture_output=True,text=True,errors='replace')
    print(result.stdout,end='',flush=True)
    if result.returncode:
        print(result.stderr,flush=True)
        result.check_returncode()
    return result.stdout.strip()


def real_replay(manifest, replay, pack):
    """Reparse locked original bytes, independently of exported replay.json."""
    for rel in (p.STREAM+'file',p.STREAM+'scratchpad'):
        p.require(p.sha((BASE/'originals'/rel).read_bytes())==manifest['source_hashes'][rel],
                  'Locked original snapshot changed: '+rel)
    defs={int(k):v for k,v in manifest['definitions'].items()}
    table=struct.unpack('<65537H',base64.b64decode(manifest['codec_base64']))
    file=p.text_assets(BASE/'originals'/(p.STREAM+'file'))
    scratch=p.text_assets(BASE/'originals'/(p.STREAM+'scratchpad'))
    archive_name=p.load(BASE/'project.json')['resource_archive']
    archive=zipfile.ZipFile(io.BytesIO(scratch[archive_name]))
    scripts={name:archive.read(name) for name in archive.namelist() if p.re.fullmatch(r'scn\d+',name)}
    scripts.update({f'subscn_{i+1}':value for i,value in enumerate(p.sub_parts(file['subscn']))})
    expected_scripts=set(manifest['script_stats'])
    p.require(set(scripts)==expected_scripts,'Missing original scenario')
    by_address={(e['script'],e['instruction']):e for e in replay['commands']}
    p.require(len(by_address)==len(replay['commands']),'Duplicate replay address')
    translations={(e['script'],e['instruction'],e['slot']):e for e in pack['scripts']}
    p.require(len(translations)==len(pack['scripts']),'Duplicate translated slot')
    result=[]
    observed=set()
    used=set()
    for name,data in scripts.items():
        rows=[]
        commands=p.parse_script(data,defs)
        p.require(len(commands)==manifest['script_stats'][name]['instructions'],'Instruction count changed: '+name)
        p.require([c['instruction'] for c in replay['commands'] if c['script']==name]==[c['offset'] for c in commands],'Replay command order changed: '+name)
        for command in commands:
            address=(name,command['offset'])
            observed.add(address)
            values=[p.decode(a['value'],table) if a['value'] else None for a in command['args'] if a['kind']==3]
            integers=[a['value'] if a['value']<2**31 else a['value']-2**32 for a in command['args'] if a['kind']!=3]
            expected=list(values)
            for slot,value in enumerate(values):
                key=(*address,slot)
                if key in translations:
                    entry=translations[key]
                    p.require(entry['source']==value and entry['opcode']==command['opcode'],'Pack source/opcode differs: '+str(key))
                    expected[slot]=entry['target']; used.add(key)
            actual=by_address.get(address)
            p.require(actual is not None,'Missing actual command: '+str(address))
            row=dict(instruction=command['offset'],opcode=command['opcode'],nextCursor=command['end'],strings=values,expected=expected,integers=integers)
            for key,value in row.items():
                p.require(actual[key]==value,'Export replay mismatch: '+str(address)+':'+key)
            row['jumps']=[a['value'] for a in command['args'] if a['kind']==4]
            rows.append(row)
        result.append(dict(name=name,bytes=base64.b64encode(data).decode(),commands=rows))
    p.require(set(by_address)==observed,'Extra replay command')
    p.require(used==set(translations),'Unreachable translation address in original bytes')
    p.require(len(observed)==sum(s['instructions'] for s in manifest['script_stats'].values()),'Seventh-game original command coverage mismatch')
    input_data=dict(definitions=[[opcode,*kinds] for opcode,kinds in defs.items()],scripts=result)
    p.save(BUILD/'original-engine-input.json',input_data)


def main():
    manifest=p.validate_sources()
    compiler=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    tests=BASE/'bepinex/tests';core=SERIES/'engine/core';adapter=SERIES/'engine/adapters/gmode-v1/src'
    pack=p.load(OUT/'translations.json');replay=p.load(BUILD/'replay.json')
    p.require(pack['gameAssemblySha256']==manifest['source_hashes'][p.DLL],'Seventh-game pack fingerprint mismatch')
    real_replay(manifest,replay,pack)
    layout=validate(replay['commands'],pack)
    p.save(BUILD/'text-layout-report.json',layout)
    p.require(not layout['failures'] and not layout['unclassified_string_commands'],'Text layout audit failed: '+str(layout['failures'])+' '+str(layout['unclassified_string_commands']))
    def compile(name,sources,refs=()):
        exe=BUILD/(name+'.exe')
        run([compiler,'/nologo','/target:exe','/r:System.Web.Extensions.dll',*('/r:'+str(r) for r in refs),'/out:'+str(exe),*sources,tests/(name+'.cs')])
        return exe
    core_files=[core/'TranslationCatalog.cs',core/'TranslationPackReader.cs']
    catalog=compile('CatalogTests',core_files)
    catalog_result=run([catalog,OUT/'translations.bin',BUILD/'replay.json',OUT/'translations.json'])
    original=compile('OriginalEngineTests',core_files)
    original_result=run([original,p.GAME,BUILD/'original-engine-input.json',OUT/'translations.bin',BUILD/'original-engine-report.json'])
    reflow=compile('DialogueReflowTests',[adapter/'DialogueReflow.cs',BASE/'bepinex/src/FixedCardLayout.cs'])
    reflow_result=run([reflow,BUILD/'replay.json',BUILD/'dialogue-reflow-report.json'])
    run([shutil.which('pwsh'),'-NoProfile','-File',BASE/'scripts/validate_runtime.ps1'])
    lock=p.load(SERIES/'engine/bepinex/locks/BepInEx-5.4.23.5-win-x64.json')
    frameworks=list((SERIES/'cache/bepinex').glob('*/framework_'+lock['sha256'][:16]+'/BepInEx/core/0Harmony.dll'))
    p.require(len(frameworks)==1,'Expected one verified BepInEx cache')
    harmony=frameworks[0]
    menu=compile('MenuHookTests',[],[harmony])
    shutil.copyfile(harmony,BUILD/'0Harmony.dll')
    menu_result=run([menu,p.GAME,OUT,harmony.parents[2]])
    report=dict(game_runtime_tested=False,catalog=catalog_result,reflow=reflow_result,original_engine=original_result,
                original_engine_details=p.load(BUILD/'original-engine-report.json'),
                menu_and_name_labels_checked=layout['speaker_string_slots']+layout['menu_string_slots'],
                text_layout={k:v for k,v in layout.items() if k not in ('rows','menus','options')},
                menu_initializer_transpiler=menu_result,hooks=p.load(BUILD/'hook_report.json'),
                dialogue=p.load(BUILD/'dialogue-reflow-report.json')['summary'])
    p.save(BUILD/'runtime-validation.json',report)
    print('PASS: seventh-game offline runtime validation; no game window opened.')


if __name__=='__main__':
    main()
