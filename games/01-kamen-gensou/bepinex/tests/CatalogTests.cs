using System;
using System.Collections.Generic;
using System.IO;
using System.Web.Script.Serialization;
using Kibu1ZhCN;

public sealed class Replay
{
    public string script;
    public int instruction, opcode, nextCursor;
    public string[] strings, expected;
}
public sealed class ReplayData { public Replay[] commands; }
public static class CatalogTests
{
    public static void Main(string[] args)
    {
        try { Run(args); }
        catch (Exception error) { Console.Error.WriteLine(error.GetType().FullName + ": " + error.Message); Environment.Exit(1); }
    }
    private static void Run(string[] args)
    {
        var json = new JavaScriptSerializer { MaxJsonLength = 50000000 };
        var pack = TranslationPackReader.Load(args[0]);
        var reference = json.Deserialize<TranslationPack>(File.ReadAllText(args[2]));
        CompareFields(pack, reference, "pack");
        var replay = json.Deserialize<ReplayData>(File.ReadAllText(args[1]));
        var catalog = new TranslationCatalog(pack);
        int translated = 0, commands = 0;
        foreach (var r in replay.commands)
        {
            string[] actual = (string[])r.strings.Clone();
            translated += catalog.ApplyScript(r.script, r.instruction, r.opcode, actual);
            for (int i=0; i<actual.Length; i++) Assert(actual[i] == r.expected[i], "Wrong text at " + r.script + ":" + r.instruction + ":" + i);
            commands++;
        }
        Assert(translated == pack.scripts.Length, "Script coverage mismatch");
        Assert(catalog.SourceMismatches == 0, "Unexpected source mismatch");
        var first = pack.scripts[0];
        var mismatched = new string[20]; mismatched[first.slot] = "Wrong version";
        Assert(catalog.ApplyScript(first.script, first.instruction, first.opcode, mismatched) == 0, "Mismatched source overwritten");
        Assert(mismatched[first.slot] == "Wrong version", "Mismatch fallback failed");
        Assert(catalog.TranslateUI("unknown text") == "unknown text", "Unknown UI altered");
        foreach (var e in pack.ui) Assert(catalog.TranslateUI(e.source) == e.target, "UI map mismatch");
        foreach (var e in pack.localization) { string target; Assert(catalog.TryLocalize(e.key, out target) && target == e.target, "Localization mismatch"); }
        Assert(TranslationCatalog.ScriptName(9, 0) == "scn9", "Main scenario routing failed");
        Assert(TranslationCatalog.ScriptName(9, 2) == "subscn_2", "Subscenario routing failed");
        // Duplicate text at different command addresses must retain distinct contextual translations.
        var a = new ScriptEntry { index=1, script="test", instruction=1, slot=0, opcode=72, source="same", target="甲" };
        var b = new ScriptEntry { index=2, script="test", instruction=2, slot=0, opcode=72, source="same", target="乙" };
        var isolated = new TranslationCatalog(new TranslationPack { schema=1, scripts=new[] {a,b} });
        var one = new[] {"same"}; var two = new[] {"same"};
        isolated.ApplyScript("test",1,72,one); isolated.ApplyScript("test",2,72,two);
        Assert(one[0]=="甲" && two[0]=="乙", "Context collapsed into a global string replacement");
        int emptyReadings = 0;
        foreach (var entry in pack.scripts)
        {
            if (entry.target != "") continue;
            var values = new string[20]; values[entry.slot] = entry.source;
            Assert(catalog.ApplyScript(entry.script, entry.instruction, entry.opcode, values) == 1, "Empty name reading was not applied");
            Assert(values[entry.slot] == "" && values[entry.slot] != null, "Empty name reading became a control marker");
            emptyReadings++;
        }
        Assert(emptyReadings == 9, "Name-only reading fragment coverage changed");
        Console.WriteLine("PASS: " + translated + " script slots / " + commands + " commands; UI and localization; mismatch fallback; contextual duplicates.");
    }
    private static void Assert(bool success, string message) { if (!success) throw new Exception(message); }
    private static void CompareFields(object actual, object expected, string path)
    {
        if (actual == null || expected == null) { Assert(actual == expected, "Null field mismatch: " + path); return; }
        Type type = actual.GetType();
        Assert(type == expected.GetType(), "Type mismatch: " + path);
        if (type == typeof(string) || type.IsPrimitive) { Assert(actual.Equals(expected), "Value mismatch: " + path); return; }
        if (type.IsArray)
        {
            Array left = (Array)actual, right = (Array)expected;
            Assert(left.Length == right.Length, "Array count mismatch: " + path);
            for (int i=0; i<left.Length; i++) CompareFields(left.GetValue(i), right.GetValue(i), path + "[" + i + "]");
            return;
        }
        foreach (var field in type.GetFields()) CompareFields(field.GetValue(actual), field.GetValue(expected), path + "." + field.Name);
    }
}
