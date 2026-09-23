"""Create a DefineFont2 SWF from GNU Unifont bitmap glyphs (vector rectangles)."""
from pathlib import Path
import gzip,struct,zlib

class Bits:
    def __init__(self):self.bits=[]
    def put(self,v,n):self.bits.extend((v>>i)&1 for i in range(n-1,-1,-1))
    def data(self):
        b=self.bits+[0]*((-len(self.bits))%8)
        return bytes(sum(b[i+j]<<(7-j) for j in range(8)) for i in range(0,len(b),8))

def rect(x0,x1,y0,y1):
    n=max(abs(x0),abs(x1),abs(y0),abs(y1)).bit_length()+1
    b=Bits();b.put(n,5)
    for v in (x0,x1,y0,y1):b.put(v,n)
    return b.data()

def shape(bitmap,bold=False):
    width=len(bitmap)//4
    b=Bits();b.put(1,4);b.put(0,4)
    for y in range(16):
        row=int(bitmap[y*width//4:(y+1)*width//4],16)
        if bold: row |= row >> 1
        x=0
        while x<width:
            if not row&(1<<(width-1-x)):x+=1;continue
            end=x+1
            while end<width and row&(1<<(width-1-end)):end+=1
            px=x*64;py=(y-14)*64
            n=max(abs(px),abs(py)).bit_length()+1
            b.put(0,1);b.put(3,5);b.put(n,5);b.put(px,n);b.put(py,n);b.put(1,1)
            for dx,dy in (((end-x)*64,0),(0,64),(-(end-x)*64,0),(0,-64)):
                n=max(abs(dx),abs(dy)).bit_length()+1
                b.put(1,1);b.put(1,1);b.put(n-2,4);b.put(0,1);b.put(int(dy!=0),1);b.put(dy or dx,n)
            x=end
    b.put(0,6)
    return b.data(),width*64

def tag(code,data):
    return struct.pack('<HI',(code<<6)|63,len(data))+data

def build(chars,destination):
    root=Path(__file__).resolve().parent
    source=[]
    with gzip.open(root.parent/'games/10-kibu10/bepinex/fonts/unifont-16.0.04.hex.gz','rt') as f:
        for row in f:
            cp,bits=row.strip().split(':');cp=int(cp,16)
            if chr(cp) in chars and cp<65536:source.append((cp,bits))
    body=rect(0,12800,0,9600)+struct.pack('<HH',24*256,1)
    for font_id,bold in ((1,False),(2,True)):
        glyphs=[(cp,*shape(bits,bold)) for cp,bits in source]
        body+=tag(48,font_payload(glyphs,font_id,bold))
    body+=b'\x40\x00\x00\x00'
    destination.write_bytes(b'CWS\x08'+struct.pack('<I',len(body)+8)+zlib.compress(body))
    print('Font glyphs',len(source),'regular + bold; bytes',destination.stat().st_size)

def font_payload(glyphs,font_id,bold):
    name=b'KibukawaCHS'
    payload=struct.pack('<HBBB',font_id,0x8c|int(bold),0,len(name))+name+struct.pack('<H',len(glyphs))
    offset=4*(len(glyphs)+1);offsets=[];shapes=b''
    for cp,sh,w in glyphs:offsets.append(offset);offset+=len(sh);shapes+=sh
    payload+=b''.join(struct.pack('<I',v) for v in offsets+[offset])+shapes
    payload+=b''.join(struct.pack('<H',cp) for cp,sh,w in glyphs)
    payload+=struct.pack('<hhh',896,128,0)
    payload+=b''.join(struct.pack('<h',w) for cp,sh,w in glyphs)
    payload+=b''.join(rect(0,w,-896,128) for cp,sh,w in glyphs)+b'\0\0'
    return payload

if __name__=='__main__':
    root=Path(__file__).resolve().parent/'saina-onsen'
    chars=set(''.join(p.read_text(encoding='utf-8-sig') for p in (root/'originals/script').glob('*.adv'))+'开始游戏继续游戏设置退出诞生纪念日事件运行测试你好世界')
    build(chars,root/'build/chs-font.swf')
