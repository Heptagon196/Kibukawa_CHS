using System;
using System.Collections.Generic;

namespace KibukawaHistory
{
    public sealed class ColoredHistoryLayout
    {
        public sealed class Run
        {
            public string Text = "";
            public int Color;
            public float X, Y;
        }
        public readonly List<Run> Runs = new List<Run>();
        public float Height;
        public ColoredHistoryLayout(string text, IList<int> colors, float width, float lineHeight, Func<char, float> measure)
        {
            float x = 0, y = 0;
            Run run = null;
            for (int i = 0; i < text.Length; i++)
            {
                char c = text[i];
                if (c == '\r') continue;
                if (c == '\n') { x = 0; y += lineHeight; run = null; continue; }
                float advance = measure(c);
                if (x > 0 && x + advance > width) { x = 0; y += lineHeight; run = null; }
                if (run == null || run.Color != colors[i])
                {
                    run = new Run { Color = colors[i], X = x, Y = y };
                    Runs.Add(run);
                }
                run.Text += c;
                x += advance;
            }
            Height = y + lineHeight;
        }
    }
}
