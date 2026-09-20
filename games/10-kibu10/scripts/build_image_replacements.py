"""Build tenth-game artwork using the shared named-image runtime and BepInEx compiler."""
import io,struct,sys,shutil
from pathlib import Path
from PIL import Image
import UnityPy
import pipeline as p
from build_ui_images import build as build_labels
from build_help_pages import build_help_pages
from build_title_components import compose
from build_title_panels import build as build_panels
from inspect_image_coverage import resource_inventory
sys.path.insert(0,str(p.SERIES/'engine/bepinex'))
import build as shared

def payload(path):
    im=Image.open(path).convert('RGBA')
    return b'KMAP'+struct.pack('<ii',*im.size)+im.tobytes()

def build(framework=None):
    output=p.WORK/'out/image-package';package=output/'package';plugin=package/'BepInEx/plugins/KibukawaImageReplacements'
    (plugin/'images').mkdir(parents=True,exist_ok=True);(plugin/'artwork').mkdir(exist_ok=True)
    if framework is None:
        framework,_=shared.ensure_framework(p.SERIES/'engine/bepinex/locks/BepInEx-5.4.23.5-win-x64.json',p.SERIES/'cache/bepinex/mono-win-x64-5.4.23.5')
    native=resource_inventory();scratch=dict(p.entries(p.bundle_text_assets('kibu10_Data/StreamingAssets/scratchpad')['scratch1.dat']))
    assembly=p.GAME/'kibu10_Data/Managed/Assembly-CSharp.dll';archive=p.GAME/'kibu10_Data/StreamingAssets/scratchpad'
    lines=['\t'.join(['KIMG1','kibu10',p.sha(assembly.read_bytes()),p.sha(archive.read_bytes())])];evidence=[]
    routes=build_labels()
    for panel in build_panels():shutil.copyfile(panel,plugin/'images'/panel.name)
    for entry in routes:
        png=p.WORK/'images'/entry['png'];data=payload(png);relative='images/'+entry['id']+'.rgba';(plugin/relative).write_bytes(data)
        for route in entry['sources']:
            name=route['name'];loader=route['loader']
            if loader=='Image_createImage': source=native[name]
            else:
                im=Image.open(io.BytesIO(scratch[name])).convert('RGBA');source=dict(size=list(im.size),source_rgba_sha256=p.sha(im.tobytes()))
            if source['size']!=entry['size']:raise ValueError('Image dimensions differ: '+name)
            key='CanvasEx.'+loader+'#*@'+name
            lines.append('\t'.join([entry['id'],key,'0',relative,p.sha(data)]))
            evidence.append(dict(route=key,source=source,png_sha256=p.sha(png.read_bytes()),payload_sha256=p.sha(data)))
    for key in ('t_start','t_help','t_append'):
        for level in (900,700,500,400,0):
            name=key+'-'+str(level);data=payload(p.WORK/'images/ui'/(name+'.png'));(plugin/'images'/(name+'.rgba')).write_bytes(data)
    (plugin/'image-replacements.tsv').write_text('\n'.join(lines)+'\n','utf-8')
    for key in ('t_start','t_help','t_append'):
        for suffix in ('','-900','-700','-500','-400','-0'):
            shutil.copyfile(p.WORK/'images/ui'/(key+suffix+'.png'),plugin/'images'/(key+suffix+'.png'))
    help_report=build_help_pages(plugin/'images')
    # Ship the game's own English logos without changing their pixels. Looking
    # through FindObjectsOfTypeAll at runtime only finds already-loaded assets.
    logo_objects={o.path_id:o for o in UnityPy.load(str(p.GAME/'kibu10_Data/resources.assets')).objects}
    logos=[]
    for path_id,name,size in [(55,'title_logo_archives_00_en',(352,44)),(23,'title_logo_archives_plus_00_en',(378,44))]:
        source=logo_objects[path_id].read()
        if source.m_Name!=name or (source.m_Width,source.m_Height)!=size:
            raise ValueError('English logo source changed: '+name)
        image=source.image.convert('RGBA');destination=plugin/'images'/(name+'.png');image.save(destination)
        if Image.open(destination).convert('RGBA').tobytes()!=image.tobytes():
            raise ValueError('English logo pixel round-trip failed: '+name)
        logos.append(dict(name=name,path_id=path_id,size=list(size),rgba_sha256=p.sha(image.tobytes()),png_sha256=p.sha(destination.read_bytes())))
    composed=compose()
    # Remove only known obsolete files from the local staging package.
    obsolete=plugin/'artwork/bg21-zh.png'
    if obsolete.exists():obsolete.unlink()
    art=[]
    for name,size in [('title1-zh.png',(240,240)),('title2-zh.png',(240,240)),('title-scratch-zh.png',(240,240)),('titleimage-zh.png',(354,354))]:
        path=composed/name;im=Image.open(path)
        if im.width<size[0] or im.height<size[1] or abs(im.width/im.height-size[0]/size[1])>.02:raise ValueError('Artwork cannot fit native viewport: '+name)
        if name in ('title1-zh.png','title2-zh.png'):
            source=native['/'+name.replace('-zh.png','.gif')]
            if source['size']!=list(size):raise ValueError('Native title dimensions changed')
        elif name in ('title-scratch-zh.png','bg21-zh.png'):
            source_name='title.gif' if name.startswith('title-') else 'bg21.jpg'
            source_image=Image.open(io.BytesIO(scratch[source_name])).convert('RGBA')
            if source_image.size!=size:raise ValueError('Native artwork dimensions changed')
            source=dict(name=source_name,size=list(size),source_rgba_sha256=p.sha(source_image.tobytes()))
        else:
            inventory=p.load(p.WORK/'images/inventory/inventory.json')
            covers=[x for x in inventory if x['name']=='titleimage']
            if not covers or any(x['size']!=list(size) for x in covers) or len({x['sha'] for x in covers})!=1:raise ValueError('Ambiguous shell cover')
            source=dict(name='titleimage',size=list(size),source_rgba_sha256=covers[0]['sha'])
        destination=plugin/name if name=='titleimage-zh.png' else plugin/'artwork'/name
        shutil.copyfile(path,destination);art.append(dict(file=name,sha256=p.sha(path.read_bytes()),generated_size=list(im.size),native_viewport=list(size),source=source))
    originals=sorted((p.GAME/'kibu10_Data').glob('resources.assets*'))+[p.GAME/'kibu10_Data/globalgamemanagers.assets']
    originals += [x for x in (p.GAME/'kibu10_Data/StreamingAssets').rglob('*') if x.is_file() and not x.name.endswith('.manifest')]
    (plugin/'image-sources.sha256').write_text(''.join(p.sha(x.read_bytes())+'  '+x.relative_to(p.GAME).as_posix()+'\n' for x in originals),'utf-8')
    common=p.SERIES/'engine/image-replacements'
    sources=[p.SERIES/'engine/adapters/gmode-v2/src/NamedImageRuntime.cs',common/'ReplacementManifest.cs',common/'TextureReplacement.cs',p.WORK/'bepinex/src/ImageReplacementPlugin.cs']+sorted((p.WORK/'bepinex/images').glob('*.cs'))
    references=['mscorlib.dll','System.dll','System.Core.dll','netstandard.dll','UnityEngine.dll','UnityEngine.CoreModule.dll','UnityEngine.UI.dll','UnityEngine.ImageConversionModule.dll']
    shared.compile_plugin(framework,p.GAME/'kibu10_Data/Managed',plugin/'KibukawaImageReplacements.dll',sources,output/'compile.rsp',references)
    report=dict(game='kibu10',named_routes=evidence,brightness_routes=12,artwork=art,help=help_report,english_logos=logos,runtime_visual_tested=False,shared_runtime='engine/adapters/gmode-v2/src/NamedImageRuntime.cs',source_hashes={x.relative_to(p.SERIES).as_posix():p.sha(x.read_bytes()) for x in sources})
    p.save(p.WORK/'reports/images_latest.json',report)
    files={x.relative_to(package).as_posix():x for x in package.rglob('*') if x.is_file()}
    print('PASS: tenth-game image package:',len(evidence),'named routes, 12 brightness variants, 4 composed titles, original bg21, 4 help pages')
    return files

if __name__=='__main__':build()
