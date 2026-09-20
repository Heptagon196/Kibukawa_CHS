"""Pinned build-time segmentation; only immutable boundary masks ship in the DLL."""
import hashlib,json,re,sys
from pathlib import Path
import pipeline as p

def build(scripts):
    sys.path.insert(0,str(p.WORK/'bepinex/build/python-deps'))
    import jieba
    assert jieba.__version__=='0.42.1'
    dictionary=Path(jieba.__file__).parent/'dict.txt'
    assert p.sha(dictionary.read_bytes())=='7197c3211ddd98962b036cdf40324d1ea2bfaa12bd028e68faa70111a88e12a8'
    words=set()
    def collect(value):
        if isinstance(value,dict):
            term=value.get('render')
            if isinstance(term,str) and len(term)>1:
                words.add(term)
                if 'person' in value.get('category',''):
                    words.update(term+t for t in ('先生','小姐','女士','警官','刑警','老师','社长','前辈'))
            for child in value.values():collect(child)
        elif isinstance(value,list):
            for child in value:collect(child)
    inputs=[p.WORK/'work/glossary.locked.json',p.SERIES/'series/glossary.json']
    for file in inputs:collect(p.load(file))
    tokenizer=jieba.Tokenizer();tokenizer.tmp_dir=str(p.WORK/'bepinex/build');tokenizer.initialize()
    for word in sorted(words):tokenizer.add_word(word,1000000)
    masks={}
    for script in scripts:
        for display in script['displays']:
            text=''.join(r['text'] for r in display['rows'])
            if not text or text in masks:continue
            mask=['0']*(len(text)+1);cursor=0
            tokens=list(tokenizer.cut(text,HMM=False));assert ''.join(tokens)==text
            for token in tokens:
                for i in range(cursor+1,cursor+len(token)):mask[i]='1'
                cursor+=len(token)
            for word in words:
                start=text.find(word)
                while start>=0:
                    for i in range(start+1,start+len(word)):mask[i]='1'
                    start=text.find(word,start+1)
            for match in re.finditer(r'[0-9０-９]+|[A-Za-zＡ-Ｚａ-ｚ]+(?:[.\'’][A-Za-zＡ-Ｚａ-ｚ]+)*',text):
                for i in range(match.start()+1,match.end()):mask[i]='1'
            masks[text]=''.join(mask)
    out=p.WORK/'bepinex/build/generated/DirectLexicon.cs'
    out.parent.mkdir(parents=True,exist_ok=True)
    quote=lambda s:json.dumps(s,ensure_ascii=True)
    out.write_text('using System.Collections.Generic; namespace Kibukawa.Engine.Gmode20050817Direct { internal static class DirectLexicon { internal static readonly Dictionary<string,string> Masks = new Dictionary<string,string> {\n'+''.join('{'+quote(t)+','+quote(m)+'},\n' for t,m in sorted(masks.items()))+'}; } }\n','utf-8')
    p.save(p.WORK/'reports/layout-lexicon.json',dict(jieba=jieba.__version__,hmm=False,dictionary_sha256=p.sha(dictionary.read_bytes()),terms=len(words),texts=len(masks),inputs={str(f.relative_to(p.SERIES)):p.sha(f.read_bytes()) for f in inputs}))
    return out
