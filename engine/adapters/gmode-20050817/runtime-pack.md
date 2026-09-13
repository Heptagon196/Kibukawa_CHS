# 20050817 runtime display pack

`runtime_pack.py --game games/08-kibu8 --output games/08-kibu8/build/runtime.k8rt --report games/08-kibu8/reports/runtime-pack.json`

Compile from authoritative `work/dialogue-tagged.json`, verifying every source against original parsed BIN. No BIN or translation file is modified. Scripts are keyed by SHA256 of the **script body**, excluding the BIN envelope and label table. Identical bodies must have identical translations; otherwise compilation fails. Identical support scenes deduplicate from 59 to 53 scripts.

All integers below are unsigned 32-bit little endian except `opcode` and array elements (one byte). Strings are `u32 UTF8 byte length` followed by strict UTF8 bytes. No BOM or terminator.

```
8 bytes ASCII K8RT0001
u32 script count
for each script:
    32 raw SHA256 bytes
    u32 display count
    for each display:
        u32 original opcode offset, u8 opcode, u32 row count
        for each row:
            string original source text
            string translated text
            u32 slot count (= translated UTF16/BMP character count)
            slot_count bytes palette indices
            slot_count bytes control values
            string original ruby metadata JSON
    u32 visible string argument count
    for each string argument:
        u32 original argument offset, u8 opcode
        string exact decoded original source
        string translated target
```

All offsets are script-relative. String argument offset points at the first string byte, before StringRead, not the opcode. Records include opcode 5/8 for runtime StringRead replacement, and opcode 17/80 for display-only mapping: names/bookmarks must retain original values for legacy SJIS persistence. INFO source rows support display-only lookup after loading persisted text. `RuntimePack.cs` supplies a standalone reader without Unity dependencies under namespace `Kibukawa8.Runtime`; `RuntimePack.Load(path).Scripts` uses lowercase hexadecimal SHA256 strings.

Target ASCII `!` through `~` becomes its fullwidth equivalent, and ASCII space becomes U+3000. This conversion happens only in the pack. Each translated character occupies one display slot. Each `<ctrl=XX/>` attaches after its preceding glyph; a translated empty span/row with no available glyph gets a U+3000 slot to retain its event. Colors remain attached to translated spans. Rows, event order, and all tagged color transitions are checked against the originals. Runtime fitting is responsible for long rows, including in-line translation notes. Compiler does not remove notes.

Ruby policy is explicit: the 1,910 original Japanese atlas ruby groups (1,751 rows) are **disabled for Chinese display**, with ruby indices initialized to -1 and group counts to zero by the runtime. Each row's JSON preserves all original indices, original base cells, and full group byte arrays/offsets. Nothing is decoded as SJIS ruby; the atlas uses nibble coordinates and only the first `cells_count` of the stored `2*cells_count` bytes. Metadata permits future readings support without losing evidence.

Original Script, Pos, label table, and saved positions remain unchanged. In particular SEEBU computes `SavePos=Pos+56`, which makes BIN relocation inappropriate without changing save compatibility. This pack intentionally changes display buffers only.

Validation: Python unit tests cover color/control attachment, empty controlled rows, tag mismatch, BMP/fullwidth conversion, full-corpus source validation and deterministic serialization. A PowerShell Add-Type compile and C# readback verified 53 script records, 14,790 display records and 1,588 string records after deduplication. Before deduplication coverage is 16,636 units (14,942 displays, 1,694 strings). Real game rendering remains for user verification.
