"""Immutable draw positions across soft SLASH rows; VM storage remains untouched."""
import hashlib
import json
import struct
import unicodedata

from vm import parse_bin

CLOSE = set('，。！？；：、）》」』】〕〉”’…—％%!?.,;:)]}')
OPEN = set('（《「『【〔〈“‘([{')


def width(text):
    from build_pack import dialogue_width
    return dialogue_width(text)


def latin_alnum(char):
    """ASCII and full-width Latin letters/digits belong to one unbreakable word."""
    if not char or not char.isalnum():
        return False
    return char.isascii() or 'LATIN' in unicodedata.name(char, '')


COMMON_WORDS = set("本期 嘉宾 侦探 侦探事务所 侦探助手 助手 小姐 先生 女士 警官 老师 社长 事务所 这么 那么 什么 为什么 怎么 因为 所以 但是 不过 已经 现在 时候 事情 知道 觉得 自己 一个 一个人 大家 今天 昨天 明天 这里 那里 这个 那个 这样 那样 可能 应该 没有 不是 还是 如果 其实 当然 一起 一直 突然 发现 调查 案件 现场 犯人 被害人 嫌疑人 证据 不在场证明 电话 照片 关系 朋友 家人 工作 公司 房间 门口 然后 最后 之前 之后 当时 后来 谢谢 对不起 没关系 没想到 看起来 听起来 总而言之 请多关照 另有住处 他在工厂附近".split())
TITLES = ('小姐', '先生', '女士', '警官', '老师', '社长')


def protected_words():
    from pathlib import Path
    import pipeline as p
    words = set(COMMON_WORDS)
    for file in (p.WORK / 'work/glossary.locked.json', p.SERIES / 'series/glossary.json'):
        def collect(value):
            if isinstance(value, dict):
                rendered = value.get('render')
                if isinstance(rendered, str) and len(rendered) > 1:
                    words.add(rendered)
                    if 'person' in value.get('category', ''):
                        words.update(rendered + title for title in TITLES)
                        words.add(rendered + '的名字')
                for child in value.values():
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)
        collect(json.loads(file.read_text(encoding='utf-8')))
    return words


_tokenizer = None


def segment(text, words):
    global _tokenizer
    if _tokenizer is None:
        import sys
        import pipeline as p
        # Build-time dependency only; never copied into the game plugin.
        sys.path.insert(0, str(p.WORK / 'bepinex/build/python-deps'))
        import jieba
        if jieba.__version__ != '0.42.1':
            raise RuntimeError('Install the pinned layout-requirements.txt dependency')
        _tokenizer = jieba.Tokenizer()
        _tokenizer.tmp_dir = str(p.WORK / 'bepinex/build')
        _tokenizer.initialize()
        for word in sorted(words):
            _tokenizer.add_word(word, freq=1000000)
    tokens = list(_tokenizer.cut(text, HMM=False))
    if ''.join(tokens) != text:
        raise ValueError('Tokenizer changed the dialogue')
    return tokens


def positions(text, block_width=204, max_rows=None, words=None, source_breaks=()):
    # Plan the whole utterance, rather than greedily filling each row. Names,
    # titles and glossary terms form indivisible spans whenever the box permits.
    words = protected_words() if words is None else words
    source_breaks = set(source_breaks)
    # A leading ellipsis or opening quote starts a new authored phrase, and a
    # completed sentence must not be merged into the next one merely to balance
    # row widths.  Keep those explicit row boundaries during reflow.
    forced_source_breaks = {
        boundary for boundary in source_breaks
        if ((boundary < len(text) and text[boundary] in '…“‘')
            or (boundary > 0 and text[boundary - 1] in '。！？!?'))
    }
    blocked, preferred = {}, {0, len(text)}
    cursor = 0
    for token in segment(text, words):
        for boundary in range(cursor + 1, cursor + len(token)):
            blocked[boundary] = 10
        cursor += len(token)
        preferred.add(cursor)
    for word in words:
        if word not in text or width(word) > block_width:
            continue
        start = text.find(word)
        while start >= 0:
            for boundary in range(start + 1, start + len(word)):
                blocked[boundary] = blocked.get(boundary, 0) + 1
            preferred.update((start, start + len(word)))
            start = text.find(word, start + 1)
    for i in range(1, len(text)):
        if latin_alnum(text[i - 1]) and latin_alnum(text[i]):
            blocked[i] = blocked.get(i, 0) + 1
        # Keep contractions such as DOESN'T / DOESN’T intact. The apostrophe has
        # punctuation category, so tokenizers otherwise expose a legal break before
        # the final T even though it is part of the same English word.
        if (text[i] in "'’" and i + 1 < len(text)
                and latin_alnum(text[i - 1]) and latin_alnum(text[i + 1])):
            blocked[i] = blocked.get(i, 0) + 10
            blocked[i + 1] = blocked.get(i + 1, 0) + 10
        # Python recognises both ASCII and full-width decimal digits here.
        # Jieba may emit full-width digits one by one, but a number must remain
        # an indivisible span regardless of which numeral width the script uses.
        if text[i - 1].isdigit() and text[i].isdigit():
            blocked[i] = blocked.get(i, 0) + 10
    max_rows = max_rows or len(text)
    from functools import lru_cache
    @lru_cache(None)
    def solve(start, remaining):
        if start == len(text):
            return (0, [])
        if not remaining:
            return None
        best = None
        for end in range(start + 1, len(text) + 1):
            used = width(text[start:end])
            if used > block_width:
                break
            if any(start < boundary < end for boundary in forced_source_breaks):
                continue
            if end < len(text) and (
                    (text[end] in CLOSE and end not in forced_source_breaks)
                    or text[end - 1] in OPEN):
                continue
            tail = solve(end, remaining - 1)
            if tail is None:
                continue
            # A protected split is a last resort when the original vertical box
            # cannot fit otherwise; no words or control boundaries are deleted.
            cost = 2000 + ((block_width - used) / 17) ** 2
            if end < len(text):
                cost += 100000 * blocked[end] if end in blocked else (0 if end in preferred or text[end - 1] in CLOSE else 80)
            if end in source_breaks and end not in blocked:
                cost -= 2
            if end == len(text) and start and len(text[start:end].strip('，。！？…')) < 2:
                cost += 300
            candidate = (cost + tail[0], [text[start:end]] + tail[1])
            if best is None or candidate[0] <= best[0]:
                best = candidate
        return best
    solution = solve(0, max_rows)
    if solution is None:
        return [], []
    rows = solution[1]
    coordinates = []
    for y, row in enumerate(rows):
        for i, char in enumerate(row):
            x = width(row[:i + 1]) - width(char)
            coordinates.append(((240 - block_width) // 2 + x, y))
    return rows, coordinates


def build(scripts, units, encoded, output):
    targets = {(u['script'], u['offset']): u.get('target', '')
               for u in units if u.get('kind', 'line') == 'line'}
    budgets = {(u['script'], u['offset']): u.get('limit', 0) for u in units}
    words = protected_words()
    records, examples = [], []
    for script, raw in scripts.items():
        parsed = parse_bin(raw)
        labels = set(parsed['labels'])
        group, current = [], None

        def flush():
            if len(group) < 2:
                return
            texts = [targets.get((script, offset), '') for offset in group]
            if not all(t.strip() for t in texts):
                return
            block_width = min(238, min(budgets[(script, offset)] * 17 for offset in group))
            if block_width <= 0:
                return
            source_breaks = {sum(map(len, texts[:i])) for i in range(1, len(texts))}
            rows, coords = positions(''.join(texts), block_width, len(group), words, source_breaks)
            if not rows or len(rows) > len(group):
                return  # Preserve the authored vertical reservation.
            index = 0
            shift = len(group) - len(rows)
            for native_row, (offset, text) in enumerate(zip(group, texts)):
                points = [(x, y + shift - native_row) for x, y in coords[index:index + len(text)]]
                records.append((script, offset, text, shift if native_row == 0 else 0, points))
                index += len(text)
            examples.append(dict(script=script, offsets=list(group), before=texts, after=rows, tokens=segment(''.join(texts), words), block_width=block_width, margin=(240 - block_width) // 2))

        for cmd in parsed['commands']:
            if cmd['offset'] in labels:
                flush()
                group = []
            name = cmd['name']
            if name == 'BUNSYOU':
                if current is None:
                    current = cmd['offset']
                    if not targets.get((script, current), '').strip():
                        flush()
                        group = []
                continue
            if name == 'BUNSYOU_SLASH':
                if current is not None:
                    group.append(current)
                else:
                    flush()
                    group = []  # Deliberate empty line.
                current = None
            elif name not in ('BUNSYOU_IRO', 'BUNSYOU_RUBI', 'BUNSYOU_F7',
                               'BUNSYOU_FA', 'BUNSYOU_SPEED', 'BUNSYOU_FADE'):
                if current is not None:
                    group.append(current)
                flush()
                group, current = [], None
        if current is not None:
            group.append(current)
        flush()

    data = bytearray(b'K9LF\x01' + hashlib.sha256(encoded).digest())
    data.extend(struct.pack('<i', len(records)))
    def string(value):
        raw = value.encode('utf-8')
        data.extend(struct.pack('<i', len(raw)))
        data.extend(raw)
    for script, offset, text, shift, points in records:
        string(script)
        data.extend(struct.pack('<i', offset))
        string(text)
        data.extend(struct.pack('<ii', shift, len(points)))
        for x, y in points:
            data.extend(struct.pack('<hh', x, y))
    (output / 'dialogue-layout.bin').write_bytes(data)
    (output / 'dialogue-layout.json').write_text(json.dumps(
        dict(groups=len(examples), native_rows=len(records), examples=examples),
        ensure_ascii=False, indent=1), encoding='utf-8')
    print('LAYOUT READY: %d soft-break groups / %d native rows' % (len(examples), len(records)))
