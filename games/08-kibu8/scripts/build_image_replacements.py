"""Build game-eight named-image routes with shared manifest, texture and BepInEx layers."""
import argparse,io,json,re,shutil,struct,subprocess,sys,time
from pathlib import Path
from PIL import Image
import UnityPy
import pipeline as p
sys.path.insert(0,str(p.SERIES/'engine/bepinex'))
import build as shared
from image_resources import resource_inventory, scratch_image
sys.path.insert(0,str(p.SERIES/'engine/ui-assets'))
from ui_asset_catalog import resolve_asset, validate_source

def build_notebook_tab_alpha(inventory):
    """Apply the native left-corner cutout symmetrically to all four tab corners."""
    env=UnityPy.load(str(p.GAME/'kibu8_Data/resources.assets'))
    textures={o.path_id:o for o in env.objects if o.type.name=='Texture2D'}
    def source(name):
        return textures[inventory[(0,'/'+name)]['path_id']].read().image.convert('RGBA')
    person=source('memo_l01.gif'); note=source('memo_l02.gif')
    alpha=person.getchannel('A')
    if person.size!=(18,40) or note.size!=(18,32):
        raise ValueError('Unexpected native notebook tab dimensions')
    if alpha.crop((0,0,18,2)).tobytes()!=note.getchannel('A').crop((0,0,18,2)).tobytes() or alpha.crop((0,38,18,40)).tobytes()!=note.getchannel('A').crop((0,30,18,32)).tobytes():
        raise ValueError('Native notebook tab corner masks differ')
    # Localized paired tabs have a complete border: mirror the left cutouts
    # onto the right instead of inheriting the original paper-attached edge.
    for y in range(alpha.height):
        for x in range(alpha.width // 2):
            alpha.putpixel((alpha.width-1-x,y),alpha.getpixel((x,y)))
    if any(alpha.getpixel(corner)!=0 for corner in [(0,0),(17,0),(0,39),(17,39)]):
        raise ValueError('All four notebook tab corners must be transparent')
    background_path=p.WORK/'images/memo-bg-zh.png'
    background=Image.open(background_path).convert('RGBA')
    original_background=source('memo_bg.jpg')
    for name,y in [('memo-person-zh.png',13),('memo-tab-zh.png',55)]:
        path=p.WORK/'images'/name
        image=Image.open(path).convert('RGBA')
        if image.size!=alpha.size:raise ValueError('Localized notebook tab dimensions changed')
        rgb=image.convert('RGB').tobytes()
        image.putalpha(alpha)
        if image.convert('RGB').tobytes()!=rgb:raise ValueError('Tab artwork changed while restoring alpha')
        image.save(path)
        strip=image.crop((0,0,8,40))
        for sy in range(40):
            for sx in range(8):
                if strip.getpixel((sx,sy))[3]==0:
                    background.putpixel((8+sx,y+sy),original_background.getpixel((8+sx,y+sy)))
        background.alpha_composite(strip,(8,y))
        if image.getchannel('A').tobytes()!=alpha.tobytes():raise ValueError('Native tab transparency lost')
    background.save(background_path)
    p.save(p.WORK/'reports/notebook-tab-alpha.json',dict(native_mask='memo_l01.gif left half mirrored to right',four_corners_transparent=True,size=[18,40],transparent_pixels=sum(a==0 for a in alpha.getdata()),rgb_unchanged=True,hidden_strips_alpha_composited=True,runtime_tested=False))


def build_notebook_profiles(inventory):
    """Compile the localized common panel onto job-specific source backgrounds."""
    env=UnityPy.load(str(p.GAME/'kibu8_Data/resources.assets'))
    textures={o.path_id:o for o in env.objects if o.type.name=='Texture2D'}
    panel=Image.open(p.WORK/'images/memo-profile-zh.png').convert('RGBA')
    if panel.size!=(208,88):raise ValueError('Unexpected notebook panel dimensions')
    routes=[];evidence=[]
    for name in ('job_office','job_station','job_mole'):
        native=inventory[(0,'/'+name+'.gif')]
        for chapter in (1,2):
            if inventory[(chapter,'/'+name+'.gif')]['source_rgba_sha256']!=native['source_rgba_sha256']:
                raise ValueError('Notebook background differs between chapters')
        source=textures[native['path_id']].read().image.convert('RGBA')
        if source.size!=panel.size:raise ValueError('Notebook job background dimensions changed')
        image=source.copy()
        image.paste(panel.crop((100,0,208,88)),(100,0))
        if image.crop((0,0,100,88)).tobytes()!=source.crop((0,0,100,88)).tobytes():
            raise ValueError('Notebook scene pixels changed')
        if image.crop((100,0,208,88)).tobytes()!=panel.crop((100,0,208,88)).tobytes():
            raise ValueError('Notebook labels differ from localized common panel')
        output=p.WORK/('images/'+name+'-zh.png');image.save(output)
        routes.append(dict(id=name,png=output.name,size=[208,88],sources=[dict(loader='Image_createImage',name='/'+name+'.gif')]))
        evidence.append(dict(name=name,chapters=3,left_scene_unchanged=True,right_panel_matches_localized_template=True,source_sha256=native['source_rgba_sha256'],target_sha256=shared.sha(image.tobytes())))
    p.save(p.WORK/'reports/notebook-backgrounds.json',dict(entries=evidence,runtime_tested=False))
    return routes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',type=Path,default=p.WORK/'images/replacements.json')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    spec=json.loads(args.spec.read_text('utf-8-sig'))
    if spec.get('schema')!=1 or spec.get('game')!='kibu8': raise ValueError('Wrong image specification')
    from build_command_icons import build as build_commands
    from build_nameplates import build as build_names
    commands = build_commands() + build_names()
    spec['images'] = [entry for entry in spec['images'] if entry['id'] not in {x['id'] for x in commands}] + commands
    image_root=args.spec.resolve().parent
    inventory=resource_inventory(p.GAME/'kibu8_Data',3)
    build_notebook_tab_alpha(inventory)
    profiles=build_notebook_profiles(inventory)
    spec['images']=[entry for entry in spec['images'] if entry['id'] not in {x['id'] for x in profiles}]+profiles
    output=args.output or p.WORK/'out'/('images_'+time.strftime('%Y%m%d_%H%M%S'))
    package=output/'package'; plugin=package/'BepInEx/plugins/KibukawaImageReplacements'
    (plugin/'images').mkdir(parents=True,exist_ok=True)
    managed=p.GAME/'kibu8_Data/Managed'; scratch=p.GAME/'kibu8_Data/StreamingAssets/scratchpad'
    lines=['\t'.join(['KIMG1','kibu8',shared.sha((managed/'Assembly-CSharp.dll').read_bytes()),shared.sha(scratch.read_bytes())])]
    ids=set(); routes=set(); entries=[]
    for entry in spec['images']:
        ident=entry['id']
        if not re.fullmatch(r'[a-zA-Z0-9_-]+',ident) or ident in ids: raise ValueError('Invalid/duplicate id')
        ids.add(ident)
        shared_entry=None
        if 'sharedAsset' in entry:
            png,shared_entry=resolve_asset(entry['sharedAsset'])
        else:
            png=(image_root/entry['png']).resolve()
            if not png.is_relative_to(image_root): raise ValueError('Image path escapes image root')
        image=Image.open(png).convert('RGBA')
        if not (0<image.width<=1024 and 0<image.height<=1024): raise ValueError('Invalid image dimensions')
        if 'size' in entry and list(image.size)!=entry['size']: raise ValueError('Replacement dimensions mismatch')
        payload=b'KMAP'+struct.pack('<ii',*image.size)+image.tobytes()
        relative=f'images/{ident}.rgba'; (plugin/relative).write_bytes(payload)
        shutil.copyfile(png,plugin/'images'/f'{ident}.png')
        for route in entry['sources']:
            loader,name=route['loader'],route['name']
            if loader not in ('LoadGraphic','Image_createImage') or not name or any(c in name for c in '\t\r\n@'): raise ValueError('Invalid named route')
            if loader=='LoadGraphic' and '.' not in name: name+='.gif'
            chapter=route.get('appliIndex','*')
            if chapter!='*' and (type(chapter) is not int or not 0<=chapter<=2): raise ValueError('Invalid chapter selector')
            originals=([scratch_image(p.GAME/'kibu8_Data/StreamingAssets/scratchpad',name)] if loader=='LoadGraphic' else
                       [inventory.get((i,name)) for i in (range(3) if chapter=='*' else [chapter])])
            if any(x is None for x in originals):raise ValueError('Native resource route absent: '+name)
            if shared_entry is not None:
                for original in originals:validate_source(shared_entry,original)
            if any(x['size']!=entry.get('sourceSize',list(image.size)) for x in originals):raise ValueError('Replacement differs from actual source dimensions: '+name)
            if chapter=='*' and len({x['source_rgba_sha256'] for x in originals})!=1:raise ValueError('Different chapter images require explicit appliIndex')
            key=f'CanvasEx.{loader}#{chapter}@{name}'
            if key in routes: raise ValueError('Duplicate named route')
            routes.add(key)
            lines.append('\t'.join([ident,key,'0',relative,shared.sha(payload)]))
            entries.append(dict(id=ident,route=key,size=list(image.size),originals=originals,png_sha256=shared.sha(png.read_bytes()),payload_sha256=shared.sha(payload)))
    if not routes: raise ValueError('No image routes')
    (plugin/'image-replacements.tsv').write_text('\n'.join(lines)+'\n','utf-8')
    originals=sorted((p.GAME/'kibu8_Data').glob('resources.assets*'))+[p.GAME/'kibu8_Data/globalgamemanagers.assets']
    (plugin/'image-sources.sha256').write_text(''.join(shared.sha(x.read_bytes())+'  '+x.relative_to(p.GAME).as_posix()+'\n' for x in originals),'utf-8')
    cover=(image_root/spec.get('shellCover','titleimage-zh.png')).resolve()
    if not cover.is_relative_to(image_root):raise ValueError('Shell cover escapes image root')
    if Image.open(cover).size!=(354,354):raise ValueError('Shell cover must be 354x354')
    cover_env=UnityPy.load(str(p.GAME/'kibu8_Data/resources.assets'))
    cover_sources=[x for x in cover_env.objects if x.type.name=='Texture2D' and x.read().m_Name=='titleimage']
    if len(cover_sources)!=1:raise ValueError('Ambiguous original shell cover')
    cover_source=cover_sources[0].read()
    if cover_source.image.size!=(354,354):raise ValueError('Original shell cover size changed')
    cover_evidence=dict(path_id=cover_sources[0].path_id,source_data_sha256=shared.sha(bytes(cover_source.get_image_data())),
                        source_rgba_sha256=shared.sha(cover_source.image.convert('RGBA').tobytes()),target_sha256=shared.sha(cover.read_bytes()))
    shutil.copyfile(cover,plugin/'titleimage-zh.png')
    framework,dependency=shared.ensure_framework(p.SERIES/'engine/bepinex/locks/BepInEx-5.4.23.5-win-x64.json',p.SERIES/'cache/bepinex/mono-win-x64-5.4.23.5')
    common=p.SERIES/'engine/image-replacements'
    sources=[p.SERIES/'engine/adapters/gmode-v2/src/NamedImageRuntime.cs',common/'ReplacementManifest.cs',common/'TextureReplacement.cs',p.WORK/'bepinex/src/ImageReplacementPlugin.cs',p.WORK/'bepinex/images/ShellCover.cs',p.WORK/'bepinex/images/TitleMenuLayout.cs']
    refs=['mscorlib.dll','System.dll','System.Core.dll','netstandard.dll','UnityEngine.dll','UnityEngine.CoreModule.dll','UnityEngine.UI.dll','UnityEngine.ImageConversionModule.dll']
    shared.compile_plugin(framework,managed,plugin/'KibukawaImageReplacements.dll',sources,output/'compile.rsp',refs)
    menu_tests=subprocess.run(['pwsh','-NoProfile','-File',str(p.WORK/'bepinex/tests/Run-TitleMenuTests.ps1')],check=True,capture_output=True,text=True)
    print(menu_tests.stdout.strip())
    report=dict(game='kibu8',version='1.2.3',package=str(package),entries=entries,shell_cover=cover_evidence,runtime_visual_tested=False,title_menu_tests=menu_tests.stdout.strip(),
                source_hashes={x.relative_to(p.SERIES).as_posix():shared.sha(x.read_bytes()) for x in sources},
                package_files={x.relative_to(package).as_posix():shared.sha(x.read_bytes()) for x in package.rglob('*') if x.is_file()})
    (output/'build-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print('PASS: built named image replacement package:',package)

if __name__=='__main__': main()
