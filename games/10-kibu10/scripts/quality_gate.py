"""Strict, repeatable Chinese-content release checks for the tenth game."""
import argparse
import hashlib
import html
import re

import pipeline as p
from runtime_pack import fullwidth
from quality_reviewed import COLOR_PUNCTUATION, ELLIPSIS

TAG = re.compile(r'(<[^>]+>)')
ELLIPSIS_RUN = re.compile(r'…+')
SOURCE_QUOTES = set('「」『』“”‘’')
TARGET_SINGLE_QUOTES = set('‘’')
TERMINAL_PUNCTUATION = set('，。！？、')
CJK = r'\u3400-\u9fff'
CHOICE_MAX_WIDTH = 7 * 12


def native_choice_width(value):
    """Measure script choices in the game's 12px/6px menu grid."""
    text = fullwidth(html.unescape(value))
    def han(c): return '\u3400' <= c <= '\u9fff' or c == '〇'
    def narrow(c): return '０' <= c <= '９' or 'Ａ' <= c <= 'Ｚ' or 'ａ' <= c <= 'ｚ'
    width = 0
    for index, char in enumerate(text):
        if index and (han(text[index - 1]) and narrow(char) or narrow(text[index - 1]) and han(char)):
            width += 6
        mixed_blank = (char == '　' and 0 < index < len(text) - 1 and
                       (han(text[index - 1]) and narrow(text[index + 1]) or
                        narrow(text[index - 1]) and han(text[index + 1])))
        width += 6 if narrow(char) or mixed_blank else 12
    return width


def plain(value):
    return html.unescape(re.sub(r'<[^>]+>', '', value))


def pair_digest(source, target):
    return hashlib.sha256((source + '\0' + target).encode('utf-8')).hexdigest()


def issue(unit, rule, **extra):
    return dict(id=unit['id'], rule=rule, **extra)


def colored_spans(unit):
    source = re.split(TAG, unit['source'])
    target = re.split(TAG, unit['target'])
    if re.findall(TAG, unit['source']) != re.findall(TAG, unit['target']):
        return
    color = None
    for token, (src, dst) in enumerate(zip(source, target)):
        if src.startswith('<color='):
            color = int(src[7:-1])
        elif src == '</color>':
            color = None
        elif not src.startswith('<') and color not in (None, 0) and (src or dst):
            yield unit['id'] + ':token' + str(token), color, html.unescape(src), html.unescape(dst)


def inspect_document(document):
    findings = []
    active = [u for u in document['units'] if u['active']]
    seen_ellipsis_exceptions = set()
    seen_color_exceptions = set()
    script_quotes = {}
    for unit in active:
        source_text = plain(unit['source'])
        target_text = plain(unit['target'])

        if unit.get('kind') == 'choice' and native_choice_width(target_text) > CHOICE_MAX_WIDTH:
            findings.append(issue(unit, 'choice_width', pixels=native_choice_width(target_text),
                                  maximum=CHOICE_MAX_WIDTH))

        if not unit['target']:
            findings.append(issue(unit, 'missing_target'))
        if re.search(r'[' + CJK + r'][,.!?]|[,.!?][' + CJK + r']', target_text):
            findings.append(issue(unit, 'mixed_ascii_chinese_punctuation'))
        if re.search(r'[「」『』]', target_text):
            findings.append(issue(unit, 'japanese_quote_in_target'))
        script = unit.get('script', unit['id'].rsplit(':', 1)[0])
        quote_counts = script_quotes.setdefault(script, [0, 0, 0, 0])
        for index, quote in enumerate(('“', '”', '‘', '’')):
            quote_counts[index] += target_text.count(quote)

        source_rows = unit['source'].split('<row/>')
        target_rows = unit['target'].split('<row/>')
        if len(source_rows) != len(target_rows):
            findings.append(issue(unit, 'row_count_mismatch', source=len(source_rows), target=len(target_rows)))
        else:
            for row, (source_row, target_row) in enumerate(zip(source_rows, target_rows)):
                if plain(source_row).strip() and not plain(target_row).strip():
                    findings.append(issue(unit, 'empty_target_row', row=row))

        for match in re.finditer(r'…{2,}。', target_text):
            findings.append(issue(unit, 'redundant_ellipsis_period', text=match.group()))
        for match in re.finditer(r'，…{2,}', target_text):
            findings.append(issue(unit, 'redundant_comma_ellipsis', text=match.group()))

        source_runs = ELLIPSIS_RUN.findall(source_text)
        target_runs = ELLIPSIS_RUN.findall(target_text)
        if len(source_runs) != len(target_runs):
            digest = pair_digest(unit['source'], unit['target'])
            if ELLIPSIS.get(unit['id']) == digest:
                seen_ellipsis_exceptions.add(unit['id'])
            else:
                findings.append(issue(unit, 'ellipsis_run_count', source=len(source_runs), target=len(target_runs)))

        for span_id, color, source, target in colored_spans(unit) or ():
            digest = pair_digest(source, target)
            if any(q in target for q in TARGET_SINGLE_QUOTES) and not any(q in source for q in SOURCE_QUOTES):
                findings.append(issue(unit, 'added_quote_in_highlight', span=span_id, color=color,
                                      source=source, target=target))
            if target and target[-1] in TERMINAL_PUNCTUATION and (not source or source[-1] not in TERMINAL_PUNCTUATION):
                if COLOR_PUNCTUATION.get(span_id) == digest:
                    seen_color_exceptions.add(span_id)
                else:
                    findings.append(issue(unit, 'added_terminal_punctuation_in_highlight', span=span_id,
                                          color=color, source=source, target=target))

    for script, (double_open, double_close, single_open, single_close) in sorted(script_quotes.items()):
        if double_open != double_close:
            findings.append(dict(id=script, rule='unbalanced_double_quotes',
                                 opening=double_open, closing=double_close))
        if single_open != single_close:
            findings.append(dict(id=script, rule='unbalanced_single_quotes',
                                 opening=single_open, closing=single_close))

    stale_ellipsis = sorted(set(ELLIPSIS) - seen_ellipsis_exceptions)
    stale_color = sorted(set(COLOR_PUNCTUATION) - seen_color_exceptions)
    for unit_id in stale_ellipsis:
        findings.append(dict(id=unit_id, rule='stale_reviewed_ellipsis_exception'))
    for span_id in stale_color:
        findings.append(dict(id=span_id.rsplit(':token', 1)[0], rule='stale_reviewed_color_exception', span=span_id))

    counts = {}
    for finding in findings:
        counts[finding['rule']] = counts.get(finding['rule'], 0) + 1
    return dict(schema=1, status='passed' if not findings else 'failed', active_units=len(active),
                reviewed_ellipsis_exceptions=len(seen_ellipsis_exceptions),
                reviewed_color_exceptions=len(seen_color_exceptions), counts=counts, findings=findings,
                note='Reviewed exceptions are bound to exact source/target content hashes; edits require re-review.')


def check(strict=False, document=None, write_report=True):
    report = inspect_document(document or p.load(p.WORK/'work/dialogue-tagged.json'))
    if write_report:
        p.save(p.WORK/'reports/quality-gate.json', report)
    if strict and report['status'] != 'passed':
        raise ValueError('Chinese content quality gate failed: ' + repr(report['counts']))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()
    result = check(strict=args.strict)
    print({k: result[k] for k in ('status', 'active_units', 'counts')})
