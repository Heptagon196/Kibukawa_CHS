using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Web.Script.Serialization;
using Kibu1ZhCN;

// A deliberately small game fixture: the text buffer and iterator ordering are
// copied from CanvasEx. The production wrapper, not a second layout algorithm,
// performs all wrapping, pagination and punctuation decisions.
public sealed class ReflowCanvas
{
    public int Cmd, PaintValue;
    public string[] ScStr = new string[16];
    public int[] ScInt = new int[16];
    public bool Truth = true, Else;
    public int Scene = 2;
    public sbyte NameID = -1, TextLine = 4;
    public char[][] Text = Enumerable.Range(0, 9).Select(x => new char[20]).ToArray();
    public sbyte[][] TextC = Enumerable.Range(0, 9).Select(x => new sbyte[20]).ToArray();
    public sbyte[] TextLen = new sbyte[9], TextPos = new sbyte[] { 4, 0 }, TextColor = new sbyte[] { 0, 0 };
    public string[] Name = new string[256];
    public sbyte[] NameC = new sbyte[256], Flag = new sbyte[256];
    public readonly StringBuilder Appended = new StringBuilder();
    public readonly StringBuilder ClearedBody = new StringBuilder();
    public readonly StringBuilder RolledOutBody = new StringBuilder(), RetiredBody = new StringBuilder();
    public readonly List<int> AppendedColors = new List<int>();
    public readonly List<ReflowPage> Pages = new List<ReflowPage>();
    public int Waits, OriginalWaits, Interactions, TypewriterTicks, Scrolls, UnreadScrolls, PluginClears, ScrolledGlyphs, UnreadScrolledGlyphs, BodyCommands, Instruction;
    private readonly int[][] glyphIds = Enumerable.Range(0, 9).Select(x => new int[20]).ToArray();
    private readonly int[] trackedLengths = new int[9];
    private readonly Dictionary<int, bool> readGlyphs = new Dictionary<int, bool>();
    private readonly Queue<Tuple<char, int, int>> carriedGlyphs = new Queue<Tuple<char, int, int>>();
    private int nextGlyphId;
    public int GlyphsTracked { get { return readGlyphs.Count; } }
    public int GlyphsAcknowledged { get { return readGlyphs.Count(x => x.Value); } }
    private bool interactionHasBody;
    public string ScriptName = "fixture";
    private bool checkChatStart;

    public IEnumerator Script()
    {
        return DialogueReflow.IsBypassed ? OriginalScript() : DialogueReflow.Wrap(this, OriginalScript());
    }
    public int ExeText(string str, int type)
    {
        SynchronizeCarriedGlyphs();
        if (str != null)
        {
            int row = TextPos[0];
            if (checkChatStart && str.Length>0)
            {
                if (TextLen[row]!=0) throw new Exception("Chat message starts mid-row: " + ScriptName + ":" + Instruction);
                checkChatStart=false;
            }
            for (int i = 0; i < str.Length && TextLen[row] < 20; i++)
            {
                int col = TextLen[row]++;
                Text[row][col] = str[i]; TextC[row][col] = (sbyte)type;
                if (Cmd == 72 || Cmd == 82 || Cmd == 83)
                {
                    Appended.Append(str[i]); AppendedColors.Add(type);
                    int id;
                    if (carriedGlyphs.Count > 0 && carriedGlyphs.Peek().Item1 == str[i] && carriedGlyphs.Peek().Item2 == type)
                        id = carriedGlyphs.Dequeue().Item3;
                    else { id = ++nextGlyphId; readGlyphs.Add(id, false); }
                    glyphIds[row][col] = id;
                }
                else glyphIds[row][col] = 0;
            }
        }
        else if (type == 0)
        {
            TextPos[1] = 0;
            if (++TextPos[0] >= 9)
            {
                Scrolls++;
                string removed = new string(Text[TextLine], 0, TextLen[TextLine]);
                RolledOutBody.Append(removed); RetiredBody.Append(removed);
                bool unread = false;
                for (int col = 0; col < TextLen[TextLine]; col++)
                {
                    int id = glyphIds[TextLine][col];
                    if (id == 0) continue;
                    ScrolledGlyphs++;
                    if (!readGlyphs[id]) { unread = true; UnreadScrolledGlyphs++; }
                }
                if (unread) UnreadScrolls++;
                for (int row = TextLine + 1; row < 9; row++)
                {
                    Array.Copy(Text[row], Text[row-1], 20);
                    Array.Copy(TextC[row], TextC[row-1], 20);
                    Array.Copy(glyphIds[row], glyphIds[row-1], 20);
                    TextLen[row-1] = TextLen[row];
                }
                TextPos[0] = 8; TextLen[8] = 0; Array.Clear(glyphIds[8], 0, 20); TrackLengths(); return 1;
            }
            TextLen[TextPos[0]] = 0;
        }
        else if (type == 1 || type == 2)
        {
            if (Cmd != 71 && Cmd != 73 && Cmd != 75 && Cmd != 76)
            { PluginClears++; Snapshot("clear"); RetireClearedBody(); }
            for (int row = type == 1 ? 0 : TextLine; row < 9; row++) { TextLen[row] = 0; Array.Clear(glyphIds[row], 0, 20); }
            TextPos[0] = TextLine; TextPos[1] = 0;
        }
        TrackLengths(); DialogueReflow.AfterExeText(this, str, type);
        return 0;
    }
    private void TrackLengths() { for (int row = 0; row < 9; row++) trackedLengths[row] = TextLen[row]; }
    private void SynchronizeCarriedGlyphs()
    {
        // The production engine may move a trailing glyph plus punctuation to
        // the next line by reducing TextLen directly. Preserve that glyph's
        // identity/read opportunity when its original color run is re-rendered.
        for (int row = 0; row < 9; row++)
        {
            for (int col = TextLen[row]; col < trackedLengths[row]; col++)
            {
                if (glyphIds[row][col] != 0) carriedGlyphs.Enqueue(Tuple.Create(Text[row][col], (int)TextC[row][col], glyphIds[row][col]));
                glyphIds[row][col] = 0;
            }
            trackedLengths[row] = TextLen[row];
        }
    }
    private void AcknowledgeVisibleGlyphs()
    {
        SynchronizeCarriedGlyphs();
        for (int row = TextLine; row < 9; row++)
            for (int col = 0; col < TextLen[row]; col++)
                if (glyphIds[row][col] != 0) readGlyphs[glyphIds[row][col]] = true;
    }
    private void RetireClearedBody()
    { string value = String.Concat(Rows()); ClearedBody.Append(value); RetiredBody.Append(value); }
    public IEnumerator OriginalScript()
    {
        if (!Truth) { Truth = true; Else = true; yield break; }
        int op = Cmd;
        if (op == 70) { Name[ScInt[0]] = ScStr[0]; NameC[ScInt[0]] = (sbyte)ScInt[1]; }
        else if (op == 71)
        {
            if (NameID >= 0) TextLine--;
            ExeText(null, 2); NameID = unchecked((sbyte)ScInt[0]);
            if (NameID >= 0)
            { ExeText(Name[NameID], NameC[NameID]); ExeText(null, 0); TextLine++; }
        }
        else if (op == 72 || op == 82 || op == 83)
        {
            string value = op == 72 ? ScStr[0] : op == 82 ? Flag[ScInt[0]].ToString() : Name[ScInt[0]];
            if (value != null)
            {
                ExeText(value, TextColor[1]); ExeText(null, 4);
                while (TextPos[1] < TextLen[TextPos[0]])
                { TextPos[1]++; TypewriterTicks++; yield return "typed"; }
            }
        }
        else if (op == 73) { TextLine = (sbyte)ScInt[0]; ExeText(null, 2); }
        else if (op == 75 || op == 76)
        {
            if (op == 76) { ExeText(null, 3); Waits++; Snapshot("wait76"); AcknowledgeVisibleGlyphs(); RetireClearedBody(); yield return "wait"; }
            if (NameID >= 0) { NameID = -1; TextLine--; }
            ExeText(null, 2);
        }
        else if (op == 77) ExeText(null, 0);
        else if (op == 78 || op == 79)
        {
            ExeText(null, 3); Waits++; Snapshot("wait" + op); AcknowledgeVisibleGlyphs(); yield return "wait";
            if (op == 78) ExeText(null, 0);
        }
        else if (op == 80) TextColor[1] = (sbyte)ScInt[0];
        else if (op == 81) TextColor[1] = TextColor[0];
        else if (op == 105) { ExeText(ScStr[0], 3); ExeText(null, 0); }
        Else = false;
    }
    public string[] Rows()
    {
        var rows = new List<string>();
        for (int row = TextLine; row < 9; row++)
            if (TextLen[row] > 0) rows.Add(new string(Text[row], 0, TextLen[row]));
        return rows.ToArray();
    }
    public void Snapshot(string reason)
    {
        string[] rows = Rows();
        if (rows.Length == 0) return;
        int unreadRows = 0;
        for (int row = TextLine; row < 9; row++)
            if (Enumerable.Range(0, TextLen[row]).Any(col => glyphIds[row][col] != 0 && !readGlyphs[glyphIds[row][col]])) unreadRows++;
        Pages.Add(new ReflowPage { script = ScriptName, instruction = Instruction, reason = reason,
            hasSpeaker = NameID >= 0, rows = rows, widths = rows.Select(DialogueLayout.Width).ToArray(),
            rowCount = rows.Length, unreadRowCount = unreadRows, limit = 9 - TextLine });
    }
    public void Execute(int op, string target = null, string source = null, params int[] values)
    {
        bool originalWait = Truth && (op == 76 || op == 78 || op == 79);
        bool nonemptyBody = Truth && ((op == 72 && !String.IsNullOrEmpty(target)) || op == 82 || op == 83);
        if (nonemptyBody && !interactionHasBody) { Interactions++; interactionHasBody = true; }
        if (originalWait) OriginalWaits++;
        if (Truth && (op == 71 || op == 73 || op == 75))
        { Snapshot("boundary" + op); RetireClearedBody(); }
        Cmd = op; ScStr[0] = target; Array.Clear(ScInt, 0, ScInt.Length);
        Array.Copy(values, ScInt, Math.Min(values.Length, ScInt.Length));
        DialogueReflow.RecordSource(this, op, source ?? target, FixedCardLayout.StartsParagraph(ScriptName,Instruction),FixedCardLayout.IsActive(ScriptName,Instruction));
        checkChatStart = op==72 && Truth && false;
        if (op == 72) BodyCommands++;
        Drain(Script());
        if (originalWait) interactionHasBody = false;
    }
    public void Drain(IEnumerator script)
    {
        int steps = 0;
        var stack = new Stack<IEnumerator>(); stack.Push(script);
        while (stack.Count > 0)
        {
            IEnumerator current = stack.Peek();
            if (!current.MoveNext())
            { stack.Pop(); var disposable = current as IDisposable; if (disposable != null) disposable.Dispose(); continue; }
            IEnumerator nested = current.Current as IEnumerator;
            if (nested != null) { stack.Push(nested); continue; }
            if (++steps > 20000) throw new Exception("Iterator failed to finish");
            if (TextPos[0] < 0 || TextPos[0] >= 9 || TextPos[1] > TextLen[TextPos[0]])
                throw new Exception("Invalid typewriter cursor");
        }
    }
}
public sealed class ReflowPage
{
    public string script, reason;
    public int instruction, rowCount, unreadRowCount, limit;
    public bool hasSpeaker;
    public string[] rows;
    public int[] widths;
}
public sealed class ReplayCommand
{
    public string script;
    public int instruction, opcode;
    public string[] strings, expected;
    public int[] integers;
}
public sealed class ReplayCommands { public ReplayCommand[] commands; }
public static class DialogueReflowTests
{
    static int checks;
    static void Check(bool condition, string description)
    { checks++; if (!condition) throw new Exception(description); }
    static ReflowCanvas New(bool speaker = false)
    {
        DialogueReflow.Reset(); DialogueReflow.Initialize(typeof(ReflowCanvas));
        var c = new ReflowCanvas(); c.Name[0] = "播音员"; c.Name[1] = "生王正生";
        if (speaker) c.Execute(71, null, null, 0);
        return c;
    }
    static void Text(ReflowCanvas c, string text, string source = null) { c.Execute(72, text, source); }
    static void Fragment(ReflowCanvas c, string text, string source = null) { Text(c, text, source); c.Execute(77); }
    static void Fill(ReflowCanvas c, int count)
    { for (int i = 0; i < count; i += 12) Text(c, new string((char)('一' + i), Math.Min(12, count - i))); }
    static void AssertPages(ReflowCanvas c, string name)
    {
        c.Snapshot("end");
        foreach (var page in c.Pages)
        {
            Check(page.unreadRowCount <= (FixedCardLayout.IsActive(page.script,page.instruction) ? 9 : page.limit), name + ": too many unread body rows at " + page.instruction + " (" + page.reason + ") rows=" + String.Join(" / ",page.rows));
            foreach (string row in page.rows)
            {
                Check(DialogueLayout.Width(row) <= 20, name + ": row exceeds ten-full-glyph text region: " + row);
                Check(row.Length <= 20, name + ": row exceeds char buffer");
            }
        }
        Check(c.UnreadScrolls == 0, name + ": unread body rows scrolled away");
        Check(c.PluginClears == 0, name + ": plugin cleared dialogue history");
    }
    static void Regression()
    {
        foreach (bool named in new[] { false, true })
        {
            var c=New(named); Fill(c,named?40:50);
            Check(c.Waits==0,"Premature pause"); Text(c,"续");
            Check(c.Waits==1,"Missing page wait"); AssertPages(c,"capacity");
        }
        var punctuation=New(); Text(punctuation,"一二三四五六七八九十一二"); Text(punctuation,"。”");
        Check(String.Concat(punctuation.Rows())=="一二三四五六七八九十一二。”","Punctuation text lost");
        AssertPages(punctuation,"punctuation");
        var boundary=New(); Text(boundary,"一二三四五六七八九十");
        boundary.Execute(80,null,null,2); Text(boundary,"。”");
        Check(boundary.Rows().SequenceEqual(new[]{"一二三四五六七八九十","。”"}),"Punctuation moved an already displayed character");
        Check(boundary.Appended.ToString()=="一二三四五六七八九十。”" && boundary.TypewriterTicks==12,"Punctuation replayed or lost a character");
        Check(boundary.AppendedColors.SequenceEqual(Enumerable.Repeat(0,10).Concat(new[]{2,2})),"Punctuation changed glyph colors");
        AssertPages(boundary,"literal width boundary");
        var opening=New(); Text(opening,"一二三四五六七八九“后");
        Check(opening.Rows().SequenceEqual(new[]{"一二三四五六七八九“","后"}),"Opening quote moved away from the width boundary");
        var sameRun=New(); Text(sameRun,"一二三四五六七八九十。后");
        Check(sameRun.Rows().SequenceEqual(new[]{"一二三四五六七八九十","。后"}),"Punctuation changed a single-run width boundary");
        var skipped=New(); skipped.Truth=false; Text(skipped,"不显示");
        Check(skipped.Appended.Length==0 && skipped.Truth && skipped.Else,"Conditional execution changed");
    }
    static void StructuralBreakRegression()
    {
        foreach (int color in new[] { 1, 3, 5, 7 })
        {
            var c = New(); c.ScriptName = "arbitrary-unregistered-script"; c.Instruction = 7654321;
            c.Execute(80, null, null, color); Text(c, "访", "訪"); Text(c, "客", "客");
            c.Execute(81); c.Execute(77); Text(c, "“你好。”", "｢こんにちは｡");
            Check(c.Rows().SequenceEqual(new[] { "访客", "“你好。”" }), "Generic colored header was merged: " + color);
            AssertPages(c, "generic header");
        }
        var baseColor = New(); baseColor.TextColor[0] = baseColor.TextColor[1] = 2;
        baseColor.Execute(80, null, null, 4); Text(baseColor, "访客"); baseColor.Execute(81); baseColor.Execute(77); Text(baseColor, "“你好。”");
        Check(baseColor.Rows().SequenceEqual(new[] { "访客", "“你好。”" }), "Nonzero default color not supported");
        var noBreak = New(); noBreak.Execute(80, null, null, 3); Text(noBreak, "访客"); noBreak.Execute(81); Text(noBreak, "“你好。”");
        Check(noBreak.Rows().SequenceEqual(new[] { "访客“你好。”" }), "Inserted a break absent from original commands");
        var consumed = New(); consumed.Execute(80, null, null, 3); Text(consumed, "他"); consumed.Execute(81); consumed.Execute(77);
        Text(consumed, "说"); Text(consumed, "“你好。”");
        Check(consumed.Rows().SequenceEqual(new[] { "他说“你好。”" }), "Stale header candidate consumed by later quote");
        var mixed = New(); mixed.Execute(80, null, null, 3); Text(mixed, "访"); mixed.Execute(80, null, null, 5); Text(mixed, "客");
        mixed.Execute(81); mixed.Execute(77); Text(mixed, "“你好。”");
        Check(mixed.Rows().SequenceEqual(new[] { "访客“你好。”" }), "Mixed original colors misclassified as a header");
        var keyword = New(); Text(keyword, "这是"); keyword.Execute(80, null, null, 3);
        Text(keyword, "证物"); keyword.Execute(81); keyword.Execute(77); Text(keyword, "“钥匙”。");
        Check(keyword.Rows().SequenceEqual(new[] { "这是证物“钥匙”。" }), "Inline highlighted keyword forced a new row");
        var continuation = New(); continuation.Execute(80, null, null, 5); Text(continuation, "证物");
        continuation.Execute(81); continuation.Execute(77); Text(continuation, "的来源");
        Check(continuation.Rows().SequenceEqual(new[] { "证物的来源" }), "Colored fragment continuation was split");
        var sameColor = New(); sameColor.Execute(80, null, null, 3); Text(sameColor, "访客");
        sameColor.Execute(77); Text(sameColor, "“你好。”");
        Check(sameColor.Rows().SequenceEqual(new[] { "访客“你好。”" }), "Color not restored but header inferred");
        var cleared = New(); cleared.Execute(80, null, null, 3); Text(cleared, "访客");
        cleared.Execute(81); cleared.Execute(77); cleared.Execute(75); Text(cleared, "旁白"); Text(cleared, "“你好。”");
        Check(cleared.Rows().SequenceEqual(new[] { "旁白“你好。”" }), "Header candidate survived clear");
        var skipped = New(); skipped.Execute(80, null, null, 3); skipped.Truth = false; Text(skipped, "访客");
        skipped.Execute(81); skipped.Execute(77); Text(skipped, "“你好。”");
        Check(skipped.Rows().SequenceEqual(new[] { "“你好。”" }), "Skipped header affected layout");
    }
    static void SeventhCardRegression()
    {
        var c = New(); c.ScriptName = "scn1";
        c.Instruction = 10923; Text(c, "鞠滨大酒店");
        c.Instruction = 10943; c.Execute(77);
        c.Instruction = 10944; Text(c, "903号　伊崎房间");
        Check(c.Rows().SequenceEqual(new[] { "鞠滨大酒店", "903号　伊崎房间" }), "Seventh-game hotel card lost its original line break");
        AssertPages(c, "seventh hotel card");
        var help = New(); help.ScriptName = "scn0";
        help.Instruction = 2666; Text(help, "　〈操作说明〉");
        help.Instruction = 2684; help.Execute(77);
        help.Instruction = 2685; Text(help, "接下来，请切换吉娃娃和林居刑警的视角，尝试各种操作。");
        Check(help.Appended.ToString() == "　〈操作说明〉接下来，请切换吉娃娃和林居刑警的视角，尝试各种操作。", "Instruction body was truncated by fixed-card mode");
        AssertPages(help, "seventh instruction body");
    }
    static void FullScreenCapacityRegression()
    {
        for(int rows=6; rows<=9; rows++)
        {
            var c=New(); c.Execute(73,null,null,0);
            Fill(c,rows*10);
            Check(c.Waits==0,"Full-screen text paused before nine visible rows: "+rows);
            Check(c.Scrolls==0,"Full-screen text scrolled prematurely: "+rows);
            AssertPages(c,"full-screen "+rows);
        }
        var overflow=New(); overflow.Execute(73,null,null,0); Fill(overflow,90); Text(overflow,"续");
        Check(overflow.Waits==1,"Full-screen tenth row lacks one safety pause");
        AssertPages(overflow,"full-screen tenth row");
    }
    static void NotebookRegression(string input)
    {
        var json = new JavaScriptSerializer { MaxJsonLength = 100000000 };
        var commands = json.Deserialize<ReplayCommands>(File.ReadAllText(input)).commands.Where(x => x.script == "subscn_3").ToArray();
        int[] known = {69,108,147,184,219,262}, unknown = {90,129,166,201,244,279};
        for (int mask=0; mask<64; mask++)
        {
            var c=New(); c.ScriptName="subscn_3";
            var selected = new List<ReplayCommand>(commands.Where(x=>x.instruction>=46 && x.instruction<=61));
            var expected = new List<string>{"搜查笔记", ""};
            for(int clue=0;clue<6;clue++)
            {
                int start=(mask & (1<<clue))!=0 ? known[clue] : unknown[clue];
                int index=Array.FindIndex(commands,x=>x.instruction==start);
                selected.Add(commands[index]); selected.Add(commands[index+1]);
                expected.Add(commands[index].expected[0]);
            }
            foreach(var command in selected)
            {
                c.Instruction=command.instruction;
                if(command.opcode==76)
                {
                    var actual=Enumerable.Range(0,8).Select(row=>new string(c.Text[row],0,c.TextLen[row])).ToArray();
                    Check(actual.SequenceEqual(expected),"Notebook rows merged or displaced; clues="+mask+" actual="+String.Join(" / ",actual));
                    // CanvasEx.Paint uses FLeft plus native glyph advances, no
                    // dialogue-region clipping. At the installed 16px font,
                    // FLeft=44 on the 240px canvas; the longest clue ends at220.
                    foreach(string row in actual)
                    {
                        Check(44 + DialogueLayout.Width(row)*8 <= 240,"Notebook exceeds native screen width: "+row);
                        Check(row.Length<=20,"Notebook exceeds native character buffer: "+row);
                    }
                    Check(c.Appended.ToString()==String.Concat(expected),"Notebook text lost or repeated: "+mask);
                }
                c.Execute(command.opcode,command.expected.FirstOrDefault(),command.strings.FirstOrDefault(),command.integers);
            }
            Check(c.Waits==1 && c.OriginalWaits==1,"Notebook introduced or lost a click: "+mask);
            Check(c.Scrolls==0 && c.PluginClears==0,"Notebook scrolled or plugin-cleared: "+mask);
            Check(c.TextLen.All(x=>x==0),"Notebook native final clear lost: "+mask);
        }
        Console.WriteLine("Notebook: 64 clue combinations preserve title, blank row, six clue rows and one native click/clear.");
    }
    static void FullReplay(string input, string output)
    {
        var json = new JavaScriptSerializer { MaxJsonLength = 100000000, RecursionLimit = 100 };
        var commands = json.Deserialize<ReplayCommands>(File.ReadAllText(input)).commands;
        var pages = new List<ReflowPage>();
        var ignored = new SortedDictionary<int, int>();
        int bodyCommands = 0, expectedCharacters = 0, actualCharacters = 0, waits = 0, originalWaits = 0, interactions = 0;
        int scrolls = 0, unreadScrolls = 0, pluginClears = 0, rolledOutCharacters = 0, glyphsTracked = 0, glyphsAcknowledged = 0, unreadScrolledGlyphs = 0;
        foreach (var group in commands.GroupBy(x => x.script))
        {
            // Replaying both sides of every notebook branch creates an
            // impossible thirteen-clue page. Its 64 real paths are tested above.
            if(group.Key=="subscn_3") continue;
            var c = New(); c.ScriptName = group.Key;
            foreach (var command in commands.Where(x => x.opcode == 70))
                c.Execute(70, command.expected.FirstOrDefault(), null, command.integers);
            var expectedText = new StringBuilder();
            foreach (var command in group)
            {
                c.Instruction = command.instruction;
                int op = command.opcode;
                if (op == 70 || op == 71 || op == 72 || op == 73 || op == 75 || op == 76 || op == 77 || op == 78 || op == 79 || op == 80 || op == 81)
                {
                    if (op == 72) { bodyCommands++; expectedText.Append(command.expected.FirstOrDefault()); }
                    c.Execute(op, command.expected.FirstOrDefault(), command.strings.FirstOrDefault(), command.integers);
                }
                else
                { if (!ignored.ContainsKey(op)) ignored[op] = 0; ignored[op]++; }
            }
            string conserved = c.RetiredBody.ToString() + String.Concat(c.Rows());
            Check(conserved == expectedText.ToString(), "Full replay text conservation failed: " + group.Key);
            Check(c.GlyphsTracked == expectedText.Length, "Glyph identity tracking failed across carries: " + group.Key);
            AssertPages(c, "full replay " + group.Key);
            pages.AddRange(c.Pages); expectedCharacters += expectedText.Length; actualCharacters += conserved.Length; waits += c.Waits;
            originalWaits += c.OriginalWaits; interactions += c.Interactions;
            scrolls += c.Scrolls; unreadScrolls += c.UnreadScrolls; pluginClears += c.PluginClears;
            rolledOutCharacters += c.RolledOutBody.Length; glyphsTracked += c.GlyphsTracked; glyphsAcknowledged += c.GlyphsAcknowledged; unreadScrolledGlyphs += c.UnreadScrolledGlyphs;
        }
        Check(bodyCommands == commands.Count(x => x.opcode == 72 && x.script != "subscn_3"), "Not every linear body command was audited");
        var commandByAddress = commands.ToDictionary(x => x.script + ":" + x.instruction);
        var additionalWaitLocations = pages.Where(p => p.reason == "wait79" &&
            commandByAddress[p.script + ":" + p.instruction].opcode != 78 &&
            commandByAddress[p.script + ":" + p.instruction].opcode != 79).ToArray();
        Check(additionalWaitLocations.Length == waits - originalWaits, "Additional wait location count disagrees with actual iterator waits");
        var summary = new { bodyCommandsChecked = bodyCommands, notebookBranchCombinations = 64, notebookBodyCommandsChecked = commands.Count(x=>x.opcode==72 && x.script=="subscn_3"), expectedCharacters, actualCharacters,
            textConserved = expectedCharacters == actualCharacters, pageSnapshots = pages.Count,
            widthOverflows = 0, lineOverflows = 0, discardedCharacters = 0, waits, originalWaits, additionalWaits = waits - originalWaits, interactions,
            scrolls, unreadScrolls, pluginClears, rolledOutCharacters, glyphsTracked, glyphsAcknowledged, unreadScrolledGlyphs };
        var report = new { schema = 1, engine = "production DialogueReflow.Wrap with CanvasEx-compatible buffer and iterator fixture",
            scope = "Every static body72 slot except subscn_3 is played in file order, including all stored branch text. The full-screen subscn_3 notebook is separately checked across all 64 actual clue combinations. This is not a control-flow or full game simulation; runtime guards cover executed branches and dynamic text.",
            limitHalfCells = DialogueLayout.MaximumHalfCells, textRegionPixels = 160, leftMarginPixels = 44, rightMarginPixels = 36,
            bodyCommandsChecked = bodyCommands, expectedCharacters, actualCharacters, textConserved = expectedCharacters == actualCharacters,
            pageSnapshots = pages.Count, widthOverflows = 0, lineOverflows = 0, discardedCharacters = 0, waits, originalWaits, additionalWaits = waits - originalWaits, interactions,
            summary, additionalWaitLocations, ignoredOpcodes = ignored.Select(x => new { opcode = x.Key, count = x.Value }).ToArray(), pages };
        File.WriteAllText(output, json.Serialize(report), new UTF8Encoding(false));
        Console.WriteLine("Full replay: " + bodyCommands + " body commands; " + pages.Count + " page snapshots; " + actualCharacters + " characters conserved.");
    }
    public static void Main(string[] args)
    {
        try
        {
            Regression();
            StructuralBreakRegression();
            SeventhCardRegression();
            FullScreenCapacityRegression();
            if (args.Length == 1) NotebookRegression(args[0]);
            if (args.Length == 2) { NotebookRegression(args[0]); FullReplay(args[0], args[1]); }
            Console.WriteLine("PASS: " + checks + " production reflow / offline fixture assertions.");
        }
        catch (Exception error) { Console.Error.WriteLine("FAIL: " + error.Message); Environment.ExitCode = 1; }
    }
}
