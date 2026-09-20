"""Deterministic title-menu labels while retaining native small artwork."""
from pathlib import Path
from PIL import Image
import pipeline as p
from title_art_parts import tile

NATIVE_NAMEPLATES = {'name00': '工藤貴樹', 'name01': '石上雅人', 'name02': '妹浦澄佳', 'name03': '白鷺洲伊綱', 'name04': '???'}
NATIVE_STATUS_LABELS = {'sell_end1': 'CLEARED'}
MENUS = {'t_start': ('开始', (16, 67)), 't_help': ('玩法说明', (17, 86)), 't_append': ('附加内容', (17, 51))}

def build():
    out=p.WORK/'images/ui'; out.mkdir(parents=True,exist_ok=True)
    # These labels remain native: a partial glyph swap or a complete redraw both
    # differ visibly from the original point artwork. Remove stale generated files
    # so an incremental build cannot accidentally package an older replacement.
    for key in tuple(NATIVE_NAMEPLATES)+tuple(NATIVE_STATUS_LABELS):
        stale=out/(key+'.png')
        if stale.exists(): stale.unlink()
    routes=[]; evidence=[]
    for key,(text,size) in MENUS.items():
        for level in (1024,900,700,500,400,0):
            color=(160,0,0,255) if level==0 else (level*255//1024,)*3+(255,)
            im=tile(key,size,color)
            suffix='' if level==1024 else '-'+str(level)
            file=out/(key+suffix+'.png');im.save(file)
            evidence.append(dict(id=key+suffix,text=text,size=list(size),brightness=level,sha256=p.sha(file.read_bytes())))
            if level==1024: routes.append(dict(id=key,png='ui/'+file.name,size=list(size),sources=[dict(loader='LoadGraphic',name=key+'.gif'),dict(loader='Image_createImage',name='/'+key+'.gif')]))
    p.save(p.WORK/'images/ui-labels.reviewed.json',dict(schema=3,game='kibu10',source='Character nameplates and the CLEARED badge retain complete native images; all title-menu lettering uses one shared artistic master title2-zh.png',native_nameplates=[dict(id=key,text=text,disposition='retain_complete_native_image') for key,text in NATIVE_NAMEPLATES.items()],native_status_labels=[dict(id=key,text=text,disposition='retain_complete_native_image') for key,text in NATIVE_STATUS_LABELS.items()],entries=evidence))
    return routes

if __name__=='__main__': build()
