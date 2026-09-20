"""Inventory every decoded image and bind tenth-game named resources by serialized pointers."""
import io,json,struct,zipfile
from PIL import Image,ImageDraw
import UnityPy
import pipeline as p

def resource_inventory():
    data=p.GAME/'kibu10_Data'; env=UnityPy.load(*map(str,data.glob('resources.assets*')))
    objects={o.path_id:o for o in env.objects}
    scripts={o.path_id:o.read().m_ClassName for o in UnityPy.load(str(data/'globalgamemanagers.assets')).objects if o.type.name=='MonoScript'}
    parents={};transforms={}
    for o in env.objects:
        if o.type.name in ('Transform','RectTransform'):
            v=o.read();parents[o.path_id]=v.m_Father.path_id;transforms[v.m_GameObject.path_id]=o.path_id
    roots=[];resources=[]
    for o in env.objects:
        if o.type.name!='MonoBehaviour':continue
        raw=o.get_raw_data()
        if len(raw)<32:continue
        sf,si=struct.unpack_from('<iq',raw,16)
        if sf!=1:continue
        kind=scripts.get(si)
        if kind not in ('Resources','ResourcesManager'):continue
        nl=struct.unpack_from('<i',raw,28)[0];pos=(32+nl+3)&~3
        if kind=='ResourcesManager':
            # Verified difference: one root pointer, not eighth game's root list.
            if len(raw)!=pos+12:raise ValueError('Unknown resource manager layout')
            f,root=struct.unpack_from('<iq',raw,pos)
            if f:raise ValueError('External root')
            roots.append(root);continue
        count=struct.unpack_from('<i',raw,pos)[0];pos+=4
        if count!=1 or len(raw)!=pos+12:raise ValueError('Unknown resource layout')
        f,target=struct.unpack_from('<iq',raw,pos)
        if f:raise ValueError('External named resource')
        resources.append((struct.unpack_from('<q',raw,4)[0],target))
    if len(roots)!=1:raise ValueError('Ambiguous resource root')
    result={}
    for go,target in resources:
        t=transforms[go];ancestors=[]
        while t:ancestors.append(objects[t].read().m_GameObject.path_id);t=parents[t]
        if roots[0] not in ancestors:raise ValueError('Resource outside verified root')
        if objects[target].type.name!='Texture2D':continue
        tex=objects[target].read();im=tex.image.convert('RGBA');name='/'+objects[go].read().m_Name
        if name in result:raise ValueError('Duplicate native route')
        result[name]=dict(path_id=target,size=list(im.size),source_rgba_sha256=p.sha(im.tobytes()))
    return result

def main():
    out=p.WORK/'images/inventory';out.mkdir(parents=True,exist_ok=True);records=[];skipped=[]
    data=p.GAME/'kibu10_Data'
    bundles=[data/'resources.assets']+[x for x in (data/'StreamingAssets').rglob('*') if x.is_file() and not x.name.endswith('.manifest')]
    for bundle in bundles:
        env=UnityPy.load(*map(str,data.glob('resources.assets*'))) if bundle.name=='resources.assets' else UnityPy.load(str(bundle))
        for o in env.objects:
            if o.type.name!='Texture2D':continue
            t=o.read()
            if t.m_Width==0 or t.m_Height==0:
                skipped.append(dict(bundle=bundle.relative_to(data).as_posix(),name=t.m_Name,reason='zero-size dynamic font atlas'));continue
            im=t.image.convert('RGBA');ident=len(records);filename=f'{ident:03d}-'+t.m_Name.replace('/','_')+'.png';im.save(out/filename)
            records.append(dict(id=ident,name=t.m_Name,file=filename,size=list(im.size),path_id=o.path_id,bundle=bundle.relative_to(data).as_posix(),sha=p.sha(im.tobytes())))
    for container,raw in p.bundle_text_assets('kibu10_Data/StreamingAssets/scratchpad').items():
        if container.endswith('.jar'):
            z=zipfile.ZipFile(io.BytesIO(raw));members=[(n,z.read(n)) for n in z.namelist()]
        else:members=p.entries(raw)
        for name,raw in members:
            try:im=Image.open(io.BytesIO(raw)).convert('RGBA')
            except Exception:continue
            ident=len(records);filename=f'{ident:03d}-'+name.replace('/','_')+'.png';im.save(out/filename)
            records.append(dict(id=ident,name=name,file=filename,size=list(im.size),container=container,sha=p.sha(im.tobytes())))
    p.save(out/'inventory.json',records);p.save(out/'skipped.json',skipped);p.save(out/'named-resources.json',resource_inventory())
    for start in range(0,len(records),64):
        sheet=Image.new('RGB',(1440,1240),'#888888');d=ImageDraw.Draw(sheet)
        for i,r in enumerate(records[start:start+64]):
            im=Image.open(out/r['file']);im.thumbnail((174,125));x=i%8*180;y=i//8*155;sheet.paste(im,(x,y),im);d.text((x,y+127),str(r['id'])+' '+r['name'][:24],fill='white')
        sheet.save(out/f'sheet-{start//64}.jpg')
    print('Inventoried',len(records),'images;',len(skipped),'zero-size atlases;',len(resource_inventory()),'named routes')

if __name__=='__main__':main()
