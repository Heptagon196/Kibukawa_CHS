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
            rowCount = rows.Length, unreadRowCount = unreadRows, limit = NameID >= 0 ? 4 : 5 });
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
        DialogueReflow.RecordSource(this, op, source ?? target, ChatLayout.IsHeader(ScriptName,Instruction),FixedCardLayout.IsActive(ScriptName,Instruction));
        checkChatStart = op==72 && Truth && ChatLayout.IsHeader(ScriptName,Instruction);
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
            Check(page.unreadRowCount <= page.limit, name + ": too many unread body rows");
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
        var credits = New(); credits.ScriptName="scn11";
        credits.Instruction=7085; Text(credits,"制作·著作","制作･著作");
        credits.Instruction=7096; credits.Execute(77);
        credits.Instruction=7097; Text(credits,"　　　元气株式会社","　　　元気株式会社");
        Check(credits.Rows().SequenceEqual(new[]{"制作·著作","　　　元气株式会社"}),"Credit role and company must be separate intact rows");
        // Original FLeft = (240 - 16 * 19 / 2) / 2 = 44 is positioning,
        // not a hard width cap. Ten full glyphs leave a 36px right gutter.
        var margin = New(); Text(margin, "一二三四五六七八九十一");
        Check(margin.Rows().SequenceEqual(new[] { "一二三四五六七八九十", "一" }), "Right gutter lost: eleventh full-width glyph must wrap");
        margin = New(); Text(margin, "123456789012345678901");
        Check(margin.Rows().SequenceEqual(new[] { "12345678901234567890", "1" }), "Right gutter lost: twenty-first half-width glyph must wrap");
        var scrollingHistory = New(); Fragment(scrollingHistory, "第一行。"); Text(scrollingHistory, "第二行。");
        scrollingHistory.Execute(78); Text(scrollingHistory, "第三行。");
        Check(scrollingHistory.Rows().SequenceEqual(new[] { "第一行。", "第二行。", "第三行。" }), "Original78 must retain acknowledged history and advance by scrolling, not clear the dialogue");
        var sharedLine = New(true); Fragment(sharedLine, "旧的一行。"); Text(sharedLine, "旧半行");
        sharedLine.Execute(79); sharedLine.Execute(80, null, null, 2); Text(sharedLine, "新半行"); sharedLine.Execute(81);
        Check(sharedLine.Rows().SequenceEqual(new[] { "旧的一行。", "旧半行新半行" }), "Original79 changed a half-line continuation into a new line");
        Check(sharedLine.TextC[6].Take(6).SequenceEqual(new sbyte[] { 0, 0, 0, 2, 2, 2 }), "Shared old/new line lost glyph colors");
        Fill(sharedLine, 34); Check(sharedLine.Waits == 1, "Read history caused an unnecessary wait while the new four-row interaction still fits");
        Fill(sharedLine, 10); Check(sharedLine.Waits == 2, "Long new interaction did not obtain a read opportunity before scrolling its shared row");
        Check(sharedLine.UnreadScrolledGlyphs == 0 && sharedLine.ScrolledGlyphs > 0, "Scrolling lost unacknowledged glyphs in a half-line continuation");
        Check(new string(sharedLine.Text[4], 0, sharedLine.TextLen[4]) == "播音员", "Scrolling a shared line damaged its speaker header");
        AssertPages(sharedLine, "original79 shared half-line");
        var baseline = New(true);
        foreach (string value in new[] { "小姐倒下时，", "仍保持着", "玩电子游戏的", "状态，" })
        {
            baseline.Cmd = 72; baseline.ScStr[0] = value; baseline.Drain(baseline.OriginalScript());
            if (value != "状态，") { baseline.Cmd = 77; baseline.Drain(baseline.OriginalScript()); }
        }
        Check(baseline.Rows().SequenceEqual(new[] { "小姐倒下时，", "仍保持着", "玩电子游戏的", "状态，" }), "Original screenshot line-break baseline did not reproduce");
        baseline.Cmd = 77; baseline.Drain(baseline.OriginalScript()); baseline.Cmd = 72; baseline.ScStr[0] = "第五行"; baseline.Drain(baseline.OriginalScript());
        Check(baseline.Scrolls > 0 && baseline.UnreadScrolls > 0 && !baseline.Rows().Contains("小姐倒下时，"), "Original five-body-row speaker scroll baseline did not reproduce");
        var c = New(true);
        Fragment(c, "小姐倒下时，"); Fragment(c, "仍保持着"); Fragment(c, "玩电子游戏的"); Text(c, "状态，");
        Check(c.Rows()[0] == "小姐倒下时，", "Punctuation-ending source break was lost");
        Check(c.Rows().Any(r => r.StartsWith("仍保持着玩电子游戏")), "Non-punctuation fragments were not joined");
        Check(c.Appended.ToString() == "小姐倒下时，仍保持着玩电子游戏的状态，", "Screenshot text changed");
        AssertPages(c, "fragment screenshot");

        c = New(true);
        Fragment(c, "“昨天下午某时，品方"); Fragment(c, "市22岁女职员");
        Fragment(c, "笠见由纪乃被发现"); Fragment(c, "死于自己居住的"); Text(c, "公寓内。”");
        Check(c.Rows()[0].StartsWith("“昨天下午"), "Screenshot first body line scrolled away");
        AssertPages(c, "news screenshot");

        c = New(); Fragment(c, "侦探事务所", "探偵事務所"); Text(c, "。");
        Check(c.Rows().Length == 1 && c.Rows()[0] == "侦探事务所。", "Short orphan full stop not joined");
        c = New(); Text(c, "一二三四五六七八九十一二"); Text(c, "。”");
        Check(!c.Rows().Any(r => r.All(DialogueLayout.IsClosingPunctuation)), "Closing punctuation stranded at a full row");
        Check(String.Concat(c.Rows()) == "一二三四五六七八九十一二。”", "Closing punctuation relocation lost text");
        AssertPages(c, "closing punctuation");

        foreach (bool named in new[] { false, true })
        {
            c = New(named); int capacity = named ? 40 : 50;
            Fill(c, capacity); Check(c.Waits == 0, "Page paused before capacity");
            Text(c, "续"); Check(c.Waits == 1, "Full page did not pause exactly once");
            Check(c.Appended.Length == capacity + 1, "Pagination dropped a character");
            Check(c.TypewriterTicks >= capacity + 1, "Wrapped rows skipped typewriter animation");
            if (named) Check(new string(c.Text[4], 0, c.TextLen[4]) == "播音员", "Speaker lost during pagination");
            AssertPages(c, named ? "four body rows" : "five body rows");
        }
        foreach (int waitOp in new[] { 78, 79 })
        {
            c = New(); Fill(c, 50); c.Execute(waitOp); Text(c, "续");
            Check(c.Waits == 1, "Original " + waitOp + " wait duplicated at pagination");
            AssertPages(c, "existing wait " + waitOp);
        }
        foreach (int waitOp in new[] { 78, 79 })
        foreach (bool named in new[] { false, true })
        {
            c = New(named); Fill(c, 20);
            string firstInteraction = String.Concat(c.Rows());
            c.Execute(waitOp);
            Check(String.Concat(c.Rows()) == firstInteraction, "Original wait prematurely removed the text being acknowledged");
            Text(c, ""); c.Execute(80, null, null, 0);
            Check(String.Concat(c.Rows()) == firstInteraction, "Empty text or a color command prematurely cleared the acknowledged interaction");
            int capacity = named ? 40 : 50;
            Fill(c, capacity);
            Check(c.Waits == 1, "Previous interaction consumed the new interaction's " + (named ? 4 : 5) + " row budget after original " + waitOp);
            Check(c.Rows().Length == (named ? 4 : 5), "Current interaction was split across pages");
            Check(c.OriginalWaits == 1 && c.Interactions == 2, "Interaction/wait accounting is incorrect");
            Check(c.RetiredBody.ToString() + String.Concat(c.Rows()) == c.Appended.ToString(), "Scrolling interactions lost body characters");
            if (named) Check(new string(c.Text[4], 0, c.TextLen[4]) == "播音员", "Speaker did not survive an interaction boundary");
            AssertPages(c, "independent interaction " + waitOp + (named ? " named" : " unnamed"));
        }
        c = New(); c.Truth = false; Text(c, "绝不显示");
        Check(c.Truth && c.Else, "Skipped command failed to preserve Truth/Else interpreter state");
        c.Truth = false; c.Execute(77);
        Check(c.Appended.Length == 0 && c.TextPos[0] == 4 && c.Waits == 0, "Truth=false command was executed");
        c = New(); Text(c, "正文"); c.Else = true; c.Execute(77);
        Check(!c.Else, "Suppressed newline failed to reset interpreter Else state");
        c = New(); c.Scene = 1; Fragment(c, "正文"); Text(c, "续文");
        Check(c.Rows().SequenceEqual(new[] { "正文", "续文" }), "Non-dialogue scene was reflowed");
        c = New(); c.Execute(105, "菜单选项");
        Check(c.Rows().SequenceEqual(new[] { "菜单选项" }) && c.TextPos[0] == 5, "Menu rendering changed");
        c = New(); Text(c, "普通"); c.Execute(80, null, null, 2); Text(c, "高亮"); c.Execute(81); Text(c, "结束");
        Check(c.AppendedColors.SequenceEqual(new[] { 0,0,2,2,0,0 }), "Text color changed across fragments");
        c = New(); c.Execute(80, null, null, 2); Text(c, "一二三四五六七八九十一二"); c.Execute(81); Text(c, "。”");
        Check(String.Concat(c.Rows()) == "一二三四五六七八九十一二。”", "Cross-color punctuation carry changed visible text");
        var visibleColors = new List<int>();
        for (int row = c.TextLine; row < 9; row++)
            for (int col = 0; col < c.TextLen[row]; col++) visibleColors.Add(c.TextC[row][col]);
        Check(visibleColors.SequenceEqual(Enumerable.Repeat(2, 12).Concat(new[] { 0, 0 })), "Carried glyph lost its original highlight color");
        Check(c.Cmd == 72 && c.ScStr[0] == "。”" && c.TextColor[1] == 0, "Wrapper did not restore original interpreter arguments");
        c = New(); Text(c, "一二三四五六七八九十一二"); c.Execute(79); c.Execute(80, null, null, 2); Text(c, "！”"); c.Execute(81); Fill(c, 60);
        Check(c.GlyphsTracked == 74, "Acknowledged punctuation carry duplicated glyph identity");
        Check(c.UnreadScrolledGlyphs == 0 && c.PluginClears == 0, "Punctuation carry after original79 lost unread text or cleared history");
        AssertPages(c, "punctuation carry across original79");
        c = New(); c.Flag[0] = 22; c.Execute(82, null, null, 0); c.Execute(83, null, null, 1);
        Check(c.Appended.ToString() == "22生王正生", "Dynamic number/name commands not preserved");
        AssertPages(c, "dynamic text");
        c = New(); Text(c, "12345678901234567890"); Text(c, "abcd");
        Check(c.Appended.ToString() == "12345678901234567890abcd", "20-character buffer truncated ASCII");
        Check(c.Rows().Length == 2, "Half-width ASCII bypassed 20-character buffer guard");
        AssertPages(c, "ASCII capacity");
        c = New(); Fragment(c, "源文句末，", "source without punctuation"); Text(c, "接续");
        Check(c.Rows().Length == 1, "Translation punctuation incorrectly preserved a source soft break");
        c = New(); Fragment(c, "岁女职员", "歳の女性会社員、"); Text(c, "笠见由纪乃被发现");
        Check(c.Rows().SequenceEqual(new[] { "岁女职员笠见由纪乃被", "发现" }), "Source punctuation retained a short break instead of filling the new width limit");
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
        Check(bodyCommands == commands.Count(x => x.opcode == 72), "Not every body command was audited");
        var commandByAddress = commands.ToDictionary(x => x.script + ":" + x.instruction);
        var additionalWaitLocations = pages.Where(p => p.reason == "wait79" &&
            commandByAddress[p.script + ":" + p.instruction].opcode != 78 &&
            commandByAddress[p.script + ":" + p.instruction].opcode != 79).ToArray();
        Check(additionalWaitLocations.Length == waits - originalWaits, "Additional wait location count disagrees with actual iterator waits");
        var summary = new { bodyCommandsChecked = bodyCommands, expectedCharacters, actualCharacters,
            textConserved = expectedCharacters == actualCharacters, pageSnapshots = pages.Count,
            widthOverflows = 0, lineOverflows = 0, discardedCharacters = 0, waits, originalWaits, additionalWaits = waits - originalWaits, interactions,
            scrolls, unreadScrolls, pluginClears, rolledOutCharacters, glyphsTracked, glyphsAcknowledged, unreadScrolledGlyphs };
        var report = new { schema = 1, engine = "production DialogueReflow.Wrap with CanvasEx-compatible buffer and iterator fixture",
            scope = "Every static body72 slot is played in file order, including all stored branch text. This is not a control-flow or full game simulation; runtime guards cover executed branches and dynamic text.",
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
            if (args.Length == 2) FullReplay(args[0], args[1]);
            Console.WriteLine("PASS: " + checks + " real-engine dialogue reflow assertions.");
        }
        catch (Exception error) { Console.Error.WriteLine("FAIL: " + error.Message); Environment.ExitCode = 1; }
    }
}
