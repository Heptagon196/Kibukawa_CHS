"""Offline reader for the 20050817 scenario container, not a runtime adapter.

Based on kibu8 CanvasEx.LoadScenario and the original scratch3 assets.
Opcode decoding, click boundaries and Chinese rendering remain unimplemented.
"""
import io
import struct
import zipfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def scenarios(data):
    require(bool(data), 'Empty scenario container')
    cursor = 1
    records = []
    names = set()
    for _ in range(data[0]):
        end = data.index(0, cursor)
        name = data[cursor:end].decode('ascii')
        require(name.endswith('.jar') and '/' not in name and '\\' not in name and name not in names, 'Invalid scenario name')
        names.add(name)
        cursor = end + 1
        offset, length = struct.unpack_from('>HH', data, cursor)
        cursor += 4
        records.append((name, offset, length))
    base = cursor
    result = []
    for name, offset, length in records:
        require(offset == (cursor - base) % 65536, 'Unexpected packed offset')
        require(cursor + length <= len(data), 'Truncated JAR')
        with zipfile.ZipFile(io.BytesIO(data[cursor:cursor + length])) as archive:
            member = name[:-4] + '.bin'
            require(archive.namelist() == [member], 'Unexpected JAR members')
            require(archive.testzip() is None, 'JAR CRC failure')
            raw = archive.read(member)
        require(raw[:2] == b'\xff\xff' and len(raw) >= 17, 'Invalid scenario envelope')
        size = int.from_bytes(raw[2:4], 'little')
        require(size == len(raw) - 4, 'Scenario size mismatch')
        payload = raw[4:]
        require(payload[:8] == b'20050817', 'Unsupported scenario version')
        count = int.from_bytes(payload[11:13], 'little')
        start = 13 + count * 2
        require(start <= len(payload), 'Truncated label table')
        labels = list(struct.unpack_from('<' + 'H' * count, payload, 13))
        script = payload[start:]
        require(all(label <= len(script) for label in labels), 'Label outside script')
        result.append(dict(name=name, offset=cursor, length=length, labels=labels,
                           script_offset=4 + start, raw=raw, script=script))
        cursor += length
    require(cursor == len(data), 'Trailing container data')
    return result
