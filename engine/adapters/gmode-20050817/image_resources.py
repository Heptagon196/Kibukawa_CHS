"""Verified named resource layout for the 20050817 Unity wrapper."""
import io, struct, hashlib, sys
from pathlib import Path
import UnityPy
from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[1] / 'gmode-v2'))
import vm_frame as frame

def sha(data):
    return hashlib.sha256(data).hexdigest()

def resource_inventory(data, chapter_count):
    """Resolve the real resourceRootList/AppliIndex routing; never infer from texture names."""
    env=UnityPy.load(str(data/'resources.assets'))
    script_env=UnityPy.load(str(data/'globalgamemanagers.assets'))
    scripts={x.path_id:x.read().m_ClassName for x in script_env.objects if x.type.name=='MonoScript'}
    objects={x.path_id:x for x in env.objects}
    parents={}; transforms={}
    for obj in env.objects:
        if obj.type.name in ('Transform','RectTransform'):
            value=obj.read();parents[obj.path_id]=value.m_Father.path_id;transforms[value.m_GameObject.path_id]=obj.path_id
    managers=[]; resources=[]
    for obj in env.objects:
        if obj.type.name!='MonoBehaviour': continue
        raw=obj.get_raw_data()
        if len(raw)<32: continue
        script_file,script_id=struct.unpack_from('<iq',raw,16)
        if script_file!=1: continue
        kind=scripts.get(script_id)
        if kind not in ('Resources','ResourcesManager'): continue
        name_length=struct.unpack_from('<i',raw,28)[0]
        pos=(32+name_length+3)&~3
        count=struct.unpack_from('<i',raw,pos)[0];pos+=4
        if count<0 or len(raw)!=pos+12*count: raise ValueError('Unexpected resource serialization layout')
        ptrs=[struct.unpack_from('<iq',raw,pos+12*i) for i in range(count)]
        if any(f!=0 for f,_ in ptrs): raise ValueError('External resource pointer needs explicit support')
        if kind=='ResourcesManager':managers.append([i for _,i in ptrs])
        else:resources.append((struct.unpack_from('<q',raw,4)[0],[i for _,i in ptrs]))
    if len(managers)!=1 or len(managers[0])!=chapter_count:raise ValueError('Unverified chapter resource root list')
    result={}
    for go,ptrs in resources:
        t=transforms[go];ancestor=[]
        while t:
            ancestor.append(objects[t].read().m_GameObject.path_id);t=parents[t]
        chapters=[i for i,root in enumerate(managers[0]) if root in ancestor]
        if not chapters:continue
        if len(chapters)!=1 or len(ptrs)!=1:raise ValueError('Ambiguous native resource')
        obj=objects[ptrs[0]]
        if obj.type.name!='Texture2D':continue
        tex=obj.read();image=tex.image.convert('RGBA')
        result[(chapters[0],'/'+objects[go].read().m_Name)]=dict(path_id=obj.path_id,size=list(image.size),
            source_data_sha256=sha(bytes(tex.get_image_data())),source_rgba_sha256=sha(image.tobytes()))
    return result

def scratch_resources(path, container='scratch1.dat'):
    env=UnityPy.load(str(path))
    assets=[o.read() for o in env.objects if o.type.name=='TextAsset' and o.read().m_Name==container]
    if len(assets)!=1: raise ValueError('Ambiguous scratch image container')
    data=assets[0].m_Script.encode('utf-8','surrogateescape')
    return dict(frame.offset_table(data, 2))


def scratch_image(path, name, container='scratch1.dat'):
    matched=scratch_resources(path,container)[name]
    image=Image.open(io.BytesIO(matched)).convert('RGBA')
    return dict(container=container,name=name,size=list(image.size),source_data_sha256=sha(matched),source_rgba_sha256=sha(image.tobytes()))
