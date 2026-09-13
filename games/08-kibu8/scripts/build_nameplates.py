"""Localize embedded MO account-name artwork using the shared sprite compiler."""
import io
from PIL import Image
import pipeline as p
from image_resources import scratch_resources
from nameplates import load_font,render_nameplate
LABELS={'ain':'艾纳','arm':'阿尔马达','bre':'布雷特','cat':'猫猫','kam':'卡姆拉','rio':'莉绪','yuk':'雪海豚'}
def build():
    source=scratch_resources(p.GAME/'kibu8_Data/StreamingAssets/scratchpad')
    glyphs=load_font(p.WORK/'bepinex/build/plugin/fonts/ui-12');routes=[];evidence=[]
    for prefix,label in LABELS.items():
        name=prefix+'_000.gif';im=Image.open(io.BytesIO(source[name])).convert('RGBA')
        image,check=render_nameplate(im,label,glyphs);out=p.WORK/'images'/(prefix+'-name-zh.png');image.save(out)
        routes.append(dict(id=prefix+'-name',png=out.name,size=list(image.size),sources=[dict(loader='LoadGraphic',name=name,appliIndex='*')]))
        evidence.append(dict(source=name,label=label,source_sha256=p.sha(source[name]),**check))
    p.save(p.WORK/'reports/account-nameplates.json',dict(entries=evidence,font='Z Labs Pixel 12px',runtime_tested=False))
    return routes
