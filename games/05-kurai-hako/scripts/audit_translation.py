"""Read-only audit of the fifth game's translated subset and protected files."""
import collections
import re
import pipeline as p


def main():
    manifest=p.validate_sources()
    cache_path=p.WORK/'work/cache.json'
    original=cache_path.read_bytes();cache=p.load(cache_path)
    rows=[x for f in cache['files'].values() for x in f['items']]
    by_id={x['text_index']:x for x in rows}
    p.require(len(rows)==len(by_id)==len(manifest['entries']),'Missing or duplicate cache IDs')
    config=p.load(p.WORK/'project.json')
    translated={}
    for entry in manifest['entries']:
        row=by_id[entry['text_index']]
        p.require(row['source_text']==entry['source_text'] and row['extra']['location']==entry['location'],'Source mapping changed')
        if entry['excluded']:
            p.require(row['translation_status']==7 and row['translated_text']=='','Excluded row changed')
        elif row['translation_status']==0:
            p.require(row['translated_text']=='','Pending row has unclassified translation')
        else:
            p.require(row['translation_status'] in (1,2),'Invalid status')
            value=row['translated_text'];translated[row['text_index']]=value
            retained=config.get('approved_retained_text',{}).get(str(row['text_index']),{})
            approved=retained.get('source')==row['source_text'] and retained.get('target')==value and bool(retained.get('reason'))
            p.require(not re.search(r'[ぁ-ゖァ-ヺｦ-ﾟ]',value) or approved,'Unapproved kana')
            p.require('\x00' not in value and '\t' not in value,'Control character')
            if row['extra']['location']['kind']=='script':
                p.require(not any(c in value for c in '\r\n'),'Script newline')
            else:
                p.require('\n' not in value or '\n' in row['source_text'],'Unexpected UI newline')
            layout=config.get('approved_layout_text',{}).get(str(row['text_index']),{})
            p.require(value==value.strip() or (layout.get('source')==row['source_text'] and layout.get('target')==value and bool(layout.get('reason'))),'Unexpected whitespace')
            if row['extra']['location']['kind']=='script':
                p.require(len(value.encode('utf-16-le'))//2<=20,'Script exceeds conservative buffer')
            if not value:
                p.require(config['approved_empty_name_readings'].get(str(row['text_index']))==row['source_text'],'Unapproved empty reading')
    for index, rule in config.get('approved_source_passthrough',{}).items():
        row=by_id[int(index)]
        p.require(row['source_text']==rule['source']==rule['target']==row['translated_text'] and bool(rule.get('reason')),'Preserved identifier changed')
    drafts={};draft_hashes={}
    for path in sorted((p.WORK/'work/drafts').glob('*.json')):
        draft=p.load(path)
        p.require(draft['manifest_sha256']==p.sha((p.WORK/'work/manifest.json').read_bytes()),'Stale draft source')
        for entry in draft['entries']:
            index=entry['id'];p.require(index not in drafts,'Duplicate draft ID')
            p.require(entry['source']==by_id[index]['source_text'],'Draft source mismatch')
            drafts[index]=entry['target']
        draft_hashes[path.name]=p.sha(path.read_bytes())
    p.require(drafts==translated,'Draft coverage/content differs from cache')
    for name,group in cache['files'].items():
        done=[x for x in group['items'] if x['translation_status'] in (1,2)]
        if not done:continue
        expected='\n'.join(f'[{x["text_index"]}] {x["translated_text"]}' for x in done)
        p.require((p.WORK/'translated_texts'/name).read_text(encoding='utf-8')==expected,'Readable export stale')
    p.require(p.first_project_hashes()==p.load(p.WORK/'reports/previous-projects-extract-baseline.json'),'Prior project changed')
    current_game=p.game_hashes()
    p.require(all(current_game.get(name)==digest for name,digest in manifest['game_hashes'].items()),'Original game files changed')
    added={name:digest for name,digest in current_game.items() if name not in manifest['game_hashes']}
    if added:
        installation=p.load(p.WORK/'reports/installation_latest.json')
        p.require(installation['status']=='installed' and added==installation['files'],'Unverified game additions')
    p.require(cache_path.read_bytes()==original,'Audit changed cache')
    result=dict(processed=len(translated),translated_content_slots=len(translated)-len(config.get('approved_source_passthrough',{})),preserved_debug_identifiers=len(config.get('approved_source_passthrough',{})),statuses=dict(collections.Counter(x['translation_status'] for x in rows)),
                draft_hashes=draft_hashes,cache_sha256=p.sha(original),
                sources_and_locations_preserved=True,prior_projects_unchanged=True,game_unchanged=not bool(added),original_game_files_unchanged=True,installed_patch_files_verified=len(added),
                draft_cache_exports_match=True,approved_empty_readings=config['approved_empty_name_readings'],
                max_script_utf16=max((len(v.encode('utf-16-le'))//2 for i,v in translated.items() if by_id[i]['extra']['location']['kind']=='script'),default=0),runtime_tested=False)
    p.save(p.WORK/'reports/translation-audit.json',result)
    print(result)

if __name__=='__main__':main()
