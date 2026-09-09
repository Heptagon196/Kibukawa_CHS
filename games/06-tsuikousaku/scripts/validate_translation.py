"""Read-only offline validation for the sixth game's reviewed text (no baseline creation)."""
import collections
import re
import pipeline as p
from review_units import current
import sys
sys.path.insert(0, str(p.SERIES/'tools'))
from click_boundaries import validate

def main():
    manifest=p.validate_sources();config=p.load(p.WORK/'project.json');cache=p.load(p.WORK/'work/cache.json')
    entries=manifest['entries'];all_rows=[r for group in cache['files'].values() for r in group['items']]
    rows={r['text_index']:r for r in all_rows}
    p.require(len(rows)==len(all_rows)==len(entries),'Missing or duplicate cache rows')
    approved_kana=[];empty=[];preserved=[]
    tokens=lambda s:collections.Counter(re.findall(r'\{\d+(?:[^{}]*)\}|</?[A-Za-z][^>]*>',s))
    for e in entries:
        i=e['text_index'];r=rows[i];t=r['translated_text'];s=e['source_text']
        p.require(r['source_text']==s and r['extra']['location']==e['location'],'Source/location changed: '+str(i))
        if e['excluded']:
            p.require(r['translation_status']==7,'Excluded entry status changed: '+str(i));continue
        p.require(r['translation_status'] in (1,2),'Untranslated entry: '+str(i))
        p.require(tokens(s)==tokens(t),'Placeholder mismatch: '+str(i))
        p.require('\x00' not in t and '\t' not in t,'Unexpected control: '+str(i))
        if e['location']['kind']=='script':
            p.require('\n' not in t and '\r' not in t and len(t.encode('utf-16-le'))//2<=20,'Script capacity: '+str(i))
        else:p.require(t.count('\n')==s.count('\n') and t.count('\r')==s.count('\r'),'UI line structure: '+str(i))
        if re.search(r'[ぁ-ゖァ-ヺｦ-ﾟ]',t):
            a=config.get('approved_retained_text',{}).get(str(i),{})
            p.require(a.get('source')==s and a.get('target')==t and a.get('reason'),'Unreviewed Japanese: '+str(i));approved_kana.append(i)
        if t!=t.strip():
            a=config.get('approved_layout_text',{}).get(str(i),{})
            p.require(a.get('source')==s and a.get('target')==t and a.get('reason'),'Unexpected whitespace: '+str(i));preserved.append(i)
        if not t:
            p.require((config.get('approved_empty_name_readings',{}).get(str(i))==s or (config.get('approved_empty_layout_text',{}).get(str(i),{}).get('source')==s and config['approved_empty_layout_text'][str(i)].get('target')=='' and config['approved_empty_layout_text'][str(i)].get('reason'))) and r['extra'].get('empty_translation_reason'),'Unapproved empty: '+str(i));empty.append(i)
    from tagged_dialogue import validate as validate_tags
    validate_tags()
    commands,lookup=current();click=validate(commands,p.WORK,strict=True)
    previous=p.load(p.WORK/'reports/previous-projects-extract-baseline.json')
    p.require(p.first_project_hashes()==previous,'Earlier project files changed')
    p.require(p.game_hashes()==manifest['game_hashes'],'Original game files changed')
    report=dict(game='kibu6',translated=sum(not e['excluded'] for e in entries),pending=0,excluded=sum(e['excluded'] for e in entries),
        source_and_locations_unchanged=True,previous_projects_unchanged=True,game_files_unchanged=True,
        click_units=click['unit_count'],click_review=click['status'],approved_kana=approved_kana,approved_empty_name_readings=empty,
        approved_layout_whitespace=preserved,unapproved_kana=0,cache_sha256=p.sha((p.WORK/'work/cache.json').read_bytes()),
        manifest_sha256=p.sha((p.WORK/'work/manifest.json').read_bytes()),runtime_tested=False,translation_patch_ready=False,
        scope='All extracted translatable text; static review only. No game launch, installation, font, artwork or runtime-layout approval.')
    p.save(p.WORK/'reports/full-text-validation.json',report)
    print('PASS: '+str(report['translated'])+' translated; '+str(click['unit_count'])+' reviewed click units; sources, original game and previous projects unchanged.')
if __name__=='__main__':main()
