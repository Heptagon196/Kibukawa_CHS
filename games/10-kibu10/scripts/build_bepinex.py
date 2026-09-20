"""Build tenth-game translation through shared BepInEx infrastructure."""
import argparse
import subprocess
import sys
import time
import pipeline as p
sys.path.insert(0,str(p.SERIES/'engine/bepinex'))
import build as shared
sys.path.insert(0,str(p.WORK/'scripts'))

def draft_hashes():
    paths=[p.WORK/name for name in ('work/dialogue-tagged.json','work/glossary.locked.json',
        'work/click_boundaries.reviewed.json','research/color-spans.reviewed.json')]
    paths += list((p.WORK/'work').glob('ui-*.zh-CN.json'))
    paths += [p.SERIES/'series/glossary.json']
    return {path.relative_to(p.SERIES).as_posix():p.sha(path.read_bytes()) for path in paths if path.exists()}

def runtime_sources():
    generated=p.WORK/'bepinex/build/generated'
    generated.mkdir(parents=True,exist_ok=True)
    text=(p.SERIES/'engine/adapters/gmode-20050817/RuntimePack.cs').read_text(encoding='utf-8-sig')
    before='entry.opcode!=17 && entry.opcode!=80'
    p.require(text.count(before)==1,'Eighth RuntimePack opcode validation changed')
    (generated/'RuntimePack.cs').write_text(text.replace(before,'entry.opcode!=17 && entry.opcode!=73 && entry.opcode!=80'),encoding='utf-8')
    (generated/'NativePaginationData.cs').write_text('using System.Collections.Generic; namespace Kibukawa.Engine.Gmode20050817 { internal static class NativePaginationData { internal static readonly Dictionary<string,int[][]> Groups = new Dictionary<string,int[][]>(); } }',encoding='utf-8')
    sources=list(generated.glob('*.cs'))
    sources += [p.SERIES/'engine/core'/n for n in ('TranslationCatalog.cs','TranslationPackReader.cs')]
    sources += [p.SERIES/'engine/adapters/gmode-20050817/src'/n for n in ('CanvasRuntime.cs','RuntimeLayout.cs','NativeDialogueLayout.cs','NativeChoiceMemory.cs','NativePagination.cs','NativeMenuPosition.cs')]
    sources += [p.PROJECT['adapter_path']/'src'/n for n in ('DirectCanvasRuntime.cs','DirectChoiceMemory.cs','DirectTextLayout.cs')]
    sources += [p.SERIES/'engine/adapters/gmode-v2/src'/n for n in ('BitmapFontAtlas.cs','LegacyFontRenderer.cs','PageMemory.cs','TextBreaks.cs','MenuMemory.cs','TextGeometry.cs')]
    sources += [p.SERIES/'engine/adapters/gmode-v2/ui/src/UiLocalizationRuntime.cs']
    sources += [p.WORK/'bepinex/src'/n for n in ('Plugin.cs','UiLocalization.cs','UiLocalizationData.cs','ScriptIdentityData.cs')]
    return sources

def main():
    if '--probe' in sys.argv:
        from build_probe import main as probe
        return probe()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke',action='store_true',help='Development only: incomplete text remains original')
    parser.add_argument('--compile-only',action='store_true')
    args=parser.parse_args()
    manifest=p.validate_sources()
    before=p.game_hashes()
    prior=p.first_project_hashes()
    draft_before=draft_hashes()
    if not args.smoke:
        from translation import collect
        from translation_review import check
        audit=collect()
        p.require(audit['pending']==0 and not audit['findings'],'Incomplete draft or unresolved language findings')
        check(strict=True)
    from build_pack import build
    from build_pixel_font import build_font
    output=p.WORK/'bepinex/build/plugin'
    text_report=build(smoke=args.smoke,output=output)
    font_report=build_font(output=output)
    config=p.load(p.WORK/'project.json')['bepinex']
    profile=p.load(p.SERIES/'engine/bepinex/profiles'/(config['profile']+'.json'))
    framework,dependency=shared.ensure_framework(p.SERIES/'engine/bepinex/locks'/profile['lock'],p.SERIES/'cache/bepinex'/config['profile'])
    sources=runtime_sources()
    refs=list(config['references'])+['UnityEngine.IMGUIModule.dll']
    shared.compile_plugin(framework,p.GAME/config['managed'],output/config['assembly'],sources,p.WORK/'bepinex/build/compile.rsp',refs)
    if args.compile_only:
        subprocess.run([p.shell(),'-NoProfile','-File',str(p.WORK/'bepinex/tests/Run-DirectPackBindingTests.ps1')],check=True)
        p.require(before==p.game_hashes() and prior==p.first_project_hashes(),'Protected-file hashes changed during build; check concurrent external changes')
        p.require(draft_before==draft_hashes(),'Draft changed during build; rebuild current reviewed version')
        print('COMPILED (smoke='+str(args.smoke)+'): '+str(output/config['assembly']))
        return
    from verify_all import verify
    verification=verify(smoke=args.smoke)
    from build_history import build as build_history
    from build_image_replacements import build as build_images
    auxiliary={}
    auxiliary.update(build_history(framework=framework))
    auxiliary.update(build_images(framework=framework))
    prefix='BepInEx/plugins/'+config['plugin_directory']+'/'
    payload={prefix+name:output/name for name in (config['assembly'],'translations.bin','sources.sha256')}
    for directory in ('fonts','licenses'):
        for file in (output/directory).rglob('*'):
            if file.is_file() and file.suffix.lower() in ('.png','.bin','.txt'):
                payload[prefix+file.relative_to(output).as_posix()]=file
    for name,path in auxiliary.items():
        p.require(name not in payload,'Duplicate package payload '+name)
        payload[name]=path
    required=p.load(p.SERIES/'series.json')['required_plugins']
    p.require(all(n in payload for n in required.values()),'Missing mandatory image/history plugin')
    payload['README_Kibu10_CHS.txt']=p.WORK/'bepinex/README_PATCH.txt'
    payload['BepInEx/licenses/BepInEx-LICENSE.txt']=p.SERIES/'engine/bepinex/licenses/BepInEx-LICENSE.txt'
    label='SMOKE_NOT_RELEASE' if args.smoke else 'CHS'
    release=p.WORK/'out'/(label+'_'+time.strftime('%Y%m%d_%H%M%S')+'_'+str(time.time_ns()%1000000000))
    package=release/'package'
    p.require(draft_before==draft_hashes(),'Draft changed during build; rebuild current reviewed version')
    shared.stage_package(package,framework,dependency,payload,set(before))
    archive=release/('Kibu10_'+label+'.zip')
    shared.archive_package(package,archive)
    p.require(before==p.game_hashes() and prior==p.first_project_hashes(),'Protected-file hashes changed during build; check concurrent external changes')
    p.require(draft_before==draft_hashes(),'Draft changed during build; rebuild current reviewed version')
    report=dict(schema=1,smoke=args.smoke,release_ready=not args.smoke,runtime_tested=False,
                archive=archive.relative_to(p.WORK).as_posix(),archive_sha256=p.sha(archive.read_bytes()),
                runtime_pack=text_report,font=font_report,dependency=dependency,verification=verification,original_game_unchanged=True,
                images=p.load(p.WORK/'reports/images_latest.json'),history=p.load(p.WORK/'reports/history-build.json'),
                previous_translation_work_unchanged=True,immutable_script_offsets=True,
                protection_scope='Hashes compared immediately before and after this build interval only; does not claim other concurrent tasks made no changes during the session.',
                source_fingerprints=manifest['source_hashes'],
                reviewed_input_hashes=draft_before,
                shared_builder_sha256=p.sha((p.SERIES/'engine/bepinex/build.py').read_bytes()),
                required_plugins=required,
                package_files={f.relative_to(package).as_posix():p.sha(f.read_bytes()) for f in package.rglob('*') if f.is_file()},
                sources={f.relative_to(p.SERIES).as_posix():p.sha(f.read_bytes()) for f in sources})
    p.save(release/'build_report.json',report)
    p.save(p.WORK/'reports'/('build_smoke_latest.json' if args.smoke else 'build_latest.json'),report)
    print('BUILT '+str(archive))

if __name__=='__main__': main()
