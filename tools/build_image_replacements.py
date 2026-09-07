"""Compile configurable native-image replacement packs; original game assets stay untouched."""
import argparse, io, json, os, re, shutil, struct, subprocess, sys, zipfile
from pathlib import Path
import UnityPy
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
VERSION='1.1.0'
OUT=ROOT/'out'/('image-replacements-'+VERSION)
sys.path.insert(0,str(ROOT/'engine/bepinex'))
import build as shared

def read_frames(data):
    offset=1; frames=[]
    for _ in range(data[0]):
        length=int.from_bytes(data[offset:offset+2],'big');offset+=2
        frames.append(data[offset:offset+length]);offset+=length
    if offset!=len(data): raise ValueError('Packed image member length mismatch')
    return frames

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',default='all')
    args=parser.parse_args()
    series=json.loads((ROOT/'series.json').read_text('utf-8'))['games']
    games=list(series) if args.game=='all' else [args.game]
    OUT.mkdir(parents=True,exist_ok=True)
    framework,_=shared.ensure_framework(ROOT/'engine/bepinex/locks/BepInEx-5.4.23.5-win-x64.json',ROOT/'cache/bepinex/mono-win-x64-5.4.23.5')
    source=ROOT/'engine/image-replacements'
    compiler=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    tests=OUT/'TextureReplacementTests.exe'
    subprocess.run([str(compiler),'/nologo','/target:exe','/out:'+str(tests),str(source/'TextureReplacement.cs'),str(source/'TextureReplacementTests.cs')],check=True)
    subprocess.run([str(tests)],check=True)
    manifest_tests=OUT/'ManifestTests.exe'
    subprocess.run([str(compiler),'/nologo','/target:exe','/out:'+str(manifest_tests),str(source/'ReplacementManifest.cs'),str(source/'ManifestTests.cs')],check=True)
    reports=[]
    for game in games:
        config=series[game]; project=ROOT/config['project']; installation=(ROOT/config['installation']).resolve()
        spec_path=project/'images/replacements.json'
        spec=json.loads(spec_path.read_text('utf-8-sig'))
        if spec['schema']!=1 or spec['game']!=game: raise ValueError('Wrong image replacement specification')
        image_root=(project/'images').resolve()
        scratchpad=installation/f'{game}_Data/StreamingAssets/scratchpad'
        bundle=UnityPy.load(str(scratchpad))
        archives={o.read().m_Name:o.read().m_Script.encode('utf-8','surrogateescape') for o in bundle.objects if o.type.name=='TextAsset'}
        managed=installation/f'{game}_Data/Managed'
        package=OUT/game/'package'; plugin=package/'BepInEx/plugins/KibukawaImageReplacements'
        (plugin/'images').mkdir(parents=True,exist_ok=True)
        lines=['\t'.join(['KIMG1',game,shared.sha((managed/'Assembly-CSharp.dll').read_bytes()),shared.sha(scratchpad.read_bytes())])]
        routes=set(); ids=set(); entries=[]
        for entry in spec['images']:
            ident=entry['id']
            if not re.fullmatch(r'[a-zA-Z0-9_-]+',ident) or ident in ids: raise ValueError('Invalid/duplicate image id')
            ids.add(ident)
            png=(image_root/entry['png']).resolve()
            if not png.is_relative_to(image_root): raise ValueError('Image path leaves project images directory')
            im=Image.open(png).convert('RGBA')
            if not (0<im.width<=1024 and 0<im.height<=1024): raise ValueError('Unsupported image size')
            payload=b'KMAP'+struct.pack('<ii',*im.size)+im.tobytes()
            payload_name=f'images/{ident}.rgba'
            (plugin/payload_name).write_bytes(payload)
            shutil.copyfile(png,plugin/'images'/f'{ident}.png')
            for route in entry['sources']:
                with zipfile.ZipFile(io.BytesIO(archives[route['archive']])) as archive:
                    if route['member'] not in ('gif1','gif2'): raise ValueError('Only native gif1/gif2 image tables are supported')
                    frames=read_frames(archive.read(route['member']))
                    original=frames[route['index']]
                    if not original: raise ValueError('Cannot replace an empty native image')
                    if Image.open(io.BytesIO(original)).size!=im.size: raise ValueError('Replacement must match original dimensions')
                    native_index=route['index']+(archive.read('gif1')[0] if route['member']=='gif2' else 0)
                key=(route['canvas'],native_index)
                if key in routes: raise ValueError('Duplicate image route')
                # This slot is owned by the existing kibu2 floor-plan translator.
                if game=='kibu2' and key==('CanvasEx',10): raise ValueError('kibu2 CanvasEx:10 is reserved for the existing floor-plan replacement')
                routes.add(key)
                lines.append('\t'.join([ident,route['canvas'],str(native_index),payload_name,shared.sha(payload)]))
                entries.append(dict(id=ident,canvas=route['canvas'],index=native_index,source=route,
                                    original_sha256=shared.sha(original),size=list(im.size),payload_sha256=shared.sha(payload)))
        (plugin/'image-replacements.tsv').write_text('\n'.join(lines)+'\n','utf-8')
        refs=['mscorlib.dll','System.dll','System.Core.dll','netstandard.dll','UnityEngine.dll','UnityEngine.CoreModule.dll']
        shared.compile_plugin(framework,managed,plugin/'KibukawaImageReplacements.dll',
                              [source/'ReplacementManifest.cs',source/'TextureReplacement.cs',source/'ImageReplacementPlugin.cs'],OUT/game/'compile.rsp',refs)
        subprocess.run([str(manifest_tests),str(plugin/'image-replacements.tsv')],check=True)
        readme=f'''癸生川系列通用图片替换插件 {VERSION} — {game}

先安装该作 BepInEx 汉化补丁，再合并本包 BepInEx 文件夹到游戏目录。
本包只替换明确配置的图片，第二作原有楼层图/帮助页替换保持不动。
通用配置源：各作 images/replacements.json。使用 tools/build_image_replacements.py 构建。
采用第二作楼层图的 ReadImg 后置替换、独立无 mipmap 纹理与原图回退。
已通过离线测试；各作游戏窗口验证状态见工作区报告。
本地化衍生图像的原作权利归原权利人，非代码 MIT 许可范围。
'''
        (package/'README_通用图片替换.txt').write_text(readme,'utf-8-sig')
        zip_path=OUT/f'{game}-通用图片替换-{VERSION}.zip'
        shared.archive_package(package,zip_path)
        audited=list(source.glob('*.cs'))+[Path(__file__).resolve(),ROOT/'tools/validate_image_replacements.ps1',spec_path]
        audited.extend((image_root/item['png']).resolve() for item in spec['images'])
        reports.append(dict(game=game,version=VERSION,routes=entries,assembly_sha256=lines[0].split('\t')[2],
                            scratchpad_sha256=shared.sha(scratchpad.read_bytes()),spec_sha256=shared.sha(spec_path.read_bytes()),
                            source_hashes={path.relative_to(ROOT).as_posix():shared.sha(path.read_bytes()) for path in audited},
                            shared_builder_sha256=shared.sha((ROOT/'engine/bepinex/build.py').read_bytes()),
                            package_files={path.relative_to(package).as_posix():shared.sha(path.read_bytes()) for path in package.rglob('*') if path.is_file()},
                            package=str(zip_path),package_sha256=shared.sha(zip_path.read_bytes()),runtime_visual_tested=False))
    runtime=json.loads((ROOT/'runtime.json').read_text('utf-8')) if (ROOT/'runtime.json').exists() else {}
    pwsh=runtime.get('pwsh') or shutil.which('pwsh')
    if not pwsh: raise RuntimeError('PowerShell 7 is required to validate the original image API')
    subprocess.run([pwsh,'-NoProfile','-File',str(ROOT/'tools/validate_image_replacements.ps1'),'-Game',args.game],check=True)
    (OUT/'build-report.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),'utf-8')
    print('PASS: built configurable image replacement packs:',OUT)

if __name__=='__main__':main()
