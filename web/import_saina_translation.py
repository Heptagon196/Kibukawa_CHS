"""Import reviewed, ID-addressed TSV translations into the canonical text table.

Trailing page/wait markers are inherited when omitted from the TSV. Inline tags
remain explicit. Exact duplicate Japanese lines reuse an unambiguous translation.
"""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parent/'saina-onsen/work'
rows=json.loads((ROOT/'dialogue.json').read_text('utf8'))
by_id={r['id']:r for r in rows}
for p in sorted((ROOT/'translations').glob('*.tsv')):
    for line in p.read_text('utf8').splitlines():
        if not line or line.startswith('#'):continue
        key,target=line.split('\t',1)
        r=by_id[key]
        suffix=re.search(r'(?:\[(?:r|rr|p|pp|ppp|l|ll)\])+$',r['source'])
        if suffix and not re.search(r'\[(?:r|rr|p|pp|ppp|l|ll)\]$',target):target+=suffix.group()
        r['target']=target
duplicates={}
for r in rows:
    if r['target']:duplicates.setdefault(r['source'],set()).add(r['target'])
for r in rows:
    options=duplicates.get(r['source'],set())
    if not r['target'] and len(options)==1:r['target']=next(iter(options))
(ROOT/'dialogue.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Translated',sum(bool(r['target']) for r in rows),'/',len(rows))
