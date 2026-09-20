import json,re,pathlib
p=pathlib.Path(__file__).parent
u=json.loads((p/'01.source.json').read_text(encoding='utf-8-sig'))['units']
f=p/'01.trans.json'
d=json.loads(f.read_text(encoding='utf-8')) if f.exists() else {'batch':1,'targets':{}}
for line in (p/'01.part.txt').read_text(encoding='utf-8-sig').splitlines():
 if not line: continue
 n,s=line.split('\t',1); x=u[int(n)]; parts=s.split('|')
 if '<' not in x['source']: out=s
 else:
  matches=list(re.finditer(r'(?<=>)[^<]+(?=<)',x['source']))
  assert len(matches)==len(parts),(n,len(matches),len(parts))
  out=x['source']
  for m,v in reversed(list(zip(matches,parts))):out=out[:m.start()]+v+out[m.end():]
 assert re.findall(r'<[^>]+>',out)==re.findall(r'<[^>]+>',x['source'])
 d['targets'][x['id']]=out
f.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
print(len(d['targets']))
