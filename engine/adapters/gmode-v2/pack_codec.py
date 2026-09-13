"""Schema-1 translation pack codec, shared by every version adapter.

The KBZH byte layout is fixed by ``engine/core/TranslationPackReader.cs``: the
C# reader is the authority, and this module is its Python counterpart. It is
version neutral — it only writes the structure, while each adapter decides which
slots exist and how they are keyed.

``gmode-20050817.runtime_pack`` re-exports :func:`encode_translation_pack` so
existing callers keep importing it from the adapter they already use.
"""
import struct


def encode_translation_pack(pack):
    """Same KBZH schema-1 byte layout as the shared TranslationPackReader."""
    if pack['schema'] != 1 or not pack['scripts'] or not pack['ui']:
        raise ValueError('Incomplete or unsupported translation pack')
    data = bytearray(b'KBZH')

    def integer(value):
        data.extend(struct.pack('<i', value))

    def text(value):
        raw = value.encode('utf-8') if value is not None else None
        integer(len(raw) if raw is not None else -1)
        if raw is not None:
            data.extend(raw)

    integer(pack['schema'])
    text(pack['gameAssemblySha256'])
    text(pack['scratchpadSha256'])
    integer(len(pack['scripts']))
    for entry in pack['scripts']:
        for key in ('index', 'instruction', 'slot', 'opcode'):
            integer(entry[key])
        for key in ('script', 'source', 'target'):
            text(entry[key])
    for group in ('ui', 'localization'):
        integer(len(pack[group]))
        for entry in pack[group]:
            for key in ('source', 'target', 'key'):
                text(entry.get(key))
    integer(len(pack['literals']))
    for entry in pack['literals']:
        for key in ('index', 'token', 'instruction'):
            integer(entry[key])
        for key in ('source', 'target', 'method'):
            text(entry[key])
    return bytes(data)


def make_script_pack(scripts, assembly_hash, scratch_hash, ui, localization=None, literals=None):
    """Assemble the pack dict the encoder and the C# reader both expect.

    ``scripts`` is an ordered list of ``dict(script=, instruction=, slot=, opcode=,
    source=, target=)`` without ``index``; it is filled in here and duplicate
    slots are rejected so a mis-built pack fails at build time, not in game.
    """
    pack = dict(schema=1, gameAssemblySha256=assembly_hash, scratchpadSha256=scratch_hash,
                scripts=[], ui=list(ui), localization=list(localization or []),
                literals=list(literals or []))
    seen = set()
    for entry in scripts:
        # Script text is not a slot identity: ordinary prose, blank spacer lines and
        # menu labels can legitimately repeat within one scenario.  The runtime pack
        # addresses an entry by its instruction and slot, matching TranslationCatalog
        # and the schema-1 reader.
        identity = (entry['script'], entry['instruction'], entry.get('slot', 0))
        if identity in seen:
            raise ValueError('Duplicate translation slot: ' + repr(identity))
        seen.add(identity)
        pack['scripts'].append(dict(index=len(pack['scripts']), instruction=entry['instruction'],
                                    slot=entry.get('slot', 0), opcode=entry.get('opcode', 0),
                                    script=entry['script'], source=entry['source'],
                                    target=entry['target']))
    if not pack['scripts'] or not pack['ui']:
        raise ValueError('Translation pack requires scripts and UI entries')
    return pack
