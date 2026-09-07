"""Read-only editorial audit. Script-order quote findings require contextual review."""
import argparse
from collections import Counter
import hashlib
import json
import re
from project_config import ROOT, read, resolve

PAIRS = {'“': '”', '‘': '’', '「': '」', '『': '』'}


def inspect_rows(rows):
    findings = []
    stacks = {}

    def flag(row, rule, detail):
        findings.append(dict(id=row['text_index'], rule=rule, detail=detail,
                             source=row.get('source_text', ''), target=row['translated_text'],
                             location=row.get('extra', {}).get('location', {})))

    for row in rows:
        if row.get('translation_status') not in (1, 2):
            continue
        value = row.get('translated_text', '')
        if not value:
            continue
        if not value.strip():
            flag(row, 'spacing_layout', '纯空白条目：复核是否为刻意排版，不自动删除')
            continue
        if value != value.strip():
            flag(row, 'spacing_edge', '首尾空白：复核原文折行缩进是否误入译文')
        if re.search(r'[\u3400-\u9fff，。！？；：、][ \t\u3000]+[\u3400-\u9fff，。！？；：、]', value):
            flag(row, 'spacing_inside', '中文之间存在空白')
        if re.search(r'[^\S\r\n]{2,}|[\t\u00a0\u200b\ufeff]', value):
            flag(row, 'spacing_unusual', '连续空白、制表符或不可见空格：复核排版用途')
        loc = row.get('extra', {}).get('location', {})
        # Dialogue fragments share state; independent UI/name/menu slots do not.
        key = (loc.get('asset'), loc.get('member')) if loc.get('kind') == 'script' and loc.get('opcode') == 72 else ('slot', row['text_index'])
        stack = stacks.setdefault(key, [])
        for char in value:
            if char in PAIRS:
                if any(opening == char for opening, _ in stack):
                    for _, origin in stack:
                        flag(origin, 'quote_unclosed', '遇到同层新引号前未闭合；须按完整发言复核')
                    stack.clear()
                stack.append((char, row))
            elif char in PAIRS.values():
                if stack and PAIRS[stack[-1][0]] == char:
                    stack.pop()
                else:
                    flag(row, 'quote_unmatched_close', '后引号无匹配或嵌套次序不符')
    for stack in stacks.values():
        for _, origin in stack:
            flag(origin, 'quote_unclosed', '本脚本/独立文字槽结束仍未闭合')
    return findings


def audit(game):
    config = resolve(game, allow_disabled=True)
    path = config['project'] / 'work/cache.json'
    raw = path.read_bytes()
    cache = json.loads(raw.decode('utf-8-sig'))
    findings = []
    for group in cache['files'].values():
        findings.extend(inspect_rows(group['items']))
    report = dict(game=game, cache_sha256=hashlib.sha256(raw).hexdigest(),
                  method='静态脚本顺序候选检查；未还原分支及说话人边界，不等同完整发言验证；不自动修正。',
                  counts=dict(Counter(x['rule'] for x in findings)), findings=findings)
    output = ROOT / 'reports/text-style' / (game + '.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if path.read_bytes() != raw:
        raise RuntimeError('Translation changed during audit: ' + game)
    print(game + ': ' + str(len(findings)) + ' review candidates; ' + str(output))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', default='all')
    parser.add_argument('--strict', action='store_true', help='Exit nonzero if any review candidates exist')
    args = parser.parse_args()
    reports = [audit(game) for game in (read()['games'] if args.game == 'all' else [args.game])]
    if args.strict and any(r['findings'] for r in reports):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
