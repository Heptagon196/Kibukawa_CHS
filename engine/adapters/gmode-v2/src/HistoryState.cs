using System;
using System.Collections.Generic;
using System.Text;
namespace KibukawaHistory
{
    public sealed class SoftKeyHintState
    {
        private string original;
        private bool replaced;
        public string Original(string current)
        {
            if (!replaced || current != LeftSoftKeyHint.Caption) { original=current;replaced=false; }
            return original;
        }
        public static bool Allowed(string label,string inactive)
        { return inactive != null && (label == inactive || label == "---"); }
        public string Render(string current,bool available,string inactive)
        {
            string source=Original(current);replaced=available && Allowed(source,inactive);
            return replaced ? LeftSoftKeyHint.Caption : source;
        }
    }
    public class DrawnTextHistory
    {
        private readonly HashSet<long> drawn = new HashSet<long>();
        private bool active, started, pendingBreak;
        public void Begin() { drawn.Clear(); active=true;started=false;pendingBreak=false; }
        public bool Seen(int row,int charIndex) { return drawn.Contains(((long)row<<32)|(uint)charIndex); }
        public void Draw(HistoryBuffer history,int row,int charIndex,char value,int color,string speaker,int speakerColor,bool breakAfter=false)
        {
            if(!active || row<0 || charIndex<0) return;
            long key=((long)row<<32)|(uint)charIndex;
            if(!drawn.Add(key)) return;
            if(!started)
            {
                history.Break();started=true;
                if(!String.IsNullOrEmpty(speaker))
                {
                    string caption=speaker+"\n";int[] colors=new int[caption.Length];
                    for(int i=0;i<colors.Length;i++) colors[i]=speakerColor;
                    history.Append(caption,colors);
                }
            }
            // Reflow physical rows, but retain the next revealed utterance's
            // logical boundary. Redraws never insert duplicate separators.
            if(pendingBreak) { history.Append("\n",new[]{0xffffff});pendingBreak=false; }
            if(value>='０' && value<='９' || value>='Ａ' && value<='Ｚ' || value>='ａ' && value<='ｚ') value=(char)(value-0xfee0);
            if(value=='　') value=' ';
            history.Append(value.ToString(),new[]{color});
            pendingBreak=breakAfter;
        }
    }

    /// <summary>
    /// The 20050117 renderer can reveal a few cells, enter a resumed full redraw,
    /// and then visit earlier rows or missing cells. Keep only cells that were
    /// actually drawn, but rebuild the active entry in native (row, character)
    /// order instead of treating callback time as reading order.
    /// </summary>
    public sealed class OrderedDrawnTextHistory
    {
        private sealed class Glyph
        {
            public char Value;
            public int Color;
        }

        private readonly HashSet<long> drawn = new HashSet<long>();
        private readonly SortedDictionary<int, SortedDictionary<int, Glyph>> rows =
            new SortedDictionary<int, SortedDictionary<int, Glyph>>();
        private bool active;
        private bool started;
        private string speaker;
        private int speakerColor;

        public void Begin()
        {
            drawn.Clear();
            rows.Clear();
            active = true;
            started = false;
            speaker = null;
            speakerColor = 0xffffff;
        }

        public bool Seen(int row, int charIndex)
        {
            return drawn.Contains(((long)row << 32) | (uint)charIndex);
        }

        public void Draw(HistoryBuffer history, int row, int charIndex, char value, int color,
                         string currentSpeaker, int currentSpeakerColor, bool breakAfter = false)
        {
            if (!active || row < 0 || charIndex < 0) return;
            long key = ((long)row << 32) | (uint)charIndex;
            if (!drawn.Add(key)) return;
            if (value >= '０' && value <= '９' || value >= 'Ａ' && value <= 'Ｚ'
                || value >= 'ａ' && value <= 'ｚ') value = (char)(value - 0xfee0);
            if (value == '　') value = ' ';

            SortedDictionary<int, Glyph> line;
            if (!rows.TryGetValue(row, out line))
            {
                line = new SortedDictionary<int, Glyph>();
                rows.Add(row, line);
            }
            line.Add(charIndex, new Glyph { Value = value, Color = color & 0xffffff });

            if (!started)
            {
                history.Break();
                started = true;
                speaker = currentSpeaker;
                speakerColor = currentSpeakerColor & 0xffffff;
                string first;
                List<int> firstColors;
                Build(out first, out firstColors);
                history.Append(first, firstColors.ToArray());
                return;
            }

            string text;
            List<int> colors;
            Build(out text, out colors);
            history.ReplaceLast(text, colors);
        }

        private void Build(out string text, out List<int> colors)
        {
            StringBuilder value = new StringBuilder();
            colors = new List<int>();
            if (!String.IsNullOrEmpty(speaker))
            {
                value.Append(speaker);
                for (int i = 0; i < speaker.Length; i++) colors.Add(speakerColor);
                value.Append('\n');
                colors.Add(speakerColor);
            }
            bool afterFirstRow = false;
            foreach (KeyValuePair<int, SortedDictionary<int, Glyph>> row in rows)
            {
                if (afterFirstRow)
                {
                    value.Append('\n');
                    colors.Add(0xffffff);
                }
                foreach (KeyValuePair<int, Glyph> cell in row.Value)
                {
                    value.Append(cell.Value.Value);
                    colors.Add(cell.Value.Color);
                }
                afterFirstRow = true;
            }
            text = value.ToString();
        }
    }
}
