"""Import and audit eighth-game tagged drafts without installing or approving them."""
import argparse
import collections
import re
from translation_io import WORK, load, save, digest, plain, check_target


def collect():
    document = load(WORK/'work/dialogue-tagged.json')
    lookup = {u['id']: u for u in document['units']}
    imported = 0
    batch_records = []
    for path in sorted((WORK/'work/batches').glob('*.zh-CN.json')):
        batch = load(path)
        source = load(path.with_name(path.name.replace('.zh-CN.json', '.source.json')))
        if len(batch['units']) != len(source['units']):
            raise ValueError('Missing units: ' + path.name)
        done = 0
        for row, origin in zip(batch['units'], source['units']):
            if any(row.get(key) != origin[key] for key in ('id','source','kind')):
                raise ValueError('Source/order changed: ' + path.name)
            unit = lookup[row['id']]
            if unit['source'] != row['source']:
                raise ValueError('Stale source: ' + row['id'])
            if not row['target']:
                continue
            check_target(row['source'], row['target'])
            if not plain(row['target']).strip():
                raise ValueError('Empty visible target: ' + row['id'])
            unit['target'] = row['target']
            unit['translation_status'] = 'draft'
            unit['translation_notes'] = row.get('notes', '')
            done += 1
        imported += done
        batch_records.append(dict(file=path.name, translated=done, total=len(source['units']), digest=digest(batch)))
    save(WORK/'work/dialogue-tagged.json', document)
    cache = load(WORK/'work/cache.json')
    manifest = load(WORK/'work/manifest.json')
    cache['files'] = {}
    entries = []
    for index, unit in enumerate(document['units'], 1):
        asset, member = unit['script'].split('/')
        location = dict(kind='script', file='kibu8_Data/StreamingAssets/scratchpad', asset=asset,
                        member=member, instruction=unit['instruction'], opcode=unit['opcode'], unit_id=unit['id'])
        if 'argument' in unit:
            location['argument'] = unit['argument']
        group = unit['script'] + '.txt'
        entries.append(dict(text_index=index, source_text=plain(unit['source']), tagged_source=unit['source'],
                            location=location, group=group, excluded=False))
        row = dict(text_index=index,source_text=plain(unit['source']),translated_text=plain(unit['target']),
                   translation_status=1 if unit['target'] else 0,model='Codex collaborative draft',
                   extra=dict(location=location,tagged_source=unit['source'],tagged_target=unit['target'],note=unit.get('translation_notes','')))
        cache['files'].setdefault(group,dict(storage_path=group,encoding='utf-8',file_project_type='Txt',
                  line_ending='\n',items=[],extra={}))['items'].append(row)
    for name in ('ui-localization.zh-CN.json','ui-assembly.zh-CN.json','ui-serialized.zh-CN.json'):
        ui = load(WORK/'work'/name)
        group = name.replace('.zh-CN.json','.txt')
        rows = []
        for item in ui['entries']:
            index = len(entries) + 1
            technical = item['classification']=='technical_sentinel' or item['classification'].startswith('excluded_')
            location = dict(kind='serialized' if 'asset_file' in item else ('csv' if 'row' in item else 'assembly'),file=item.get('asset_file',ui.get('source_asset')))
            if 'asset_file' in item:
                location.update({k:item[k] for k in ('serialized_file','path_id','byte_offset','length_prefix_offset','serialized_byte_offset','script_class','fields') if k in item})
                manifest['source_hashes'][item['asset_file']] = manifest['game_hashes'][item['asset_file']]
            location.update({k:item[k] for k in ('row','key','token','instruction','method') if k in item})
            entries.append(dict(text_index=index,source_text=item['source_text'],location=location,group=group,excluded=technical))
            rows.append(dict(text_index=index,source_text=item['source_text'],translated_text=item['target_text'] or '',
                 translation_status=7 if technical else 1,model='Codex UI draft',
                 extra=dict(location=location,note=item.get('notes',''),classification=item['classification'])))
        cache['files'][group]=dict(storage_path=group,encoding='utf-8',file_project_type='Txt',line_ending='\n',items=rows,extra={})
    cache['extra'] = dict(translation_stage='draft',coverage='Validated scenario display blocks, visible string arguments and separate UI drafts.',
                         semantic_release_review_complete=False)
    manifest['entries'] = entries
    manifest['coverage'] = 'All scenario VM commands parsed; display opcodes and visible string operands extracted. Serialized UI positions are indexed separately; image text and runtime integration remain pending.'
    save(WORK/'work/cache.json',cache)
    save(WORK/'work/manifest.json',manifest)
    save(WORK/'reports/batch-import.json',dict(imported=imported,batches=batch_records,document_digest=digest(document)))
    return audit()


def audit():
    document = load(WORK/'work/dialogue-tagged.json')
    pending, findings = [], []
    for unit in document['units']:
        if not unit['target']:
            pending.append(unit['id'])
            continue
        check_target(unit['source'],unit['target'])
        text = plain(unit['target'])
        if unit['kind']=='menu_prompt' and len(text)>6:
            findings.append(dict(id=unit['id'],rule='menu_title_max_6',target=unit['target']))
        if '软键' in text:
            findings.append(dict(id=unit['id'],rule='unmapped_softkey',target=unit['target']))
        # Japanese middle dots/iteration symbols and original waving emoticons are punctuation.
        scanned = re.sub(r'(?<=[)）])ノ', '', text)
        for emoticon in ('（＠ω＠；ノ','ΣΣ（◎ω◎ノノ'):
            if emoticon in plain(unit['source']):
                scanned = scanned.replace(emoticon, '')
        if re.search(r'[\u3041-\u3096\u30a1-\u30fa\uff66-\uff9d]',scanned):
            findings.append(dict(id=unit['id'],rule='japanese_candidate',source=unit['source'],target=unit['target']))
        if any(0xe000<=ord(c)<=0xf8ff for c in text):
            findings.append(dict(id=unit['id'],rule='private_use_glyph',source=unit['source'],target=unit['target']))
    import pipeline  # Resolve the configured adapter for standalone audits too.
    from menu_constraints import short_choice_offsets
    from vm import parse_bin
    lookup={(u['script'],u['instruction']):u for u in document['units']}
    for path in (WORK/'raw').rglob('*.bin'):
        # start contains the original developer sound-test list, not investigation topics.
        if path.stem=='start': continue
        script=path.parent.name+'/'+path.stem
        for offset in short_choice_offsets(parse_bin(path.read_bytes())['commands']):
            unit=lookup.get((script,offset))
            if unit and len(plain(unit['target']))>6:
                findings.append(dict(id=unit['id'],rule='short_menu_max_6',target=unit['target']))
    result = dict(total=len(document['units']),translated=len(document['units'])-len(pending),pending=len(pending),
                  structure_valid=True,document_digest=digest(document),findings=findings,pending_ids=pending,
                  note='Structure checks are not semantic approval, click/color review baselines, or runtime validation.')
    save(WORK/'reports/translation-audit.json',result)
    print({k:result[k] for k in ('total','translated','pending','structure_valid')},'review candidates:',len(findings))
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['collect','check'])
    parser.add_argument('--complete',action='store_true')
    args=parser.parse_args()
    result=collect() if args.action=='collect' else audit()
    if args.complete and (result['pending'] or result['findings']):
        raise SystemExit('Draft has pending text or review candidates')
