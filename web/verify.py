"""Verify translation control markers and original-file hashes, without running games."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parent
def main():
    results={}
    for game in ('birthday','operation-check-2','saina-onsen'):
        p=ROOT/game
        manifest=json.loads((p/'source-manifest.json').read_text(encoding='utf-8'))
        for name,digest in manifest['files'].items():
            assert hashlib.sha256((p/'originals'/name).read_bytes()).hexdigest()==digest,(game,name)
        rows=json.loads((p/'work/dialogue.json').read_text(encoding='utf-8'))
        translated=[r for r in rows if r['target']]
        for row in translated:
            pat=r'\[(?:lp|ll|lr|ler|p|l|me|\$[^\]]+)\]'
            if game == 'saina-onsen':
                pat=r'\[(?:r|rr|p|pp|ppp|pp_j|l|ll)\]'
            assert re.findall(pat,row['source'])==re.findall(pat,row['target']),row['id']
        results[game]={'rows':len(rows),'translated':len(translated),'control_mismatches':0,'sources_verified':len(manifest['files'])}
    print(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
