"""Verify compact glossary references directly against per-game locked tables."""
import collections
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))

def main():
    config=load(ROOT/'series.json');public=load(ROOT/'series/glossary.json')
    assert public['schema']==2
    rules_path=(ROOT/'series'/public['rules_file']).resolve()
    assert rules_path.is_relative_to((ROOT/'series').resolve())
    rules=load(rules_path)
    expected={}
    assert set(public['source_tables'])==set(public['source_projects']), 'Baseline provenance inventory differs'
    assert set(public['source_projects']).issubset(config['games']), 'Unknown baseline game'
    for game in public['source_projects']:
        entry=config['games'][game]
        path=entry['project']+'/work/glossary.locked.json';file=ROOT/path
        reference=public['source_tables'][game]
        assert reference['path']==path and reference['sha256']==hashlib.sha256(file.read_bytes()).hexdigest(), 'Source changed: '+game
        data=load(file)
        for section in ('characters','terms','game_terms','non_translate'):
            for index,record in enumerate(data.get(section,[])):
                expected[f'{game}/{section}/{index}']=record
        assert rules['games'][game]['source_table']==path
        for key in ('chinese_only_clue_rendering','snowman_distinction','second_game_policy','interface_short_forms','textual_clues'):
            if key in data:assert rules['games'][game]['rules'][key]==data[key], 'Game rule missing: '+key
    seen=set();spellings=collections.defaultdict(set)
    for section in ('characters','terms','non_translate'):
        identities=set()
        for row in public[section]:
            key=(row['canonical'],row['render'])
            assert key not in identities,'Duplicate normalized row'
            identities.add(key)
            assert row['status'] in ('project_locked','preserve_in_context')
            assert row['source_refs'],'Missing source reference'
            for ref in row['source_refs']:
                assert ref in expected and ref not in seen,'Invalid or duplicate source reference: '+ref
                seen.add(ref);record=expected[ref]
                source_section=ref.split('/')[1]
                assert section==('terms' if source_section=='game_terms' else source_section),'Wrong section'
                canonical=record.get('canonical',record.get('src',record.get('source',record.get('marker'))))
                render=record.get('render',record.get('dst',record.get('target',record.get('marker'))))
                assert (canonical,render)==key,'Source mapping differs'
                assert set(record.get('aliases',[])).issubset(row.get('aliases',[])),'Alias lost'
                if record.get('keep_source'):assert row.get('keep_source') is True
            if section!='non_translate':
                for word in [row['canonical'],*row.get('aliases',[])]:spellings[word].add((section,*key))
    # Provenance is auxiliary; a public baseline need not archive every local record.
    assert {k for k,v in spellings.items() if len(v)>1}=={x['source'] for x in public['ambiguities']},'Missing ambiguity'
    assert all(x['first_recorded_game'] in public['source_projects'] for section in ('characters','terms','non_translate') for x in public[section])
    print('PASS: '+str(len(seen))+' source records directly referenced; source hashes, mappings, aliases, game rules and ambiguities verified.')
    print({k:len(public[k]) for k in ('characters','terms','non_translate')})

if __name__=='__main__':main()
