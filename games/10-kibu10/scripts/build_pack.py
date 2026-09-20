"""Compile immutable-offset KBZH and generated tenth-game script identities."""
import argparse
import json
import pipeline as p
from runtime_pack import compile_pack, make_translation_pack, encode_translation_pack

def build(smoke=False, output=None):
    manifest=p.validate_sources()
    out=p.inside(output or p.WORK/'bepinex/build/plugin')
    out.mkdir(parents=True,exist_ok=True)
    from generate_ui_data import generate
    exact,keys=generate()
    scripts,report=compile_pack(p.WORK,smoke=smoke)
    from build_layout_lexicon import build as build_lexicon
    build_lexicon(scripts)
    names={}
    for item in report['scripts']:
        names.setdefault(item['sha256'],item['name'])
    identity=p.WORK/'bepinex/src/ScriptIdentityData.cs'
    identity.write_text('using System.Collections.Generic;\nnamespace Kibu10ZhCN { internal static class ScriptIdentityData {\n'
        'internal static readonly Dictionary<string,string> Names = new Dictionary<string,string> {\n'
        + ''.join('{'+json.dumps(k)+','+json.dumps(v)+'},\n' for k,v in sorted(names.items()))+'}; } }\n',encoding='utf-8')
    pack=make_translation_pack(scripts,manifest['source_hashes']['kibu10_Data/Managed/Assembly-CSharp.dll'],
        manifest['source_hashes']['kibu10_Data/StreamingAssets/scratchpad'],
        [dict(source=k,target=v,key=None) for k,v in sorted(exact.items())],
        [dict(source=None,target=v,key=k) for k,v in sorted(keys.items())],script_names=names)
    p.save(out/'translations.json',pack)
    binary=encode_translation_pack(pack)
    (out/'translations.bin').write_bytes(binary)
    p.require(binary==encode_translation_pack(p.load(out/'translations.json')),'Pack JSON/binary mismatch')
    report.update(sha256=p.sha(binary),bytes=len(binary),runtime_tested=False)
    p.save(p.WORK/'reports'/('runtime-pack-smoke.json' if smoke else 'runtime-pack.json'),report)
    (out/'sources.sha256').write_text(''.join(h+'  '+n+'\n' for n,h in sorted(manifest['source_hashes'].items())),encoding='utf-8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    print(build(args.smoke))
