"""Prepare a backed-up test rewind; never writes the live save."""
import struct
import time
import pipeline as p


def main():
    source=p.GAME/'save/SaveData2'
    data=source.read_bytes()
    p.require(p.sha(data)=='7782f2e6763c2d110c3cfaa7c6955001fa406dedce90fbe722fddbd78b7ee3d4','Save changed since inspection')
    p.require(len(data)==803 and data[2]==1 and data[281]==8,'Unexpected inspected save format')
    pos=348
    for _ in range(24):
        length=int.from_bytes(data[pos:pos+2],'big')
        pos+=2+length+1
    p.require(pos==495,'Name table layout changed')
    output=bytearray(data)
    edits=[]
    def edit(name,offset,value,fmt):
        raw=struct.pack(fmt,value)
        old=bytes(output[offset:offset+len(raw)])
        output[offset:offset+len(raw)]=raw
        edits.append(dict(field=name,offset=offset,before=old.hex(),after=raw.hex()))
    for name,offset,value,fmt in [
        ('ScSelect',3,0,'B'),('ScCur',4,13927,'>i'),('ScCurTemp',8,0,'>i'),
        ('oldCur',12,-1,'>i'),('oldCurTemp',16,-1,'>i'),
        ('scIndent',20,0,'B'),('tempIndent',21,0,'B'),('Scenario',281,7,'B'),
        ('BG',504,11,'B'),('Pic[0]',505,16,'B'),
        ('Chara[0]',518,255,'B'),('Chara[1]',519,255,'B'),('Chara[2]',520,255,'B'),
        ('PicPos.X',521,125,'>h'),('PicPos.Y',523,50,'>h'),
        ('Mouth',525,255,'B'),('Music[0]',526,6,'B')]:
        edit(name,offset,value,fmt)
    changed={i for i in range(len(data)) if data[i]!=output[i]}
    allowed={e['offset']+j for e in edits for j in range(len(bytes.fromhex(e['after'])))}
    p.require(changed<=allowed and data[26:281]==output[26:281],'Unexpected save or flag modification')
    replay=p.load(p.WORK/'bepinex/build/replay.json')['commands']
    entry=next(x for x in replay if x['script']=='scn7' and x['instruction']==13927)
    p.require(entry['opcode']==71 and entry['integers']==[1],'Quiz entry point changed')
    directory=p.inside(p.WORK/'installations'/('save_rewind_'+time.strftime('%Y%m%d_%H%M%S')))
    directory.mkdir()
    backup=directory/'SaveData2.original'
    staged=directory/'SaveData2.quiz-test'
    backup.write_bytes(data)
    staged.write_bytes(output)
    report=dict(target=str(source),backup=str(backup),staged=str(staged),
                source_sha256=p.sha(data),staged_sha256=p.sha(output),edits=edits,
                changed_bytes=len(changed),entry='scn7:13927',purpose='test-only rewind before sentence puzzle',
                limitation='Preserves current flags; does not reconstruct earlier chapter investigation history',installed=False)
    p.save(directory/'report.json',report)
    p.save(p.WORK/'reports/puzzle-save-latest.json',report)
    print('Prepared test save; original safely backed up. Live save unchanged.')
    print(directory/'report.json')


if __name__=='__main__': main()
