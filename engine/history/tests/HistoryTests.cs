using System;
using System.Collections;
using KibukawaHistory;
class HistoryTests
{
    static void Check(bool ok, string message) { if (!ok) throw new Exception(message); }
    static int steps;
    static bool disposed;
    static IEnumerator Story()
    {
        try { steps++; yield return Child(); steps++; }
        finally { disposed = true; }
    }
    static IEnumerator Child() { steps++; yield return null; steps++; }
    static int Main()
    {
        var log = new HistoryBuffer(2);
        log.Append("第一"); log.Append("句"); Check(log.Entries[0] == "第一句", "Fragments must join");
        log.Break(); log.Break(); log.Append("第二句"); log.Break(); log.Append("第三句");
        Check(log.Entries.Count == 2 && log.Entries[0] == "第二句", "Evict only oldest entry");
        log.Break(); log.Append("第三句"); Check(log.Entries[0] == log.Entries[1], "Repeated dialogue is legitimate history");
        log.Append(new string('长', 6000)); Check(log.Entries.Count == 2 && log.Entries[1].Length <= 2000, "Bound long entries");
        Check(log.Colors.Count == log.Entries.Count && log.Colors[1].Count == log.Entries[1].Length, "Colors evict and split with text");
        var colored = new HistoryBuffer(2);
        int[] rgb = {0xFF0080,0xFFFFFF,0xFFFFFF};
        colored.Append("甲乙丙", rgb); rgb[0] = 0;
        Check(colored.Colors[0][0] == 0xFF0080, "Snapshot RGB rather than retaining mutable palette");
        colored.Append("丁", new[] {0x00FF00});
        var layout = new ColoredHistoryLayout(colored.Entries[0], colored.Colors[0], 20, 12, delegate(char c) { return 10; });
        Check(layout.Runs.Count == 4 && layout.Runs[0].Color == 0xFF0080 && layout.Runs[3].Color == 0x00FF00, "Mixed colors preserved");
        Check(layout.Runs[1].X == 10 && layout.Runs[2].X == 0 && layout.Runs[2].Y == 12, "Color runs wrap at actual line boundary");
        colored.Break(); colored.Append("<color=red>");
        Check(colored.Entries[1] == "<color=red>", "Literal text remains literal, not rich markup");
        Console.WriteLine("PASS RGB snapshots, mixed-color fragments, colored wrapping, literal markup and color eviction");
        bool paused = true;
        IEnumerator flow = PausedEnumerator.Wrap(Story(), delegate { return paused; });
        flow.MoveNext(); Check(steps == 0, "No story advance when paused");
        paused = false; flow.MoveNext(); Check(steps == 1, "Resume story exactly once");
        IEnumerator child = (IEnumerator)flow.Current;
        paused = true; child.MoveNext(); Check(steps == 1, "Nested story must pause");
        paused = false; child.MoveNext(); Check(steps == 2, "Resume nested story");
        Check(!child.MoveNext() && steps == 3, "Complete child once");
        Check(!flow.MoveNext() && steps == 4 && disposed, "Complete and dispose original");
        Console.WriteLine("PASS history grouping, eviction, repeats, bounds, nested pause/resume and disposal");
        return 0;
    }
}
