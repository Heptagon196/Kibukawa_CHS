"""One-off, backed-up edit of the user's current save; never loaded by the plugin."""
import shutil
import struct
import pipeline as p

save=p.GAME/'save/SaveData2'
before=save.read_bytes()
# This is the inspected save's complete length-prefixed UTF-8 name table.
expected=['伊纲','生王','','癸生川','尾场','音成','砂永','萌奈','绫城','小早志','续木','美贰',
          '望美','山王丸','濑堂','中年女性','工作人员','男性','女性','播音员','路人','前台小姐','传次郎','逢井']
pos=348; edits=[]; after=bytearray(before)
p.require(len(before)==803,'Save changed in size; inspect again before editing')
for index,name in enumerate(expected):
    length=struct.unpack_from('>H',before,pos)[0]
    start=pos+2;end=start+length
    p.require(before[start:end].decode('utf-8')==name,f'Unexpected name table at slot {index}')
    target={5:'林居',11:'美妮'}.get(index)
    if target:
        encoded=target.encode('utf-8');p.require(len(encoded)==length,'Replacement would change save structure')
        after[start:end]=encoded
        edits.append(dict(slot=index,offset=start,length=length,before=name,after=target))
    pos=end+1  # Preserve the following name color byte.
p.require(pos==591,'Unexpected name table end')
allowed={i for edit in edits for i in range(edit['offset'],edit['offset']+edit['length'])}
changed=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
p.require(set(changed)<=allowed and len(before)==len(after),'Non-name save bytes would change')
backup=p.WORK/'save_backups'/('names_'+p.stamp());backup.mkdir(parents=True)
for path in (p.GAME/'save').iterdir():
    if path.is_file():shutil.copy2(path,backup/path.name)
p.require((backup/save.name).read_bytes()==before,'Backup verification failed')
p.require(save.read_bytes()==before,'Save changed during backup; stop')
save.write_bytes(after)
p.require(save.read_bytes()==bytes(after),'Saved file verification failed')
p.save(p.WORK/'reports/saved_name_update.json',dict(save=str(save),backup=str(backup),size=len(after),
       edits=edits,changed_byte_offsets=changed,other_bytes_unchanged=True,
       before_sha256=p.sha(before),after_sha256=p.sha(bytes(after)),runtime_plugin_modified=False))
print('Updated saved names only:',edits)
print('Verified all other bytes unchanged; backup:',backup)
