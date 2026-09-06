using System;
using System.Collections.Generic;

namespace Kibu1ZhCN
{
    [Serializable] public sealed class TranslationPack
    {
        public int schema;
        public string gameAssemblySha256;
        public string scratchpadSha256;
        public ScriptEntry[] scripts;
        public StringEntry[] ui;
        public StringEntry[] localization;
        public LiteralEntry[] literals;
    }
    [Serializable] public sealed class ScriptEntry
    {
        public int index, instruction, slot, opcode;
        public string script, source, target;
    }
    [Serializable] public sealed class StringEntry
    {
        public string source, target, key;
    }
    [Serializable] public sealed class LiteralEntry
    {
        public int index, token, instruction;
        public string source, target, method;
    }

    // Pure managed core, shared by the real plugin and offline replay tests.
    public sealed class TranslationCatalog
    {
        private readonly Dictionary<string, Dictionary<int, List<ScriptEntry>>> scripts =
            new Dictionary<string, Dictionary<int, List<ScriptEntry>>>(StringComparer.Ordinal);
        private readonly Dictionary<string, string> ui = new Dictionary<string, string>(StringComparer.Ordinal);
        private readonly Dictionary<string, string> localization = new Dictionary<string, string>(StringComparer.Ordinal);
        public readonly Dictionary<int, Dictionary<int, LiteralEntry>> Literals = new Dictionary<int, Dictionary<int, LiteralEntry>>();
        public readonly TranslationPack Pack;
        public int SourceMismatches { get; private set; }
        public int ReplacedScriptSlots { get; private set; }

        public TranslationCatalog(TranslationPack pack)
        {
            if (pack == null || pack.schema != 1) throw new ArgumentException("Unsupported translation schema");
            Pack = pack;
            foreach (ScriptEntry e in pack.scripts ?? new ScriptEntry[0])
            {
                // Empty strings intentionally suppress reading-only name fragments.
                // Null remains invalid: the game uses null as a control operation.
                if (e.slot < 0 || e.slot >= 20 || e.target == null || e.target.Length > 20 || e.target.IndexOf('\0') >= 0)
                    throw new ArgumentException("Invalid script translation " + e.index);
                Dictionary<int, List<ScriptEntry>> commands;
                if (!scripts.TryGetValue(e.script, out commands)) scripts.Add(e.script, commands = new Dictionary<int, List<ScriptEntry>>());
                List<ScriptEntry> slots;
                if (!commands.TryGetValue(e.instruction, out slots)) commands.Add(e.instruction, slots = new List<ScriptEntry>());
                if (slots.Exists(x => x.slot == e.slot)) throw new ArgumentException("Duplicate script slot " + e.index);
                slots.Add(e);
            }
            foreach (StringEntry e in pack.ui ?? new StringEntry[0]) Add(ui, e.source, e.target);
            foreach (StringEntry e in pack.localization ?? new StringEntry[0]) Add(localization, e.key, e.target);
            foreach (LiteralEntry e in pack.literals ?? new LiteralEntry[0])
            {
                Dictionary<int, LiteralEntry> method;
                if (!Literals.TryGetValue(e.token, out method)) Literals.Add(e.token, method = new Dictionary<int, LiteralEntry>());
                method.Add(e.instruction, e);
            }
        }
        private static void Add(Dictionary<string, string> dict, string key, string value)
        {
            string previous;
            if (dict.TryGetValue(key, out previous) && previous != value) throw new ArgumentException("Ambiguous UI text: " + key);
            dict[key] = value;
        }
        public int ApplyScript(string script, int instruction, int opcode, string[] strings)
        {
            Dictionary<int, List<ScriptEntry>> commands;
            List<ScriptEntry> slots;
            if (!scripts.TryGetValue(script, out commands) || !commands.TryGetValue(instruction, out slots)) return 0;
            int count = 0;
            foreach (ScriptEntry entry in slots)
            {
                if (entry.opcode != opcode || entry.slot >= strings.Length || strings[entry.slot] != entry.source)
                {
                    SourceMismatches++;
                    continue;
                }
                strings[entry.slot] = entry.target;
                count++;
            }
            ReplacedScriptSlots += count;
            return count;
        }
        public string TranslateUI(string source)
        {
            string target;
            return source != null && ui.TryGetValue(source, out target) ? target : source;
        }
        public bool TryLocalize(string key, out string target) { return localization.TryGetValue(key, out target); }
        public static string ScriptName(int scenario, int selected)
        {
            return selected > 0 ? "subscn_" + selected : "scn" + scenario;
        }
    }
}
