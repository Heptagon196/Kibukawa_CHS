"""Offline extraction and relocation for this game's Unity/Socotra resources.
All writes are confined to translation_workspace. No install/deploy operation.
"""
from __future__ import annotations
import argparse, base64, collections, copy, csv, hashlib, io, json, os, re
import shutil, struct, subprocess, sys, tempfile, time, zipfile
from pathlib import Path
import UnityPy

WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORK.parents[1] / 'tools'))
from project_config import resolve
PROJECT = resolve(project=WORK)
SERIES = PROJECT['root']
GAME = PROJECT['installation']
DATA = 'kibu1_Data/'
STREAM = DATA + 'StreamingAssets/'
DLL = DATA + 'Managed/Assembly-CSharp.dll'
JP = re.compile(r'[\u3040-\u30ff\u3400-\u9fff\uff66-\uff9f]')
MARKER = b'\xef\xbb\xbf'
# User-approved deletion of pronunciation-only name fragments. An empty
# string is a no-op in CanvasEx.ExeText; null instead has control semantics.
EMPTY_NAME_READINGS = {
    43: '(ｻｷﾞｼﾏ ｲﾂﾞﾅ)', 211: 'ﾘｮｳｽｹ)', 474: '(ｽﾅｶﾞ)',
    1288: '(ｱﾔｷ)', 2581: 'ﾎｳｹﾞﾂ)', 2937: '(ｾﾄﾞｳ)',
    4123: '(ｱｲ)', 4840: 'ﾉｿﾞﾐ)', 4883: '(ｻｶﾞﾜ ﾐﾆ)',
}

def require(test, message):
    if not test: raise ValueError(message)

def inside(path):
    path = Path(path).resolve()
    require(path.is_relative_to(WORK) and path != WORK, f'Output must be inside {WORK}: {path}')
    return path

def save(path, value):
    path = inside(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def sha(data): return hashlib.sha256(data).hexdigest()
def stamp(): return time.strftime('%Y%m%d_%H%M%S') + f'_{time.time_ns()%1000000000:09d}'

def assembly(mode, source, json_path=None, output=None, utf8=False, all_strings=False):
    shell = shutil.which('pwsh')
    require(shell, 'PowerShell 7 (pwsh) is required.')
    args = [shell, '-NoProfile', '-File', str(WORK/'scripts/assembly.ps1'), '-Mode', mode, '-InputDll', str(source)]
    if json_path: args += ['-JsonPath', str(json_path)]
    if output: args += ['-OutputDll', str(inside(output))]
    if utf8: args += ['-Utf8']
    if all_strings: args += ['-AllStrings']
    subprocess.run(args, check=True)

def decode(data, table):
    if data.startswith(MARKER): return data[3:].decode('utf-8')
    result=[]; p=0
    while p<len(data):
        c=data[p]; p+=1
        if 0x81<=c<=0x9f or 0xe0<=c<=0xea:
            require(p<len(data), 'Truncated SJIS sequence')
            c=(c<<8)|data[p]; p+=1
        value=table[c]
        require(value != 0, f'Unsupported original character 0x{c:04x}')
        result.append(chr(value))
    return ''.join(result)

def definitions(data):
    out={}; p=1
    for _ in range(data[0]):
        n=data[p]; p+=1
        out[data[p]]=list(data[p+1:p+n]); p+=n
    require(p==len(data), 'Invalid command definition table')
    return out

def parse_script(data, defs):
    p=0; commands=[]
    while p<len(data):
        start=p; op=data[p]; p+=1; args=[]
        require(op in defs, f'Unknown opcode {op:#x} at {start:#x}')
        for kind in defs[op]:
            begin=p
            if kind==3:
                p=data.index(0,p)+1
                val=data[begin:p-1]
            else:
                p += {0:1,1:2,2:4,4:2,5:1}[kind]
                require(p<=len(data), f'Truncated instruction at {start}')
                val=int.from_bytes(data[begin:p], 'big')
            args.append(dict(kind=kind, offset=begin, end=p, value=val))
        commands.append(dict(offset=start, end=p, opcode=op, args=args))
    starts={c['offset'] for c in commands}
    for c in commands:
        for a in c['args']:
            if a['kind']==4:
                require(a['value']==65535 or a['value'] in starts, f'Jump target {a["value"]:#x} is not an instruction boundary')
    return commands

def sub_parts(data):
    p=1; parts=[]
    for _ in range(data[0]):
        n=int.from_bytes(data[p:p+2], 'big'); p+=2
        parts.append(data[p:p+n]); p+=n
    require(p==len(data), 'Invalid subscenario lengths')
    return parts

def raw_text(obj): return obj.read().m_Script.encode('utf-8','surrogateescape')

def text_objects(env):
    return {o.read().m_Name: o for o in env.objects if o.type.name=='TextAsset'}

def set_text(obj, data):
    value=obj.read(); value.m_Script=data.decode('utf-8','surrogateescape'); value.save()

def aligned_strings(data):
    """Conservative UTF8 length-prefix scan; Unity aligns serialized strings to 4.
    This also covers custom MonoBehaviours stripped of type trees.
    """
    occupied=0
    for offset in range(0,len(data)-4,4):
        if offset<occupied: continue
        size=struct.unpack_from('<i',data,offset)[0]
        if not 1<=size<=len(data)-offset-4: continue
        end=(offset+4+size+3)&~3
        if end>len(data) or any(data[offset+4+size:end]): continue
        try: value=data[offset+4:offset+4+size].decode('utf-8')
        except UnicodeError: continue
        if not JP.search(value) or any(ord(c)<32 and c not in '\r\n\t' for c in value): continue
        occupied=end
        yield offset,end,value

def items(cache):
    return [x for f in cache['files'].values() for x in f['items']]

def game_hashes():
    roots=[GAME/'kibu1_Data',GAME/'MonoBleedingEdge']
    paths=[p for root in roots for p in root.rglob('*') if p.is_file()]
    paths += [p for p in GAME.iterdir() if p.is_file()]
    return {p.relative_to(GAME).as_posix():sha(p.read_bytes()) for p in sorted(paths)}

def extract_tagged_dialogue():
    """Reparse original instructions even when the legacy flat extraction already exists."""
    from dialogue_tags import document
    manifest=load(WORK/'work/manifest.json')
    for rel,digest in manifest['source_hashes'].items():require(sha((GAME/rel).read_bytes())==digest,'Source changed: '+rel)
    defs={int(k):v for k,v in manifest['definitions'].items()}
    table=list(struct.unpack('<65537H',base64.b64decode(manifest['codec_base64'])))
    file=text_objects(UnityPy.load(str(GAME/(STREAM+'file'))))
    scratch=text_objects(UnityPy.load(str(GAME/(STREAM+'scratchpad'))))
    archive=zipfile.ZipFile(io.BytesIO(raw_text(scratch['kamen.res'])))
    scripts=[(n,archive.read(n)) for n in sorted(archive.namelist()) if re.fullmatch(r'scn\d+',n)]
    scripts += [('subscn_'+str(i+1),b) for i,b in enumerate(sub_parts(raw_text(file['subscn'])))]
    replay=[]
    for name,data in scripts:
        for c in parse_script(data,defs):
            replay.append(dict(script=name,instruction=c['offset'],opcode=c['opcode'],nextCursor=c['end'],
                strings=[decode(a['value'],table) if a['value'] else None for a in c['args'] if a['kind']==3],
                integers=[a['value'] if a['value']<2147483648 else a['value']-4294967296 for a in c['args'] if a['kind']!=3]))
    save(WORK/'research/source-replay.json',dict(commands=replay))
    save(WORK/'texts/dialogue-tagged.json',document(WORK,replay))

def extract():
    manifest_path=WORK/'work/manifest.json'
    if manifest_path.exists():
        manifest=load(manifest_path)
        for rel,h in manifest['source_hashes'].items():
            require(sha((GAME/rel).read_bytes())==h, f'Game version changed: {rel}. Use a separate workspace.')
        require((WORK/'work/cache.json').exists(), 'Existing manifest has no cache; restore cache from backup.')
        extract_tagged_dialogue()
        print('Tagged extraction refreshed; cache and translations preserved.'); return
    before=game_hashes()
    (WORK/'work').mkdir(exist_ok=True)
    assembly('extract', GAME/DLL, WORK/'work/assembly_inventory.json')
    inv=load(WORK/'work/assembly_inventory.json')
    table=list(struct.unpack('<65537H',base64.b64decode(inv['codec_base64'])))
    envs={}; sources={}; entries=[]; files={}; script_stats={}; inventory=[]
    def env(rel):
        if rel not in envs: envs[rel]=UnityPy.load(str(GAME/rel))
        return envs[rel]
    def snapshot(rel):
        if rel not in sources:
            data=(GAME/rel).read_bytes(); sources[rel]=sha(data)
            dest=inside(WORK/'originals'/rel); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(data)
    def add(group, value, loc, excluded=False, reason=''):
        if not value: return
        snapshot(loc['file']); idx=len(entries)+1
        entry=dict(text_index=idx, source_text=value, location=loc, group=group, excluded=excluded, reason=reason)
        entries.append(entry)
        files.setdefault(group,dict(storage_path=group,encoding='utf-8',file_project_type='Txt',line_ending='\n',items=[],extra={}))['items'].append(
            dict(text_index=idx,translation_status=7 if excluded else 0,model='',source_text=value,translated_text='',text_to_detect=value,
                 extra=dict(location=loc, note=reason, max_characters=20 if loc['kind']=='script' else None)))
    file_objs=text_objects(env(STREAM+'file'))
    defs=definitions(raw_text(file_objs['define']))
    zip_obj=text_objects(env(STREAM+'scratchpad'))['kamen.res']
    archive=zipfile.ZipFile(io.BytesIO(raw_text(zip_obj)))
    def add_script(name,data,loc):
        commands=parse_script(data,defs); count=0
        line_used=0
        for c in commands:
            if c['opcode'] in (75,76,77,78): line_used=0
            for arg_no,a in enumerate(c['args']):
                if a['kind']!=3: continue
                value=decode(a['value'],table); count+=bool(value)
                at=dict(loc,kind='script',offset=a['offset'],opcode=c['opcode'],instruction=c['offset'],argument=arg_no)
                add(name+'.txt',value,at)
                if c['opcode']==72: line_used+=len(value)
        script_stats[name]=dict(bytes=len(data),instructions=len(commands),strings=count,jumps=sum(a['kind']==4 for c in commands for a in c['args']))
    for name in sorted(archive.namelist(),key=lambda x: int(x[3:]) if re.fullmatch(r'scn\d+',x) else -1):
        if re.fullmatch(r'scn\d+',name):
            add_script(name,archive.read(name),dict(file=STREAM+'scratchpad',asset='kamen.res',member=name))
    for i,data in enumerate(sub_parts(raw_text(file_objs['subscn']))):
        add_script(f'subscn_{i+1}',data,dict(file=STREAM+'file',asset='subscn',part=i))
    local_obj=text_objects(env(STREAM+'localization'))['Localization']
    rows=list(csv.reader(io.StringIO(raw_text(local_obj).decode('utf-8-sig'),newline='')))
    ja=rows[0].index('ja')
    for row in range(1,len(rows)):
        add('localization_ja.csv',rows[row][ja],dict(kind='csv',file=STREAM+'localization',asset='Localization',row=row,column=ja,key=rows[row][0]))
    paths=list((GAME/STREAM).rglob('*'))+list((GAME/DATA).glob('*.assets'))+[GAME/DATA/'level0']
    for path in sorted(paths):
        if not path.is_file() or path.suffix=='.manifest': continue
        rel=path.relative_to(GAME).as_posix()
        e=env(rel)
        for obj in sorted(e.objects,key=lambda o:o.path_id):
            if obj.type.name!='MonoBehaviour': continue
            for offset,end,value in aligned_strings(obj.get_raw_data()):
                excluded=bool(re.search(r'説明１６字|ボタン名|１プライヤー名|ランキング名',value))
                # m_Name is an identifier, never a displayed translation field.
                if offset==28: excluded=True
                add('ui/'+rel+'.txt',value,dict(kind='unity_string',file=rel,asset_file=obj.assets_file.name,path_id=obj.path_id,offset=offset,end=end),excluded,'Unity serialized string; template/identifier' if excluded else 'Unity serialized UTF-8 string')
    for row in inv['strings']:
        method=row['method']; value=row['source_text']
        visible=('CanvasEx' in method or 'CharacterInputDialog' in method or 'CharacterInputKeyManager::Init' in method or 'WindowDialog' in method)
        add('assembly_ui.txt' if visible else 'excluded/assembly_technical.txt',value,dict(kind='assembly',file=DLL,token=row['token'],instruction=row['instruction'],method=method),not visible,'UI literal' if visible else 'Keyboard table, comparison key, diagnostic or template: excluded by default')
    snapshot(STREAM+'file'); snapshot(STREAM+'scratchpad'); snapshot(STREAM+'localization'); snapshot(DLL)
    cache=dict(project_id='kibu1-'+sources[STREAM+'scratchpad'][:16],project_type='Txt',project_name='癸生川凌介事件譚 Vol.1 仮面幻想殺人事件',
               project_create_time=time.strftime('%Y-%m-%d %H:%M:%S'),input_path=str(GAME),stats_data={},files=files,
               detected_encoding='utf-8',detected_line_ending='\n',extra=dict(format='socotra-unity-v1',exporter='scripts/pipeline.py build'))
    manifest=dict(version=1,source_hashes=sources,game_hashes=before,entries=entries,script_stats=script_stats,codec_base64=inv['codec_base64'],definitions=defs)
    save(WORK/'work/cache.json',cache); save(manifest_path,manifest)
    extract_tagged_dialogue()
    save(WORK/'work/glossary.draft.json',dict(characters=[],terms=[],non_translate=[],note='Not reviewed or locked. Populate before translating.'))
    for group,f in files.items():
        target=inside(WORK/'texts'/group); target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text('\n'.join(f'[{x["text_index"]}] {x["source_text"]}' for x in f['items']),encoding='utf-8')
    require(game_hashes()==before,'Game files changed during extraction')
    report=dict(total=len(entries),translatable=sum(not e['excluded'] for e in entries),excluded=sum(e['excluded'] for e in entries),
                groups={k:len(v['items']) for k,v in files.items()},scripts=script_stats,original_game_unchanged=True,
                coverage='Scenario bytecode, localization ja, aligned Japanese/CJK strings in Unity MonoBehaviours and managed ldstr. Image text and arbitrary native/binary strings are not OCRed.')
    save(WORK/'reports/extraction.json',report)
    print(json.dumps({k:report[k] for k in ('total','translatable','excluded','original_game_unchanged')},ensure_ascii=False))

def validate_cache(cache,manifest):
    current=items(cache); by_id={x['text_index']:x for x in current}
    require(len(by_id)==len(current)==len(manifest['entries']),'Cache has missing or duplicate text_index values')
    changes={}
    for e in manifest['entries']:
        x=by_id.get(e['text_index']); require(x is not None and x['source_text']==e['source_text'],f'Source was edited at index {e["text_index"]}')
        status=x['translation_status']; require(status in (0,1,2,7),f'Invalid status at {e["text_index"]}')
        if status not in (1,2): continue
        text=x['translated_text']
        approved_empty=(text == '' and e['location']['kind'] == 'script'
                        and e['location']['opcode'] == 72
                        and (EMPTY_NAME_READINGS.get(e['text_index']) == e['source_text'] or (load(WORK/'project.json').get('approved_empty_layout_text',{}).get(str(e['text_index']),{}).get('source') == e['source_text'] and x['extra'].get('empty_translation_reason'))))
        require(isinstance(text,str) and (text.strip() or approved_empty),f'Empty translation at {e["text_index"]}')
        require('\0' not in text,f'NUL in translation {e["text_index"]}')
        require(not any(0xd800<=ord(c)<=0xdfff for c in text),'Unpaired surrogate in translation')
        if text==e['source_text']: continue
        require(not e['excluded'], f'Index {e["text_index"]} is a protected technical/template entry')
        # Keep .NET format arguments and Unity rich-text tags intact.
        tokens=lambda s: collections.Counter(re.findall(r'\{\d+(?:[^{}]*)\}|</?[A-Za-z][^>]*>',s))
        require(tokens(text)==tokens(e['source_text']),f'Placeholder/tag mismatch at {e["text_index"]}')
        if e['location']['kind']=='script':
            require(not any(c in text for c in '\r\n\t'),f'No embedded newlines in script string {e["text_index"]}; keep existing command structure')
            require(len(text.encode('utf-16-le'))//2<=20,f'Script string {e["text_index"]} exceeds 20 characters')
        changes[e['text_index']]=text
    return changes

def rebuild_script(data,defs,edits,table):
    commands=parse_script(data,defs); output=bytearray(); relocation={}; fixups=[]; new_strings=[]
    line_length=0; changed_line=False
    def check_line():
        require(not changed_line or line_length<=20,f'Combined dialogue fragments exceed 20 characters ({line_length})')
    for c in commands:
        relocation[c['offset']]=len(output); output.append(c['opcode'])
        # Speaker changes and selection menus also clear the dialogue buffer.
        # See CanvasEx.Script(): ExeText(null, 2) for these commands.
        if c['opcode'] in (71,73,75,76,77,78) or 105<=c['opcode']<=112 or 120<=c['opcode']<=123:
            check_line(); line_length=0; changed_line=False
        for a in c['args']:
            if a['kind']==3:
                value=edits.get(a['offset'])
                encoded=MARKER+value.encode('utf-8') if value is not None else a['value']
                if c['opcode']==72:
                    line_length+=len((value if value is not None else decode(a['value'],table)).encode('utf-16-le'))//2
                    changed_line |= value is not None
                new_strings.append((len(output),encoded))
                output.extend(encoded+b'\0')
            else:
                if a['kind']==4: fixups.append((len(output),a['value']))
                output.extend(data[a['offset']:a['end']])
    check_line()
    require(len(output)<=32767,'Scenario exceeds signed 16-bit script buffer limit (32767 bytes)')
    for off,target in fixups:
        output[off:off+2]=(65535 if target==65535 else relocation[target]).to_bytes(2,'big')
    parsed=parse_script(bytes(output),defs)
    require(len(parsed)==len(commands),'Instruction count changed')
    actual=[a['value'] for c in parsed for a in c['args'] if a['kind']==3]
    require(actual==[x[1] for x in new_strings],'Repacked text mismatch')
    return bytes(output),dict(instructions=len(commands),jumps=len(fixups),bytes_before=len(data),bytes_after=len(output))

def build(cache_path=None,out=None):
    manifest=load(WORK/'work/manifest.json'); cache=load(cache_path or WORK/'work/cache.json')
    changes=validate_cache(cache,manifest)
    for rel,h in manifest['source_hashes'].items():
        require(sha((GAME/rel).read_bytes())==h,f'Game version changed: {rel}')
        require(sha((WORK/'originals'/rel).read_bytes())==h,f'Original snapshot damaged: {rel}')
    out=inside(out or WORK/'out'/('build_'+stamp()))
    require(not out.exists(),f'Output already exists; choose a fresh folder: {out}')
    out.mkdir(parents=True)
    patch=inside(out/'patch'); patch.mkdir()
    table=struct.unpack('<65537H',base64.b64decode(manifest['codec_base64']))
    defs={int(k):v for k,v in manifest['definitions'].items()}
    grouped=collections.defaultdict(list)
    for entry in manifest['entries']:
        if entry['text_index'] in changes: grouped[entry['location']['file']].append(entry)
    stats={}; verifications=[]; utf8=False; scenario_max=0; envs={}
    def get_env(rel):
        if rel not in envs: envs[rel]=UnityPy.load(str(WORK/'originals'/rel))
        return envs[rel]
    for rel,entries in grouped.items():
        if rel==DLL: continue
        env=get_env(rel); by_kind=collections.defaultdict(list)
        for e in entries: by_kind[e['location']['kind']].append(e)
        if by_kind['script']:
            utf8=True; objs=text_objects(env); split=collections.defaultdict(list)
            for e in by_kind['script']:
                loc=e['location']; split[loc.get('member',loc.get('part'))].append(e)
            if rel==STREAM+'scratchpad':
                original=raw_text(objs['kamen.res']); z=zipfile.ZipFile(io.BytesIO(original)); replacements={}
                for member,es in split.items():
                    edits={e['location']['offset']:changes[e['text_index']] for e in es}
                    replacements[member],stats[member]=rebuild_script(z.read(member),defs,edits,table)
                    scenario_max=max(scenario_max,len(replacements[member]))
                buffer=io.BytesIO()
                with zipfile.ZipFile(buffer,'w') as target:
                    target.comment=z.comment
                    for info in z.infolist(): target.writestr(copy.copy(info),replacements.get(info.filename,z.read(info.filename)))
                encoded=buffer.getvalue(); z2=zipfile.ZipFile(io.BytesIO(encoded))
                require(z.namelist()==z2.namelist(),'ZIP entries changed')
                for name in z.namelist(): require(z2.read(name)==replacements.get(name,z.read(name)),f'ZIP roundtrip failed: {name}')
                set_text(objs['kamen.res'],encoded)
                verifications.append((rel,objs['kamen.res'].path_id,encoded))
            else:
                parts=sub_parts(raw_text(objs['subscn']))
                for part,es in split.items():
                    edits={e['location']['offset']:changes[e['text_index']] for e in es}
                    parts[part],stats[f'subscn_{part+1}']=rebuild_script(parts[part],defs,edits,table)
                encoded=bytes([len(parts)])+b''.join(len(p).to_bytes(2,'big')+p for p in parts)
                set_text(objs['subscn'],encoded); verifications.append((rel,objs['subscn'].path_id,encoded))
        if by_kind['csv']:
            objs=text_objects(env); obj=objs['Localization']
            rows=list(csv.reader(io.StringIO(raw_text(obj).decode('utf-8-sig'),newline='')))
            for e in by_kind['csv']:
                loc=e['location']; require(rows[loc['row']][loc['column']]==e['source_text'],'CSV source mismatch')
                rows[loc['row']][loc['column']]=changes[e['text_index']]
            buffer=io.StringIO(newline=''); csv.writer(buffer,lineterminator='\r\n',quoting=csv.QUOTE_ALL).writerows(rows)
            encoded=buffer.getvalue().encode('utf-8'); set_text(obj,encoded); verifications.append((rel,obj.path_id,encoded))
        if by_kind['unity_string']:
            groups=collections.defaultdict(list)
            for e in by_kind['unity_string']: groups[e['location']['path_id']].append(e)
            obj_map={o.path_id:o for o in env.objects}
            for path_id,es in groups.items():
                obj=obj_map[path_id]; raw=obj.get_raw_data(); output=bytearray(); pos=0
                for e in sorted(es,key=lambda x:x['location']['offset']):
                    loc=e['location']; off=loc['offset']; n=struct.unpack_from('<i',raw,off)[0]
                    require(raw[off+4:off+4+n].decode('utf-8')==e['source_text'],'Serialized source mismatch')
                    value=changes[e['text_index']].encode('utf-8'); output.extend(raw[pos:off]); output.extend(struct.pack('<i',len(value))+value)
                    output.extend(b'\0'*((-len(output))%4)); pos=loc['end']
                output.extend(raw[pos:]); obj.set_raw_data(bytes(output)); verifications.append((rel,path_id,bytes(output),'raw'))
    if scenario_max:
        rel=STREAM+'file'; obj=text_objects(get_env(rel))['env']; data=bytearray(raw_text(obj))
        capacity=max(int.from_bytes(data[3:5],'big'),int.from_bytes(data[5:7],'big'))
        if scenario_max>capacity:
            data[3:5]=scenario_max.to_bytes(2,'big'); data[5:7]=scenario_max.to_bytes(2,'big')
            set_text(obj,bytes(data)); verifications.append((rel,obj.path_id,bytes(data)))
    # Preserve untouched source files byte-for-byte; output is always a complete resource set.
    for rel in manifest['source_hashes']:
        dest=inside(patch/rel); dest.parent.mkdir(parents=True,exist_ok=True)
        if rel in envs:
            env=envs[rel]; root=list(env.files.values())
            require(len(root)==1,'Expected one Unity root file')
            dest.write_bytes(root[0].save())
        else: shutil.copyfile(WORK/'originals'/rel,dest)
    asm_patches=[]
    for e in grouped.get(DLL,[]):
        loc=e['location']; asm_patches.append(dict(token=loc['token'],method=loc['method'],instruction=loc['instruction'],source_text=e['source_text'],translated_text=changes[e['text_index']]))
    if utf8 or asm_patches:
        save(out/'assembly_patches.json',asm_patches)
        assembly('build',WORK/'originals'/DLL,out/'assembly_patches.json',patch/DLL,utf8=utf8)
        if utf8: assembly('verify',patch/DLL)
        assembly('extract',patch/DLL,out/'assembly_check.json',all_strings=True)
        # ldstr instructions remain at original indices except inside decoder; no translated literals there.
        actual={(x['method'],x['instruction']):x['source_text'] for x in load(out/'assembly_check.json')['strings']}
        for p in asm_patches:
            require(actual.get((p['method'],p['instruction']))==p['translated_text'],'Assembly write verification failed')
    reopened={}
    for v in verifications:
        rel,path_id,want,*mode=v
        if rel not in reopened: reopened[rel]=UnityPy.load(str(patch/rel))
        obj=next(o for o in reopened[rel].objects if o.path_id==path_id)
        actual=obj.get_raw_data() if mode else raw_text(obj)
        require(actual==want,f'Unity write verification failed: {rel} {path_id}')
    # Every object not explicitly patched must retain its complete raw payload.
    for rel,env in envs.items():
        old=UnityPy.load(str(WORK/'originals'/rel)); new=reopened.get(rel) or UnityPy.load(str(patch/rel))
        a={o.path_id:o.get_raw_data() for o in old.objects}; b={o.path_id:o.get_raw_data() for o in new.objects}
        changed_ids={v[1] for v in verifications if v[0]==rel}
        require(a.keys()==b.keys(),f'Unity object inventory changed: {rel}')
        require(all(a[k]==b[k] for k in a if k not in changed_ids),f'Unrelated Unity object changed: {rel}')
    unchanged=game_hashes()==manifest['game_hashes']
    require(unchanged,'Original game files changed since extraction')
    output_hashes={r:sha((patch/r).read_bytes()) for r in manifest['source_hashes']}
    report=dict(translated_changes=len(changes),utf8_decoder_patched=utf8,scenarios=stats,verified_resource_objects=len(verifications),
                output_hashes=output_hashes,byte_identical_noop=not changes and output_hashes==manifest['source_hashes'],original_game_unchanged=unchanged,
                runtime_visual_tested=False,font_note='Original Japanese fonts retained. Chinese glyph coverage and actual UI layout require a font pass and in-game validation.',
                deployment_note='This directory contains replacement resources only. No original game files were written. DLL is required when utf8_decoder_patched is true.')
    save(out/'build_report.json',report); save(WORK/'reports/latest_build.json',dict(output=str(out),**report))
    print(f'Build verified: {out} ({len(changes)} changed text occurrences)')
    return out,report

def apply_batch(path):
    cache_path=WORK/'work/cache.json'; cache=load(cache_path); manifest=load(WORK/'work/manifest.json'); updates=load(path)
    require(isinstance(updates,list),'Batch must be a JSON array')
    by_id={x['text_index']:x for x in items(cache)}; seen=set()
    for x in updates:
        idx=x['text_index']; require(idx in by_id and idx not in seen,f'Invalid/duplicate index {idx}'); seen.add(idx)
        require(isinstance(x.get('translated_text'),str),'translated_text must be a string')
        by_id[idx]['translated_text']=x['translated_text']; by_id[idx]['translation_status']=1
    validate_cache(cache,manifest)
    shutil.copyfile(cache_path,inside(WORK/'work'/('cache.json.bak.'+stamp())))
    save(cache_path,cache); print(f'Applied {len(updates)} translations')

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('extract')
    b=sub.add_parser('build'); b.add_argument('--cache'); b.add_argument('--out')
    a=sub.add_parser('apply'); a.add_argument('batch')
    r=sub.add_parser('batch'); r.add_argument('--size',type=int,default=100)
    sub.add_parser('status')
    args=p.parse_args()
    if args.command=='extract': extract()
    elif args.command=='build': build(args.cache,args.out)
    elif args.command=='apply': apply_batch(args.batch)
    elif args.command=='batch':
        rows=[{k:x[k] for k in ('text_index','source_text')} for x in items(load(WORK/'work/cache.json')) if x['translation_status']==0]
        print(json.dumps(rows[:args.size],ensure_ascii=False,indent=2))
    elif args.command=='status':
        print(json.dumps(collections.Counter(x['translation_status'] for x in items(load(WORK/'work/cache.json'))),ensure_ascii=False,indent=2))

if __name__=='__main__':
    try: main()
    except (ValueError,KeyError,UnicodeError,subprocess.CalledProcessError) as e:
        print(f'ERROR: {e}',file=sys.stderr); sys.exit(1)
