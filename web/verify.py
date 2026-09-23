"""Verify source hashes, control markers, and locked series terminology."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent

# These are established in series/glossary.json.  The web games predate the
# shared pipeline, so keep a small executable bridge here until they have
# per-title locked glossaries of their own.
REQUIRED_DIALOGUE_TERMS = {
    '音成孝一': '林居孝一',
    'オバキュー': '尾Q',
    '鞠浜警察署': '鞠滨警署',
}
FORBIDDEN_TARGET_TERMS = ('音成', '鞠滨警察署')
REQUIRED_ROWS = {
    ('birthday', 'scene1.ks:480'): '这个先不提',
    ('birthday', 'scene2.ks:479'): '这个先不提',
    ('saina-onsen', 's01.adv:1440'): '这个先不提',
}
REQUIRED_UI = {
    ('operation-check-2', 'あそびかた'): '玩法说明',
    ('operation-check-2', '捜査中断'): '中断调查',
    ('operation-check-2', 'タイトル画面に戻る'): '返回标题',
    ('operation-check-2', '探偵事務所前'): '侦探事务所门前',
    ('saina-onsen', '話すと音成電話'): '交谈后林居来电',
    ('saina-onsen', '音成行ってから'): '从林居离开后开始',
    ('saina-onsen', '話すと音成'): '交谈后转入林居段落',
}


def plain(text):
    """Remove engine tags while retaining visible characters."""
    return re.sub(r'\[[^\]]*\]', '', text)


def load_ui(game):
    if game == 'operation-check-2':
        return json.loads((ROOT / game / 'work/ui.json').read_text(encoding='utf-8'))
    if game == 'saina-onsen':
        result = {}
        for line in (ROOT / game / 'work/ui.tsv').read_text(encoding='utf-8').splitlines():
            source, target = line.split('\t', 1)
            result[source] = target
        return result
    return {}


def verify_terminology(all_rows):
    target_cells = []
    matched = {source: 0 for source in REQUIRED_DIALOGUE_TERMS}
    for game, rows in all_rows.items():
        by_id = {row['id']: row for row in rows}
        for row in rows:
            source = plain(row['source'])
            target = plain(row['target'])
            target_cells.append((game, row['id'], target))
            for locked_source, locked_target in REQUIRED_DIALOGUE_TERMS.items():
                if locked_source in source:
                    assert locked_target in target, (game, row['id'], locked_source, locked_target)
                    matched[locked_source] += 1
        for (locked_game, row_id), locked_target in REQUIRED_ROWS.items():
            if locked_game == game:
                assert locked_target in plain(by_id[row_id]['target']), (game, row_id, locked_target)

    ui_cells = 0
    for game in ('operation-check-2', 'saina-onsen'):
        ui = load_ui(game)
        for (locked_game, source), target in REQUIRED_UI.items():
            if locked_game == game:
                assert ui[source] == target, (game, source, ui[source], target)
        target_cells.extend((game, f'ui:{source}', target) for source, target in ui.items())
        ui_cells += len(ui)

    for game, cell_id, target in target_cells:
        for forbidden in FORBIDDEN_TARGET_TERMS:
            assert forbidden not in plain(target), (game, cell_id, forbidden)
    assert all(matched.values()), matched
    return {'dialogue_rules': matched, 'ui_cells': ui_cells, 'forbidden_terms': 0}


def verify_saina_tsv(rows):
    """Ensure reviewed TSV entries and the canonical dialogue table agree."""
    by_id = {row['id']: row for row in rows}
    expected = {}
    for path in sorted((ROOT / 'saina-onsen/work/translations').glob('*.tsv')):
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line or line.startswith('#'):
                continue
            row_id, target = line.split('\t', 1)
            source = by_id[row_id]['source']
            suffix = re.search(r'(?:\[(?:r|rr|p|pp|ppp|l|ll)\])+$', source)
            if suffix and not re.search(r'\[(?:r|rr|p|pp|ppp|l|ll)\]$', target):
                target += suffix.group()
            expected[row_id] = (path.name, target)
    for row_id, (filename, target) in expected.items():
        assert by_id[row_id]['target'] == target, (filename, row_id)
    return len(expected)


def main():
    results = {}
    all_rows = {}
    for game in ('birthday', 'operation-check-2', 'saina-onsen'):
        path = ROOT / game
        manifest = json.loads((path / 'source-manifest.json').read_text(encoding='utf-8'))
        for name, digest in manifest['files'].items():
            assert hashlib.sha256((path / 'originals' / name).read_bytes()).hexdigest() == digest, (game, name)
        rows = json.loads((path / 'work/dialogue.json').read_text(encoding='utf-8'))
        all_rows[game] = rows
        translated = [row for row in rows if row['target']]
        for row in translated:
            pattern = r'\[(?:lp|ll|lr|ler|p|l|me|\$[^\]]+)\]'
            if game == 'saina-onsen':
                pattern = r'\[(?:r|rr|p|pp|ppp|pp_j|l|ll)\]'
            assert re.findall(pattern, row['source']) == re.findall(pattern, row['target']), row['id']
        results[game] = {
            'rows': len(rows),
            'translated': len(translated),
            'control_mismatches': 0,
            'sources_verified': len(manifest['files']),
        }
    results['saina-onsen']['reviewed_tsv_rows'] = verify_saina_tsv(all_rows['saina-onsen'])
    results['terminology'] = verify_terminology(all_rows)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
