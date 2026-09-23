"""Package the reviewed Chinese artwork into the original single-bitmap SWF.

Only image format/size conversion is performed here; artwork was edited with
the built-in image generation tool, see work/title-artwork.md.
"""
from pathlib import Path
from PIL import Image
import io,struct,zlib

def build(source:Path, artwork:Path, target:Path):
    raw=source.read_bytes()
    body=zlib.decompress(raw[8:]) if raw[:3]==b'CWS' else raw[8:]
    rect=(5+4*(body[0]>>3)+7)//8
    pos=rect+4; output=bytearray(body[:pos]);replaced=0
    stream=io.BytesIO()
    Image.open(artwork).convert('RGB').resize((400,300),Image.Resampling.LANCZOS).save(stream,format='JPEG',quality=95)
    while pos<len(body):
        header=struct.unpack_from('<H',body,pos)[0];pos+=2
        tag,size=header>>6,header&63
        if size==63:size=struct.unpack_from('<I',body,pos)[0];pos+=4
        data=body[pos:pos+size];pos+=size
        if tag==21:
            data=data[:2]+stream.getvalue();replaced+=1
        output+=struct.pack('<HI',(tag<<6)|63,len(data))+data
        if tag==0:break
    assert replaced==1
    target.write_bytes(b'CWS'+raw[3:4]+struct.pack('<I',len(output)+8)+zlib.compress(output))
