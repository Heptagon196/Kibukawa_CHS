"""Materialize translator-authored click-unit drafts; never translates or approves text."""
import argparse
import math
import pipeline as p
p.require(not (p.WORK/'work/dialogue-tagged.json').exists(), 'Legacy untagged materialization is disabled. Edit work/dialogue-tagged.json and run tagged_dialogue.py import.')
from review_units import current
import sys
sys.path.insert(0,str(p.SERIES/'tools'))
from click_boundaries import units

def main():
 parser=argparse.ArgumentParser();parser.add_argument('script');args=parser.parse_args()
 cs,lookup=current();manifest=p.load(p.WORK/'work/manifest.json');cache=p.load(p.WORK/'work/cache.json')
 rows={e['text_index']:e for g in cache['files'].values() for e in g['items']}
 groups={}
 for u in units(cs):
  if u['script']==args.script:
   es=[lookup[(u['script'],i)] for i in u['instructions'] if (u['script'],i) in lookup]
   groups[es[0]['text_index']]=es
 targets={}
 overrides_path=p.WORK/'work/drafts'/(args.script+'.slots.json')
 overrides={int(k):v for k,v in p.load(overrides_path).items()} if overrides_path.exists() else {}
 for line in (p.WORK/'work/drafts'/(args.script+'.units.txt')).read_text(encoding='utf-8-sig').splitlines():
  if not line or line.startswith('#'):continue
  key,t=line.split('|',1);key=int(key);es=groups[key];n=len(es)
  p.require(len(t)>=n and len(t)<=20*n,f'Unit capacity {key}: {len(t)}/{n}')
  weights=[len(e['source_text']) for e in es];total=sum(weights);pos=0;acc=0
  for j,e in enumerate(es):
   acc+=weights[j]
   end=len(t) if j==n-1 else max(pos+1,len(t)-20*(n-j-1),min(round(len(t)*acc/total),pos+20,len(t)-(n-j-1)))
   p.require(e['text_index'] not in targets,'Duplicate unit')
   targets[e['text_index']]=t[pos:end];pos=end
 targets.update(overrides)
 # Reuse only reviewed exact non-dialogue source mappings; no substring replacement.
 prior={}
 for e in manifest['entries']:
  r=rows[e['text_index']]
  if r['translation_status'] in (1,2) and e['location']['kind']=='script' and e['location']['opcode']!=72:
   prior.setdefault(e['source_text'],set()).add(r['translated_text'])
 extra=p.load(p.WORK/'work/menu-translations.json')
 for e in manifest['entries']:
  if e['group']!=args.script+'.txt':continue
  if e['text_index'] in targets:continue
  s=e['source_text']
  p.require(e['location']['opcode']!=72,'Missing dialogue '+str(e['text_index']))
  if s in extra:targets[e['text_index']]=extra[s]
  else:
   p.require(len(prior.get(s,[]))==1,'Missing menu '+str(e['text_index'])+': '+s)
   targets[e['text_index']]=next(iter(prior[s]))
 es=[e for e in manifest['entries'] if e['group']==args.script+'.txt']
 p.require(set(targets)=={e['text_index'] for e in es},'Coverage mismatch')
 draft=dict(manifest_sha256=p.sha((p.WORK/'work/manifest.json').read_bytes()),entries=[dict(id=e['text_index'],source=e['source_text'],target=targets[e['text_index']],**({'empty_reason':'中文姓名不附日语注音'} if targets[e['text_index']]=='' else {})) for e in es])
 p.save(p.WORK/'work/drafts'/(args.script+'.json'),draft)
 print('Prepared',args.script,len(es))
if __name__=='__main__':main()
