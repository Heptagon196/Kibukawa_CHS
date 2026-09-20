"""Split original title assets and compose with shared artistic-lettering components."""
from PIL import Image
import pipeline as p
from title_art_parts import tile, MASTER
from build_ui_images import build, MENUS

SERIES_TEXT='侦探·癸生川凌介事件谭'
MENU_POS={'t_start':(82,37),'t_help':(57,37),'t_append':(31,38)}
SOURCES={'title1-zh.png':'042-title1.png','title2-zh.png':'065-title2.png','title-scratch-zh.png':'333-title.gif.png','titleimage-zh.png':'008-titleimage.png'}

def compose():
    build();out=p.WORK/'images/composed';parts=out/'parts';parts.mkdir(parents=True,exist_ok=True)
    caption=tile('caption',(16,156));caption.save(parts/'series-caption.png')
    after=tile('after',(18,40));after.save(parts/'after-part.png')
    records=[]
    for name,source in SOURCES.items():
        original=Image.open(p.WORK/'images/inventory'/source).convert('RGBA');base=original.copy();rects=[]
        if original.size==(240,240):
            # One whole generated master supplies every common pixel, including
            # all lettering. Only footer/part label differ between versions.
            base=Image.open(MASTER).convert('RGBA').resize((240,240),Image.Resampling.LANCZOS)
            rects=[(84,173,109,220),(0,220,240,240)]
            for rect in rects[:2]:base.paste((0,0,0,255),rect)
            base.save(parts/(name+'.base.png'))
            footer=original.crop((0,220,240,240));footer.save(parts/(name+'.footer.png'));base.paste(footer,(0,220))
            if name=='title2-zh.png':base.paste(after,(87,176))
        else:
            rects=[(246,18,275,237)]
            base.paste((0,0,0,255),rects[0]);base.save(parts/(name+'.base.png'))
            cover_caption=Image.new('RGBA',(29,219),(0,0,0,255));cover_caption.paste(caption.resize((21,205),Image.Resampling.LANCZOS),(4,0))
            cover_caption.save(parts/'cover-caption.png');base.paste(cover_caption,(246,18))
        base.save(out/name)
        # Covers retain their own original composition. The three game titles
        # are checked below against one another, not against the old Japanese art.
        if original.size!=(240,240):
            for y in range(original.height):
                for x in range(original.width):
                    if not any(l<=x<r and t<=y<b for l,t,r,b in rects):
                        assert base.getpixel((x,y))==original.getpixel((x,y)),(name,x,y)
        records.append(dict(file=name,source=source,size=list(base.size),localized_rectangles=rects,sha256=p.sha((out/name).read_bytes()),original_footer_preserved=True))
    titles=[Image.open(out/n).convert('RGBA') for n in list(SOURCES)[:3]]
    for y in range(220):
        for x in range(240):
            if 84<=x<109 and 173<=y<220:continue
            assert len({im.getpixel((x,y)) for im in titles})==1,(x,y)
    p.save(out/'composition.json',dict(method='One complete title master; shared artistic text components and identical common pixels across 3 variants; original per-version footers; bg21 untouched',master_sha256=p.sha(MASTER.read_bytes()),menus=MENU_POS,artwork=records,bg21='Original retained; no replacement route'))
    return out

if __name__=='__main__':print(compose())
