"""Compare full normalized CanvasEx bodies after removing only the part namespace."""
import difflib
import pipeline as p


def main():
    target = p.load(p.WORK/'research/kibu4-assembly.json')
    baseline = p.load(p.WORK/'research/kibu3-assembly.json')
    original = {k: v for k, v in baseline['methods'].items() if 'CanvasEx' in k}
    results = {}
    diff = []
    for namespace in ('appli1.', 'appli2.'):
        methods = {k.replace(namespace, ''): v for k, v in target['methods'].items()
                   if namespace+'CanvasEx' in k}
        same, changed = [], []
        for name in sorted(original.keys() & methods.keys()):
            before = original[name]['normalized_body']
            after = [line.replace(namespace, '') for line in methods[name]['normalized_body']]
            (same if before == after else changed).append(name)
            if before != after:
                diff.extend(difflib.unified_diff(before, after, fromfile='kibu3/'+name,
                                               tofile=namespace+name, lineterm=''))
        fields = {k.replace(namespace, ''): v for k, v in target['fields'].items()
                  if namespace+'CanvasEx' in k}
        old_fields = {k: v for k, v in baseline['fields'].items() if 'CanvasEx' in k}
        results[namespace.rstrip('.')] = dict(
            identical_methods=same, changed_methods=changed,
            removed_methods=sorted(original.keys()-methods.keys()),
            added_methods=sorted(methods.keys()-original.keys()),
            fields_equal=fields == old_fields, field_count=len(fields))
    rva = {k: dict(before=baseline['initialized_fields'].get(k), after=v)
           for k, v in target['initialized_fields'].items()
           if baseline['initialized_fields'].get(k) != v}
    p.save(p.WORK/'research/dual-engine-comparison.json', dict(
        reference_sha256=baseline['assembly_sha256'], target_sha256=target['assembly_sha256'],
        parts=results, new_or_changed_initialized_fields=rva,
        note='Only appli1./appli2. prefixes removed; locals and exception handlers retained. '
             'RVA differences are reported separately. This is not runtime validation.'))
    (p.WORK/'research/dual-engine.diff').write_text('\n'.join(diff)+'\n', encoding='utf-8')
    for part, value in results.items():
        print(part, 'identical full bodies:', len(value['identical_methods']),
              'changed:', len(value['changed_methods']), 'fields equal:', value['fields_equal'])


if __name__ == '__main__':
    main()
