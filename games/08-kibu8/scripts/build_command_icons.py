"""Rebuild command labels from editable, pinned 10px BDF glyphs at native pixels."""
import io, zipfile, sys
from pathlib import Path
from PIL import Image
import pipeline as p
from build_pixel_font import parse_bdf, dependency
from command_icons import render_command
from image_resources import scratch_resources

sys.path.insert(0,str(p.SERIES/'engine/ui-assets'))
from ui_asset_catalog import resolve_asset, validate_source
LABELS = tuple(resolve_asset(f'classic-240/cmd{i}')[1]['text'] for i in range(10))

def build():
    lock=p.load(p.WORK/'bepinex/fusion-icon-font-dependency.lock.json')
    with zipfile.ZipFile(dependency(lock['dependencies']['bdf'])) as z:
        glyphs=parse_bdf(z.read('fusion-pixel-10px-monospaced-zh_hans.bdf'),(5,10))
        license_root=p.WORK/'bepinex/build/plugin/licenses/FusionPixelIcons'
        for name in z.namelist():
            if name=='OFL.txt' or name.startswith('LICENSES/') and not name.endswith('/'):
                target=license_root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
    sources=scratch_resources(p.GAME/'kibu8_Data/StreamingAssets/scratchpad')
    background_path,_=resolve_asset('classic-240/command-backgrounds')
    blank=Image.open(background_path).convert('RGBA')
    if blank.size!=(96,120):raise ValueError('Command background atlas dimensions changed')
    routes=[];report=[]
    for index,label in enumerate(LABELS):
        name=f'cmd{index}.gif';source=Image.open(io.BytesIO(sources[name])).convert('RGBA')
        left=(index%2)*48;top=(index//2)*24
        image=render_command(source,blank.crop((left,top,left+48,top+24)),label,glyphs)
        output,asset=resolve_asset(f'classic-240/cmd{index}')
        validate_source(asset,dict(size=list(source.size),source_rgba_sha256=p.sha(source.tobytes())))
        if image.tobytes()!=Image.open(output).convert('RGBA').tobytes():
            raise ValueError('Generated command differs from approved shared artwork')
        routes.append(dict(id=f'cmd{index}',sharedAsset=f'classic-240/cmd{index}',size=[48,24],sources=[dict(loader='LoadGraphic',name=name,appliIndex='*')]))
        report.append(dict(id=index,source=name,target=label,source_sha256=p.sha(sources[name]),target_sha256=p.sha(output.read_bytes()),states=2,upper_pictogram_unchanged=True,outlined_labels=True,background_sha256=p.sha(background_path.read_bytes())))
    notice=license_root/'NOTICE.txt'
    notice.write_text('Command image labels only: native 10px Fusion Pixel 2026.07.20 by TakWolf, OFL-1.1. Runtime 12px text continues to use Z Labs. Pinned source download: fusion-icon-font-dependency.lock.json.\n',encoding='utf-8')
    p.save(p.WORK/'reports/command-icons.json',dict(entries=report,dependency=lock,native_glyphs=True))
    return routes

if __name__=='__main__':build()
