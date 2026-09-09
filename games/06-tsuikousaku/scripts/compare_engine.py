"""Read-only method/field comparison with validated prior-game assemblies."""
import difflib
import re
import pipeline as p


def normalized(value, namespace):
    return re.sub(r'(?<=d__)\d+', '#', value.replace(namespace, ''))


def compare(target, baseline, namespace):
    def methods(data, prefix):
        result = {}
        for key, value in data['methods'].items():
            if 'CanvasEx' not in key or (prefix and prefix not in key):
                continue
            name = normalized(key, prefix)
            p.require(name not in result, 'Normalization collision: '+name)
            result[name] = [normalized(line, prefix) for line in value['body']]
        return result
    target_methods = methods(target, 'appli1.')
    base_methods = methods(baseline, namespace)
    common = set(target_methods) & set(base_methods)
    changed = sorted(k for k in common if target_methods[k] != base_methods[k])
    return dict(changed_methods=changed, unchanged_methods=len(common)-len(changed),
                added_methods=sorted(set(target_methods)-set(base_methods)),
                missing_methods=sorted(set(base_methods)-set(target_methods)),
                codec_equal=target['codec_base64']==baseline['codec_base64'],
                rva_fields_equal=target['rva_fields']==baseline['rva_fields'],
                canvas_fields_equal={normalized(k,'appli1.'):v for k,v in target['fields'].items() if 'appli1.CanvasEx' in k} == {normalized(k,namespace):v for k,v in baseline['fields'].items() if 'CanvasEx' in k and (not namespace or namespace in k)},
                diffs={k:list(difflib.unified_diff(base_methods[k], target_methods[k], fromfile='baseline', tofile='kibu6')) for k in changed})


def main():
    p.validate_sources()
    target=p.inspect(p.GAME, 'kibu6_Data', p.WORK/'research/kibu6-assembly.json')
    results={}
    for game, namespace in [('kibu1',''),('kibu2',''),('kibu3',''),('kibu4','appli1.'),('kibu5','appli1.')]:
        config=p.resolve(game)
        data_dir=game+'_Data'
        baseline=p.inspect(config['installation'], data_dir, p.WORK/('research/'+game+'-assembly.json'))
        manifest=p.load(config['project']/'work/manifest.json')
        p.require(baseline['assembly_sha256']==manifest['source_hashes'][data_dir+'/Managed/Assembly-CSharp.dll'], 'Baseline fingerprint mismatch: '+game)
        results[game]=compare(target,baseline,namespace)
    report=dict(comparisons=results, caveat='Namespace and coroutine suffix normalized for comparison only. Method body comparison includes locals and exception handlers. RVA hashes are captured separately; artwork and runtime effects remain unverified.', runtime_tested=False)
    p.save(p.WORK/'research/normalized-engine-comparison.json',report)
    print({k:{f:v[f] for f in ('changed_methods','unchanged_methods','added_methods','missing_methods','codec_equal')} for k,v in results.items()})

if __name__=='__main__': main()
