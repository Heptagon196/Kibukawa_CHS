"""Identify explicit, reciprocal script pagination without rewriting VM bytes."""
import hashlib
import json
from pathlib import Path
from vm import parse_bin


def groups(parsed):
    menus, edges, current = {}, [], None
    for c in parsed['commands']:
        if c['name'] in ('KOMANDO', 'CHOUBUN_KOMANDO'):
            current = c
            menus[c['offset']] = c
        elif c['name'] == 'SENTAKUSI' and current:
            args = [a['value'] for a in c['args']]
            if args[0] in ('次のページへ', '前のページへ'):
                edges.append((current['offset'], parsed['labels'][args[-1]]))
        elif c['name'] != 'BUNKI':
            current = None
    graph = {}
    for a, b in edges:
        if a in menus and b in menus and (b, a) in edges:
            graph.setdefault(a, set()).add(b)
            graph.setdefault(b, set()).add(a)
    result = []
    while graph:
        pending, seen = [min(graph)], set()
        while pending:
            n = pending.pop()
            if n in seen:
                continue
            seen.add(n)
            pending.extend(graph.get(n, ()))
        pages = sorted(seen)
        root = menus[pages[0]]
        back = root['args'][-1]['value']
        # Only same-kind pages with a genuine external cancel destination.
        if back >= 0 and parsed['labels'][back] not in seen and all(
                menus[n]['opcode'] == root['opcode'] for n in pages):
            result.append([back, *[n + 1 for n in pages]])
        for n in seen:
            graph.pop(n, None)
    return result


def generate(game):
    entries = {}
    for path in sorted((game / 'raw').rglob('*.bin')):
        raw = path.read_bytes()
        parsed = parse_bin(raw)
        found = groups(parsed)
        if found:
            body = raw[parsed['script_offset']:parsed['script_offset'] + parsed['script_size']]
            entries[hashlib.sha256(body).hexdigest()] = found
    source = 'using System.Collections.Generic;\nnamespace Kibukawa.Engine.Gmode20050817 {\n'
    source += 'internal static class NativePaginationData { internal static readonly Dictionary<string,int[][]> Groups = new Dictionary<string,int[][]> {\n'
    for digest, values in sorted(entries.items()):
        source += '{"' + digest + '",new int[][]{' + ','.join(
            'new int[]{' + ','.join(map(str, g)) + '}' for g in values) + '}},\n'
    source += '}; } }\n'
    (game / 'bepinex/src/NativePaginationData.cs').write_text(source, encoding='utf-8')
    (game / 'reports/pagination-groups.json').write_text(json.dumps(entries, indent=2) + '\n', encoding='utf-8')
