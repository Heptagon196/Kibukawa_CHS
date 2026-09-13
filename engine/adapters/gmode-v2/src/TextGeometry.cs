using System;
using System.Text.RegularExpressions;
namespace Kibukawa.Engine.GmodeV2
{
    public static class TextGeometry
    {
        public static float SpaceAdvance(string text, float step, float width, float narrowWidth, Func<char,bool> narrow)
        {
            int spaces = 0;
            foreach (char c in text) if (c == '\u3000' || c == ' ') spaces++;
            float ink=0;
            foreach(char c in text) if(c!='　' && c!=' ') ink+=narrow(c)?narrowWidth:step;
            return spaces == 0 ? narrowWidth : Math.Max(0, Math.Min(narrowWidth, (width-ink)/spaces));
        }
        public static float RowAdvance(string text, int end, float step, float width, float narrowWidth, Func<char,bool> narrow, float secondColumn)
        {
            float blank = SpaceAdvance(text, step, width, narrowWidth, narrow), result = 0;
            // A double-bullet row is a two-column list, not prose spacing.
            // Anchor the second column independently of label/blank widths.
            Match columns = Regex.Match(text, @"^・[^・ 　]+[ 　]+・");
            int second = columns.Success ? columns.Length - 1 : -1;
            for (int i = 0; i < Math.Min(end, text.Length); i++)
            {
                if (i == second) result = Math.Max(result, secondColumn);
                result += text[i] == '\u3000' || text[i] == ' ' ? blank : narrow(text[i]) ? narrowWidth : step;
            }
            if (end == second) result = Math.Max(result, secondColumn);
            return result;
        }
    }
}
