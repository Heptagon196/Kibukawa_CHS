using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using Kibu1ZhCN;

namespace Kibukawa.Engine.Gmode20050117
{
    /// <summary>
    /// Read-only view of a series schema-1 pack for the 20050117 text model.
    ///
    /// Entries are keyed on the canonical script name plus the script-relative
    /// offset of the BUNSYOU command that opens a display line, matching the
    /// repository pack convention. A line is a run of BUNSYOU fragments, so the
    /// entry also carries how many fragments it spans: the runtime stocks the whole
    /// translated line with the first fragment and blanks the continuations, which
    /// keeps the translation unit linguistic instead of fragment-shaped.
    /// </summary>
    public sealed class RuntimePack
    {
        public sealed class LayoutLine
        {
            public string Text;
            public int NameShift;
            public int[] X, RowDelta;
        }
        private readonly Dictionary<string, LayoutLine> layouts = new Dictionary<string, LayoutLine>();

        public bool TryLayout(string script, int offset, out LayoutLine layout)
        { return layouts.TryGetValue(Slot(script, offset), out layout); }

        private static string LayoutString(BinaryReader reader)
        {
            int count = reader.ReadInt32();
            if (count < 0 || count > 4096) throw new InvalidDataException("Invalid layout string");
            byte[] bytes = reader.ReadBytes(count);
            if (bytes.Length != count) throw new EndOfStreamException();
            return System.Text.Encoding.UTF8.GetString(bytes);
        }

        private void LoadLayout(string packPath)
        {
            string path = Path.Combine(Path.GetDirectoryName(packPath), "dialogue-layout.bin");
            if (!File.Exists(path)) return; // Older packs retain their original layout.
            using (var reader = new BinaryReader(File.OpenRead(path)))
            {
                if (System.Text.Encoding.ASCII.GetString(reader.ReadBytes(5)) != "K9LF\u0001")
                    throw new InvalidDataException("Invalid dialogue layout version");
                byte[] expected = reader.ReadBytes(32);
                using (var sha = System.Security.Cryptography.SHA256.Create())
                using (var stream = File.OpenRead(packPath))
                {
                    byte[] actual = sha.ComputeHash(stream);
                    if (expected.Length != actual.Length) throw new InvalidDataException("Truncated layout hash");
                    for (int i = 0; i < actual.Length; i++)
                        if (actual[i] != expected[i]) throw new InvalidDataException("Stale dialogue layout");
                }
                int count = reader.ReadInt32();
                if (count < 0 || count > 100000) throw new InvalidDataException("Invalid layout count");
                for (int i = 0; i < count; i++)
                {
                    string script = LayoutString(reader);
                    int offset = reader.ReadInt32();
                    string text = LayoutString(reader);
                    int shift = reader.ReadInt32(), length = reader.ReadInt32();
                    string target; int fragments;
                    if (length != text.Length || length > 32 || shift < 0 || shift > 7 ||
                        !TryLine(script, offset, out target, out fragments) ||
                        target.Replace(RunSeparator.ToString(), "") != text)
                        throw new InvalidDataException("Layout does not match translation");
                    var line = new LayoutLine { Text = text, NameShift = shift,
                        X = new int[length], RowDelta = new int[length] };
                    for (int j = 0; j < length; j++)
                    {
                        line.X[j] = reader.ReadInt16(); line.RowDelta[j] = reader.ReadInt16();
                        if (line.X[j] < 1 || line.X[j] > 232 || Math.Abs(line.RowDelta[j]) > 7)
                            throw new InvalidDataException("Layout coordinate outside viewport");
                    }
                    layouts.Add(Slot(script, offset), line);
                }
                if (reader.BaseStream.Position != reader.BaseStream.Length)
                    throw new InvalidDataException("Trailing dialogue layout data");
            }
        }
        private readonly Dictionary<string, string> lines = new Dictionary<string, string>(StringComparer.Ordinal);
        private readonly Dictionary<string, int> fragments = new Dictionary<string, int>(StringComparer.Ordinal);
        private readonly Dictionary<string, string> ui = new Dictionary<string, string>(StringComparer.Ordinal);
        private readonly Dictionary<string, string> localization = new Dictionary<string, string>(StringComparer.Ordinal);
        private readonly Dictionary<string, string> nameSourceToTarget = new Dictionary<string, string>(StringComparer.Ordinal);
        private readonly Dictionary<string, string> nameTargetToSource = new Dictionary<string, string>(StringComparer.Ordinal);

        // vm.py: NAMAE_SETTEI. Filtering on the opcode keeps repeated dialogue and
        // choice literals out of the save-data mapping even when their text matches.
        private const int NameOpcode = 17;

        public readonly string GameAssemblySha256;
        public readonly string ScratchpadSha256;

        private RuntimePack(string assembly, string scratchpad)
        {
            GameAssemblySha256 = assembly;
            ScratchpadSha256 = scratchpad;
        }

        public int LineCount { get { return lines.Count; } }
        public int UiCount { get { return ui.Count; } }
        public int LocalizationCount { get { return localization.Count; } }

        /// <summary>Every source literal the pack can replace in native UI arrays.</summary>
        public IEnumerable<KeyValuePair<string, string>> UiEntries { get { return ui; } }

        /// <summary>Separates colour runs inside a packed line.
        ///
        /// A line the script recolours part-way through arrives as one string per colour,
        /// joined by this character, so the runtime can stock each run in the fragment
        /// where that colour takes effect. The pack format itself is unchanged: the shared
        /// reader hands ``target`` over verbatim. No translation can contain it, so a line
        /// without it is simply a line of one colour. Must equal
        /// ``runtime_pack.RUN_SEPARATOR`` on the build side.
        /// </summary>
        public const char RunSeparator = '\u0001';

        private static string Slot(string script, int offset)
        {
            return (script ?? string.Empty) + "\0" + offset.ToString(CultureInfo.InvariantCulture);
        }

        public static RuntimePack Load(string path)
        {
            TranslationPack data = TranslationPackReader.Load(path);
            RuntimePack result = new RuntimePack(data.gameAssemblySha256, data.scratchpadSha256);
            foreach (ScriptEntry entry in data.scripts)
            {
                if (entry.source == null || entry.target == null) continue;
                string key = Slot(entry.script, entry.instruction);
                string existing;
                if (result.lines.TryGetValue(key, out existing))
                {
                    // The builder already refuses conflicting targets; this is the last
                    // line of defence against a hand-edited pack.
                    if (!string.Equals(existing, entry.target, StringComparison.Ordinal))
                        throw new InvalidDataException("Conflicting translation at " + entry.script + ":" + entry.instruction);
                    continue;
                }
                result.lines.Add(key, entry.target);
                result.fragments[key] = entry.slot > 0 ? entry.slot : 1;
                if (entry.opcode == NameOpcode)
                {
                    AddStrict(result.nameSourceToTarget, entry.source, entry.target, "name source");
                    AddStrict(result.nameTargetToSource, entry.target, entry.source, "name target");
                }
            }
            foreach (StringEntry entry in data.ui)
            {
                if (entry.source == null || entry.target == null) continue;
                result.ui[entry.source] = entry.target;
            }
            foreach (StringEntry entry in data.localization)
            {
                if (entry.key == null || entry.target == null) continue;
                result.localization[entry.key] = entry.target;
            }
            result.LoadLayout(path);
            return result;
        }

        private static void AddStrict(Dictionary<string, string> map, string key, string value, string label)
        {
            string previous;
            if (map.TryGetValue(key, out previous))
            {
                if (!string.Equals(previous, value, StringComparison.Ordinal))
                    throw new InvalidDataException("Ambiguous " + label + ": " + key);
                return;
            }
            map.Add(key, value);
        }

        /// <summary>Return the original CP932 name for the native save serializer.</summary>
        public string NameForSave(string displayed)
        {
            if (displayed == null) return null;
            string source;
            return nameTargetToSource.TryGetValue(displayed, out source) ? source : displayed;
        }

        /// <summary>
        /// Restore an exact Japanese name loaded from the native save to Chinese.
        /// </summary>
        public string NameAfterLoad(string stored)
        {
            if (stored == null) return null;
            string target;
            if (nameSourceToTarget.TryGetValue(stored, out target)) return target;
            if (nameTargetToSource.ContainsKey(stored)) return stored;

            return stored;
        }

        /// <summary>Translate a Steezy.Localize key, or return false to keep the game's text.</summary>
        public bool TryLocalization(string key, out string target)
        {
            if (key == null) { target = null; return false; }
            return localization.TryGetValue(key, out target);
        }

        /// <summary>Translate the display line that starts at ``script``:``offset``.
        ///
        /// ``fragments`` is how many native BUNSYOU commands the line spans, so the
        /// runtime can blank the continuations instead of repeating the text.
        /// Returns false to keep the original fragment.
        /// </summary>
        public bool TryLine(string script, int offset, out string target, out int fragments)
        {
            fragments = 1;
            if (!lines.TryGetValue(Slot(script, offset), out target)) return false;
            this.fragments.TryGetValue(Slot(script, offset), out fragments);
            if (fragments < 1) fragments = 1;
            return true;
        }

        public bool TryUi(string source, out string target)
        {
            if (source == null) { target = null; return false; }
            return ui.TryGetValue(source, out target);
        }
    }
}
