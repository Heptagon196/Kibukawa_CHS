"""Build the BepInEx runtime edition. All writes remain in translation_workspace.
Pinned official framework download is automatic; cached archives are SHA256 checked.
"""
import argparse, base64, collections, io, json, os, re, shutil, struct, subprocess, sys, time, urllib.request, zipfile
from pathlib import Path
import pipeline as p
from check_dialogue_width import validate as validate_width
from build_pixel_font import build_font
from build_help_pages import build_help_pages
from check_text_layout import validate as validate_text_layout
from check_japanese_residue import audit as audit_japanese_residue
from check_click_boundaries import validate as validate_click_boundaries
from build_chat_layout import generate as generate_chat_layout
from check_fixed_cards import validate as validate_fixed_cards

ROOT=p.WORK/'bepinex'

def source(name):
    candidates=[ROOT/'src'/name, p.SERIES/'engine/core'/name, p.PROJECT['adapter_path']/'src'/name]
    matches=[path for path in candidates if path.is_file()]
    p.require(len(matches)==1,'Missing or duplicate C# source: '+name)
    return matches[0]

def all_sources():
    paths=list((ROOT/'src').glob('*.cs'))+list((p.SERIES/'engine/core').glob('*.cs'))+list((p.PROJECT['adapter_path']/'src').glob('*.cs'))
    p.require(len({x.name for x in paths})==len(paths),'Duplicate runtime source names')
    return sorted(paths)


def write_binary_pack(pack,path):
    data=io.BytesIO()
    def integer(value): data.write(struct.pack('<i',value))
    def text(value):
        encoded=value.encode('utf-8') if value is not None else None
        integer(len(encoded) if encoded is not None else -1)
        if encoded is not None: data.write(encoded)
    data.write(b'KBZH'); integer(pack['schema'])
    text(pack['gameAssemblySha256']); text(pack['scratchpadSha256'])
    integer(len(pack['scripts']))
    for entry in pack['scripts']:
        for key in ('index','instruction','slot','opcode'): integer(entry[key])
        for key in ('script','source','target'): text(entry[key])
    for group in ('ui','localization'):
        integer(len(pack[group]))
        for entry in pack[group]:
            for key in ('source','target','key'): text(entry.get(key))
    integer(len(pack['literals']))
    for entry in pack['literals']:
        for key in ('index','token','instruction'): integer(entry[key])
        for key in ('source','target','method'): text(entry[key])
    p.inside(path).write_bytes(data.getvalue())

def ensure_framework(refresh=False):
    lock=p.load(ROOT/'dependency.lock.json')
    dest=p.inside(ROOT/'deps'/lock['asset']); dest.parent.mkdir(parents=True,exist_ok=True)
    cached=dest.exists() and dest.stat().st_size==lock['size'] and p.sha(dest.read_bytes())==lock['sha256']
    downloaded=False
    if refresh or not cached:
        print('Downloading official BepInEx '+lock['version'],flush=True)
        request=urllib.request.Request(lock['url'],headers={'User-Agent':'Kibu1-ZhCN-Build/1.0'})
        temp=dest.with_suffix('.download')
        try:
            with urllib.request.urlopen(request,timeout=90) as response, temp.open('wb') as out:
                shutil.copyfileobj(response,out)
            p.require(temp.stat().st_size==lock['size'] and p.sha(temp.read_bytes())==lock['sha256'],'BepInEx download hash mismatch; refusing to use it')
            os.replace(temp,dest); downloaded=True
        finally:
            if temp.exists(): temp.unlink()
    print('BepInEx SHA256 verified: '+lock['sha256'],flush=True)
    extracted=p.inside(ROOT/'deps'/('framework_'+lock['version']))
    extracted.mkdir(exist_ok=True)
    files=[]
    with zipfile.ZipFile(dest) as archive:
        for info in archive.infolist():
            target=p.inside(extracted/info.filename)
            p.require(target.is_relative_to(extracted),'Dependency ZIP path traversal')
            if info.is_dir(): target.mkdir(parents=True,exist_ok=True); continue
            content=archive.read(info)
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists() or target.read_bytes()!=content: target.write_bytes(content)
            files.append(info.filename)
    for required in ['winhttp.dll','doorstop_config.ini','BepInEx/core/BepInEx.dll','BepInEx/core/0Harmony.dll']:
        p.require((extracted/required).exists(),'Missing framework file: '+required)
    return extracted,dict(version=lock['version'],sha256=lock['sha256'],downloaded=downloaded,cache_verified=True,files=files)

def export_pack(out):
    cache=p.load(p.WORK/'work/cache.json'); manifest=p.load(p.WORK/'work/manifest.json')
    p.validate_cache(cache,manifest)
    for rel,digest in manifest['source_hashes'].items(): p.require(p.sha((p.GAME/rel).read_bytes())==digest,'Original game changed: '+rel)
    # Public checkout contains no original assets. Recreate local snapshots only
    # from the user's hash-verified installation, without touching translations.
    for rel,digest in manifest['source_hashes'].items():
        snapshot=p.inside(p.WORK/'originals'/rel)
        if not snapshot.exists():
            snapshot.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(p.GAME/rel,snapshot)
        p.require(p.sha(snapshot.read_bytes())==digest,'Original snapshot changed: '+rel)
    by_id={x['text_index']:x for x in p.items(cache)}
    defs={int(k):v for k,v in manifest['definitions'].items()}
    pack=dict(schema=1,gameAssemblySha256=manifest['source_hashes'][p.DLL],scratchpadSha256=manifest['source_hashes'][p.STREAM+'scratchpad'],scripts=[],ui=[],localization=[],literals=[])
    ui=collections.defaultdict(set)
    for e in manifest['entries']:
        x=by_id[e['text_index']]; loc=e['location']
        if x['translation_status'] not in (1,2): continue
        base=dict(index=x['text_index'],source=x['source_text'],target=x['translated_text'])
        if loc['kind']=='script':
            script=loc.get('member') or 'subscn_'+str(loc['part']+1)
            slot=defs[loc['opcode']][:loc['argument']].count(3)
            pack['scripts'].append(dict(base,script=script,instruction=loc['instruction'],slot=slot,opcode=loc['opcode']))
        elif loc['kind']=='assembly':
            pack['literals'].append(dict(base,token=loc['token'],instruction=loc['instruction'],method=loc['method']))
            ui[base['source']].add(base['target'])
        else:
            ui[base['source']].add(base['target'])
            if loc['kind']=='csv': pack['localization'].append(dict(source=base['source'],target=base['target'],key=loc['key']))
    conflicts=[]
    for source,targets in ui.items():
        if len(targets)!=1: conflicts.append(dict(source=source,targets=sorted(targets)))
        else: pack['ui'].append(dict(source=source,target=next(iter(targets))))
    p.require(not conflicts,'Ambiguous UI translations: '+str(conflicts))
    p.save(out/'translations.json',pack)
    write_binary_pack(pack,out/'translations.bin')
    # Independent replay fixture: parse every original instruction, including unmodified slots.
    file=p.text_objects(p.UnityPy.load(str(p.WORK/'originals'/(p.STREAM+'file'))))
    scratch=p.text_objects(p.UnityPy.load(str(p.WORK/'originals'/(p.STREAM+'scratchpad'))))
    archive=zipfile.ZipFile(io.BytesIO(p.raw_text(scratch['kamen.res'])))
    scripts={n:archive.read(n) for n in archive.namelist() if re.fullmatch(r'scn\d+',n)}
    scripts.update({'subscn_'+str(i+1):b for i,b in enumerate(p.sub_parts(p.raw_text(file['subscn'])))})
    table=struct.unpack('<65537H',base64.b64decode(manifest['codec_base64']))
    translated={(x['script'],x['instruction'],x['slot']):x['target'] for x in pack['scripts']}
    replay=[]
    for name,data in scripts.items():
        for command in p.parse_script(data,defs):
            strings=[p.decode(a['value'],table) if a['value'] else None for a in command['args'] if a['kind']==3]
            expected=[translated.get((name,command['offset'],i),s) for i,s in enumerate(strings)]
            integers=[a['value'] if a['value'] < 2147483648 else a['value']-4294967296 for a in command['args'] if a['kind']!=3]
            replay.append(dict(script=name,instruction=command['offset'],opcode=command['opcode'],nextCursor=command['end'],strings=strings,expected=expected,integers=integers))
    p.save(ROOT/'build/replay.json',dict(commands=replay))
    generate_chat_layout(replay)
    validate_fixed_cards(replay)
    validate_click_boundaries(replay)
    width_report=validate_width(replay,pack)
    p.save(ROOT/'build/width_report.json',width_report)
    # Historical source-row widths are diagnostic only: runtime now joins and reflows them.
    text_report=validate_text_layout(replay,pack)
    p.save(ROOT/'build/text-layout-report.json',text_report)
    p.require(not text_report['failures'] and not text_report['unclassified_string_commands'],
              'Unclassified or overflowing script text; see bepinex/build/text-layout-report.json')
    return pack,manifest

def compile_plugin(framework,out):
    dotnet=shutil.which('dotnet'); p.require(dotnet,'Install a .NET SDK to compile the plugin')
    sdk_lines=subprocess.check_output([dotnet,'--list-sdks'],text=True).strip().splitlines()
    choices=[re.fullmatch(r'([^ ]+) \[(.+)\]',line) for line in sdk_lines]
    choices=[m for m in choices if m]
    p.require(choices,'No .NET SDK installed')
    match=choices[-1]; compiler=Path(match[2])/match[1]/'Roslyn/bincore/csc.dll'
    managed=p.GAME/'kibu1_Data/Managed'
    refs=['mscorlib.dll','netstandard.dll','System.dll','System.Core.dll','UnityEngine.dll','UnityEngine.CoreModule.dll','UnityEngine.UI.dll','UnityEngine.UIModule.dll','UnityEngine.TextRenderingModule.dll','UnityEngine.ImageConversionModule.dll']
    response=['-nologo','-nostdlib+','-target:library','-optimize+','-langversion:7.3','-out:"'+str(out/'Kibu1ZhCN.dll')+'"']
    response+=['-reference:"'+str(managed/r)+'"' for r in refs]
    response+=['-reference:"'+str(framework/'BepInEx/core'/r)+'"' for r in ['BepInEx.dll','0Harmony.dll']]
    response+=['"'+str(s)+'"' for s in all_sources()]
    rsp=p.inside(ROOT/'build/compile.rsp'); rsp.parent.mkdir(parents=True,exist_ok=True); rsp.write_text('\n'.join(response),encoding='utf-8-sig')
    subprocess.run([dotnet,str(compiler),'@'+str(rsp)],check=True)

def run_tests(out):
    compiler=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    p.require(compiler.exists(),'.NET Framework C# compiler required for offline replay tests')
    exe=p.inside(ROOT/'build/CatalogTests.exe')
    subprocess.run([str(compiler),'/nologo','/target:exe','/r:System.Web.Extensions.dll','/out:'+str(exe),str(source('TranslationCatalog.cs')),str(source('TranslationPackReader.cs')),str(ROOT/'tests/CatalogTests.cs')],check=True)
    result=subprocess.run([str(exe),str(out/'translations.bin'),str(ROOT/'build/replay.json'),str(out/'translations.json')],capture_output=True,text=True)
    if result.returncode:
        print(result.stdout,flush=True); print(result.stderr,file=sys.stderr,flush=True); result.check_returncode()
    print(result.stdout.strip())
    return result.stdout.strip()

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--refresh-dependency',action='store_true'); args=parser.parse_args()
    residue_report=audit_japanese_residue()
    framework,dependency=ensure_framework(args.refresh_dependency)
    out=p.inside(ROOT/'build/plugin'); out.mkdir(parents=True,exist_ok=True)
    pack,manifest=export_pack(out)
    font_report=build_font(pack,out)
    help_report=build_help_pages()
    compile_plugin(framework,out)
    tests=run_tests(out)
    compiler=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    reflow_exe=ROOT/'build/DialogueReflowTests.exe'
    subprocess.run([str(compiler),'/nologo','/r:System.Web.Extensions.dll','/out:'+str(reflow_exe),str(source('DialogueReflow.cs')),str(source('ChatLayout.cs')),str(source('FixedCardLayout.cs')),str(ROOT/'tests/DialogueReflowTests.cs')],check=True)
    subprocess.run([str(reflow_exe),str(ROOT/'build/replay.json'),str(ROOT/'build/dialogue-reflow-report.json')],check=True)
    menu_exe=ROOT/'build/MenuMemoryTests.exe'
    subprocess.run([str(compiler),'/nologo','/out:'+str(menu_exe),str(source('MenuSelectionMemory.cs')),str(ROOT/'tests/MenuMemoryTests.cs')],check=True)
    subprocess.run([str(menu_exe)],check=True)
    menu_hook_exe=ROOT/'build/MenuHookTests.exe'
    subprocess.run([str(compiler),'/nologo','/r:'+str(framework/'BepInEx/core/0Harmony.dll'),'/out:'+str(menu_hook_exe),str(ROOT/'tests/MenuHookTests.cs')],check=True)
    subprocess.run([str(menu_hook_exe),str(p.GAME),str(out)],check=True)
    # Validate runtime hook signatures and every literal ordinal against the original assembly.
    shell=shutil.which('pwsh'); p.require(shell,'PowerShell 7 required for managed hook validation')
    subprocess.run([shell,'-NoProfile','-File',str(ROOT/'tests/ValidateHooks.ps1')],check=True)
    release=p.inside(p.WORK/'out'/('bepinex_zh-CN_'+p.stamp())); release.mkdir()
    package=release/'package'; package.mkdir()
    for rel in dependency['files']:
        src=framework/rel; dst=p.inside(package/rel); dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
    plugin_dir=package/'BepInEx/plugins/Kibu1ZhCN'; plugin_dir.mkdir(parents=True,exist_ok=True)
    for name in ('Kibu1ZhCN.dll','translations.json','translations.bin'): shutil.copyfile(out/name,plugin_dir/name)
    (plugin_dir/'fonts').mkdir()
    for name in ('dialogue-16.png','dialogue-16.bin','unifont-16.0.04.hex.gz'): shutil.copyfile(out/'fonts'/name,plugin_dir/'fonts'/name)
    (plugin_dir/'licenses').mkdir()
    for path in (out/'licenses').glob('Unifont-*.txt'): shutil.copyfile(path,plugin_dir/'licenses'/path.name)
    shutil.copyfile(ROOT/'README_INSTALL.txt',package/'README_汉化安装.txt')
    (package/'BepInEx/licenses').mkdir()
    for path in (ROOT/'licenses').glob('*.txt'):
        if path.name == 'BepInEx-LICENSE.txt' or path.name.startswith('Unifont-'):
            shutil.copyfile(path,package/'BepInEx/licenses'/path.name)
    version=re.search(r'BepInPlugin\(Id, "[^"]+", "([^"]+)"', (source('Plugin.cs')).read_text(encoding='utf-8-sig')).group(1)
    report=dict(plugin_version=version,edition='BepInEx runtime plugin',dependency=dependency,script_slots=len(pack['scripts']),ui_strings=len(pack['ui']),localization_keys=len(pack['localization']),assembly_literals=len(pack['literals']),
                tests=tests,original_game_unchanged=all((p.GAME/rel).is_file() and p.sha((p.GAME/rel).read_bytes())==digest for rel,digest in manifest['game_hashes'].items()),game_runtime_tested=False,
                original_assets_in_package=False,original_assembly_in_package=False,dynamic_chinese_font=True,
                hook_validation=p.load(ROOT/'build/hook_report.json'),dialogue_width=p.load(ROOT/'build/width_report.json'),pixel_dialogue_font=font_report,help_pages=help_report,japanese_residue=residue_report,
                text_layout={k:v for k,v in p.load(ROOT/'build/text-layout-report.json').items() if k not in ('rows','menus','options')},
                dialogue_reflow={k:v for k,v in p.load(ROOT/'build/dialogue-reflow-report.json').items() if k != 'pages'})
    p.require(report['original_game_unchanged'],'Original game hash changed')
    for path in package.rglob('*'):
        if path.is_file():
            rel=path.relative_to(package).as_posix()
            p.require(not rel.startswith('kibu1_Data/') and path.name!='Assembly-CSharp.dll','Original game file leaked into package')
    report['reproducibility'] = dict(
        series_config=p.load(p.SERIES/'series.json'), project=p.load(p.WORK/'project.json'),
        source_hashes={x.relative_to(p.SERIES).as_posix():p.sha(x.read_bytes()) for x in all_sources()},
        translation_sha256=p.sha((p.WORK/'work/cache.json').read_bytes()),
        manifest_sha256=p.sha((p.WORK/'work/manifest.json').read_bytes()))
    report['package_files']={x.relative_to(package).as_posix():p.sha(x.read_bytes()) for x in package.rglob('*') if x.is_file()}
    p.save(release/'build_report.json',report)
    archive_path=release/'Kibu1_ZhCN_BepInEx_Full.zip'
    with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package.rglob('*')):
            if path.is_file(): archive.write(path,path.relative_to(package).as_posix())
    with zipfile.ZipFile(archive_path) as archive: p.require(archive.testzip() is None,'Release ZIP corrupted')
    p.save(p.WORK/'reports/bepinex_latest.json',dict(output=str(release),zip=str(archive_path),zip_sha256=p.sha(archive_path.read_bytes()),**report))
    summary_path=p.WORK/'reports/translation_summary.json'
    if summary_path.exists():
        summary=p.load(summary_path)
        if 'legacy_offline_output' not in summary:
            summary['legacy_offline_output']={key:summary.get(key) for key in ('output','font_replaced','utf8_decoder_patched')}
        summary.update(output=str(release),zip=str(archive_path),patch_mode='BepInEx runtime plugin',
                       original_game_unchanged=report['original_game_unchanged'],utf8_decoder_patched=False,
                       font_replaced=False,font_runtime_substitution=True,
                       current_patch_report=str(p.WORK/'reports/bepinex_latest.json'))
        p.save(summary_path,summary)
    print('READY: '+str(archive_path))

if __name__=='__main__': main()
