using System;
using System.Collections.Generic;
using Kibukawa8.Runtime;

namespace Kibukawa.Engine.Gmode20050817
{
    internal static class NativeDialogueLayout
    {
        private const string Closing = Kibukawa.Engine.GmodeV2.TextBreaks.Closing;
        private static bool Blank(char c) { return c == ' ' || c == '\u3000'; }

        private static bool Han(char c)
        {
            return c >= '\u3400' && c <= '\u9fff' || c >= '\uf900' && c <= '\ufaff' || c == '〇';
        }
        internal static bool DigitHanBoundary(char left, char right)
        {
            char a=LatinMetrics.Display(left), b=LatinMetrics.Display(right);
            return a>='0' && a<='9' && Han(right) || Han(left) && b>='0' && b<='9';
        }
        private static RuntimeRow SpaceLatinBoundaries(RuntimeRow row)
        {
            var text = new System.Text.StringBuilder();
            var colors = new List<byte>(); var controls = new List<byte>();
            for (int i = 0; i < row.Text.Length; i++)
            {
                char c = row.Text[i];
                if (i > 0 && (Han(row.Text[i-1]) && LatinMetrics.Narrow(c) ||
                    LatinMetrics.Narrow(row.Text[i-1]) && Han(c)))
                {
                    // A native fullwidth slot rendered with a halfwidth blank advance.
                    text.Append('\u3000'); colors.Add(row.Colors[i]); controls.Add(0);
                }
                text.Append(c); colors.Add(row.Colors[i]); controls.Add(row.Controls[i]);
            }
            return new RuntimeRow { Text=text.ToString(), SourceText=row.SourceText,
                Colors=colors.ToArray(), Controls=controls.ToArray(), RubyJson=row.RubyJson };
        }

        internal static string PrepareChoiceText(string text)
        {
            return SpaceLatinBoundaries(new RuntimeRow { Text=text, SourceText=text,
                Colors=new byte[text.Length], Controls=new byte[text.Length], RubyJson="{}" }).Text;
        }
        internal static RuntimeRow[] PrepareNotebookRows(RuntimeRow[] source)
        {
            // Preserve the native profile fields and notebook's authored rows.
            var rows = new RuntimeRow[source.Length];
            for (int i=0;i<rows.Length;i++) rows[i]=SpaceLatinBoundaries(source[i]);
            return rows;
        }

        private static bool EndsClause(string text)
        {
            text=(text ?? String.Empty).TrimEnd();
            return text.Length>0 && Closing.IndexOf(text[text.Length-1])>=0;
        }
        private static bool HardBoundary(RuntimeRow previous, RuntimeRow next)
        {
            if(String.IsNullOrWhiteSpace(previous.Text) || String.IsNullOrWhiteSpace(next.Text)) return true;
            // Keep intentional spaced headings and indented layouts. The source
            // layout is authoritative too: translations may contain fewer glyphs,
            // but that must not turn separately authored credit rows into one row.
            if(previous.Text.IndexOf('\u3000')>=0 || next.Text.IndexOf('\u3000')>=0 ||
                (previous.SourceText ?? String.Empty).IndexOf('\u3000')>=0 ||
                (next.SourceText ?? String.Empty).IndexOf('\u3000')>=0 ||
                next.Text[0]==' ' || next.Text[0]=='\u3000') return true;
            byte terminal=previous.Controls[previous.Controls.Length-1];
            if(terminal!=0 && terminal!=0x2f) return true;
            // Same policy as gmode-v1: preserve a clause break only if both
            // the original and translated fragment end at that punctuation.
            if(EndsClause(previous.SourceText) && EndsClause(previous.Text)) return true;
            // A chapter number is a heading, not an automatically wrapped sentence.
            if(System.Text.RegularExpressions.Regex.IsMatch(previous.SourceText ?? String.Empty,@"^第[0-9０-９一二三四五六七八九十百]+章$")) return true;
            string speech=next.Text.TrimStart();
            bool quoted=speech.Length>0 && "「『“‘\"".IndexOf(speech[0])>=0;
            bool uniform=previous.Colors.Length>0;
            for(int i=1;i<previous.Colors.Length;i++) uniform &= previous.Colors[i]==previous.Colors[0];
            return quoted && uniform && next.Colors.Length>0 && previous.Colors[0]!=next.Colors[0];
        }
        private static RuntimeRow Merge(RuntimeRow a, RuntimeRow b)
        {
            var colors=new byte[a.Colors.Length+b.Colors.Length];var controls=new byte[colors.Length];
            Array.Copy(a.Colors,colors,a.Colors.Length);Array.Copy(b.Colors,0,colors,a.Colors.Length,b.Colors.Length);
            Array.Copy(a.Controls,controls,a.Controls.Length);Array.Copy(b.Controls,0,controls,a.Controls.Length,b.Controls.Length);
            return new RuntimeRow {Text=a.Text+b.Text,SourceText=a.SourceText+b.SourceText,Colors=colors,Controls=controls,RubyJson="{}"};
        }
        private static IEnumerable<RuntimeRow> JoinSoftRows(RuntimeRow[] rows)
        {
            RuntimeRow pending=null,previous=null;
            foreach(var row in rows)
            {
                if(row==null || row.Text==null || row.Colors==null || row.Controls==null || row.Text.Length!=row.Colors.Length || row.Text.Length!=row.Controls.Length)
                    throw new ArgumentException("Dialogue text/color/control planes must match");
                if(pending!=null && HardBoundary(previous,row)) {yield return pending;pending=null;}
                pending=pending==null?row:Merge(pending,row);previous=row;
            }
            if(pending!=null) yield return pending;
        }
        // Preserve VM events at their original characters. This only reflows the
        // display buffer; it does not change script bytes or script/save offsets.
        public static RuntimeRow[] Wrap(RuntimeRow[] rows, int columns = 12)
        {
            if (columns < 1 || columns > 127) throw new ArgumentOutOfRangeException("columns");
            if (rows == null) throw new ArgumentNullException("rows");
            var result = new List<RuntimeRow>();
            foreach (RuntimeRow joined in JoinSoftRows(rows))
            {
                RuntimeRow row = SpaceLatinBoundaries(joined);
                bool slashBreaks=Array.IndexOf(row.Controls,(byte)0x2f)>=0;
                // SLASH advances to the next display row (and updates scroll),
                // so old internal SLASH positions must not survive reflow.
                // Recreate them at new row ends; keep waits/events untouched.
                for(int i=0;i<row.Controls.Length-1;i++)
                    if(row.Controls[i]==0x2f)row.Controls[i]=0;
                if (row == null || row.Text == null || row.Colors == null || row.Controls == null ||
                    row.Colors.Length != row.Text.Length || row.Controls.Length != row.Text.Length)
                    throw new ArgumentException("Dialogue text, color and control planes must have matching lengths.");
                int ink = 0;
                int width=0;
                foreach (char c in row.Text) { width+=LatinMetrics.Width(c); if (!Blank(c)) ink+=LatinMetrics.Width(c); }
                // Spaced title cards retain their original spacing positions;
                // FitDraw compresses only blank advances to the available width.
                if (width <= columns*17 || ink <= columns*17)
                {
                    result.Add(Slice(row, 0, row.Text.Length));
                }
                else
                {
                    int start = 0;
                    while (start < row.Text.Length)
                    {
                        int end=Kibukawa.Engine.GmodeV2.TextBreaks.Next(row.Text,start,columns*17,LatinMetrics.Width,LatinMetrics.Narrow);
                        var output=Slice(row, start, end - start);
                        if(slashBreaks && end<row.Text.Length && output.Controls[output.Controls.Length-1]==0)
                            output.Controls[output.Controls.Length-1]=0x2f;
                        result.Add(output);
                        start = end;
                    }
                }
                if (result.Count > SByte.MaxValue)
                    throw new InvalidOperationException("Reflowed dialogue exceeds the VM's 127-row limit.");
            }
            return result.ToArray();
        }

        public static RuntimeRow[] WrapWithAnnotations(RuntimeRow[] source, int columns, int capacity)
        {
            var prepared = new List<RuntimeRow>();
            var pending = new List<RuntimeRow>();
            foreach (var row in source)
            {
                var note = System.Text.RegularExpressions.Regex.Match(row.Text, @"[（(]译注[：:].*[）)]$");
                if (!note.Success || note.Index == 0) { pending.Add(row); continue; }
                var combined = new List<RuntimeRow>(pending); combined.Add(row);
                if (Wrap(combined.ToArray(), columns).Length <= capacity)
                { pending.Add(row); continue; }
                // Long notes start a new native click segment. Preserve the
                // original terminal event on the note, and pause after speech.
                var speech = Slice(row, 0, note.Index);
                if (speech.Controls[speech.Controls.Length-1] == 0)
                    speech.Controls[speech.Controls.Length-1] = 0x3b;
                pending.Add(speech);
                prepared.AddRange(Wrap(pending.ToArray(), columns)); pending.Clear();
                prepared.AddRange(Wrap(new[]{Slice(row,note.Index,note.Length)},columns));
            }
            prepared.AddRange(Wrap(pending.ToArray(), columns));
            if (prepared.Count > SByte.MaxValue) throw new InvalidOperationException("Too many dialogue rows including notes");
            return prepared.ToArray();
        }

        private static RuntimeRow Slice(RuntimeRow source, int start, int length)
        {
            var colors = new byte[length];
            var controls = new byte[length];
            Array.Copy(source.Colors, start, colors, 0, length);
            Array.Copy(source.Controls, start, controls, 0, length);
            return new RuntimeRow { SourceText = source.SourceText, Text = source.Text.Substring(start, length),
                Colors = colors, Controls = controls, RubyJson = "{}" };
        }
    }
}
