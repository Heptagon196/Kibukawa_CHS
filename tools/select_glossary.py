"""Read public baseline AND the current game's glossary for a chapter."""
import argparse
import json
import unicodedata
from project_config import ROOT, resolve, read

SECTIONS=('characters','terms','non_translate')
RULE_FIELDS=('rules','chinese_only_clue_rendering','snowman_distinction','second_game_policy','interface_short_forms','textual_clues')

def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def normal(text):return unicodedata.normalize('NFKC',text)

def normalize_local(data):
    result={key:[] for key in SECTIONS}
    for field,section in [('characters','characters'),('terms','terms'),('game_terms','terms'),('non_translate','non_translate')]:
        for index,row in enumerate(data.get(field,[])):
            canonical=row.get('canonical',row.get('src',row.get('source',row.get('marker'))))
            render=row.get('render',row.get('dst',row.get('target',row.get('marker'))))
            result[section].append(dict(row,canonical=canonical,render=render,
                status=row.get('status','local_locked'),local_ref=field+'/'+str(index)))
    return result

def conflicts(public,local):
    result=[]
    for section in SECTIONS:
        for current in local[section]:
            for prior in public[section]:
                if normal(current['canonical'])==normal(prior['canonical']) and current['render']!=prior['render']:
                    result.append(dict(section=section,source=current['canonical'],public_render=prior['render'],local_render=current['render'],
                        action='Review required; neither table automatically overrides the other.',local_ref=current['local_ref']))
    return result

def select(game,script):
    project=resolve(game,allow_disabled=True)
    manifest=load(project['project']/'work/manifest.json')
    sources=[entry['source_text'] for entry in manifest['entries'] if not entry.get('excluded') and entry['group'] in (script,script+'.txt')]
    if not sources:raise ValueError('No source group: '+script)
    corpus=normal(''.join(sources))
    public=load(ROOT/'series/glossary.json')
    config=load(project['project']/'project.json')
    local_path=project['project']/config.get('glossary','work/glossary.locked.json')
    local_data=load(local_path);local=normalize_local(local_data)
    order=list(read()['games']);before=set(order[:order.index(game)])
    # A later entry in the public baseline must not leak into an earlier game.
    baseline={section:[x for x in public[section] if x['first_recorded_game'] in before] for section in SECTIONS}
    def matching(table):
        result={section:[] for section in SECTIONS}
        for section in SECTIONS:
            for entry in table[section]:
                forms=[x for x in [entry['canonical'],*entry.get('aliases',[])] if x and normal(x) in corpus]
                if forms:result[section].append(dict(entry,matched_forms=forms))
        return result
    selected_public=matching(baseline);selected_local=matching(local)
    # Conflicting same-source entries must be visible even when matched via only one alias.
    all_conflicts=conflicts(baseline,local)
    visible={normal(x['canonical']) for table in (selected_public,selected_local) for section in SECTIONS for x in table[section]}
    active_conflicts=[x for x in all_conflicts if normal(x['source']) in visible]
    prior_rules=load(ROOT/'series'/public['rules_file'])
    relevant_games={x['first_recorded_game'] for section in SECTIONS for x in selected_public[section]}
    return dict(game=game,script=script,
        policy='Always read public and local together. Matches are candidates, not identity detection. Local additions and provisional terms stay local; explicit review is required for conflicts.',
        public=selected_public,local=selected_local,conflicts=active_conflicts,
        public_rules={key:prior_rules['games'][key]['rules'] for key in sorted(relevant_games) if key in prior_rules['games']},
        local_rules={key:local_data[key] for key in RULE_FIELDS if key in local_data},
        local_table=str(local_path.relative_to(ROOT)),default_usage=public['default_usage'],ambiguities=public['ambiguities'])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',required=True);parser.add_argument('--script',required=True)
    args=parser.parse_args();print(json.dumps(select(args.game,args.script),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
