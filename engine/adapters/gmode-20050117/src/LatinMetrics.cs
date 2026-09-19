using System;

namespace Kibukawa.Engine.Gmode20050117
{
    /// <summary>
    /// The eighth game's Latin policy, applied to this VM at draw time.  Kibu9 cannot
    /// insert spacing cells into the script line without changing its command budget,
    /// so Han/Latin boundary blanks are represented by the same 9px visual advance.
    /// </summary>
    public static class LatinMetrics
    {
        public static char Display(char c)
        {
            if (c >= '０' && c <= '９' || c >= 'Ａ' && c <= 'Ｚ' || c >= 'ａ' && c <= 'ｚ')
                return (char)(c - 0xfee0);
            return c;
        }

        public static bool Narrow(char c)
        {
            c = Display(c);
            return c >= '0' && c <= '9' || c >= 'A' && c <= 'Z' || c >= 'a' && c <= 'z';
        }

        public static int Width(char c) { return Narrow(c) || c == ' ' || c == '　' ? 9 : 17; }

        private static bool Han(char c)
        {
            return c >= '\u3400' && c <= '\u9fff' || c >= '\uf900' && c <= '\ufaff' || c == '〇';
        }

        private static bool Boundary(char left, char right)
        {
            return Han(left) && Narrow(right) || Narrow(left) && Han(right);
        }

        public static int Advance(string text, int end)
        {
            if (String.IsNullOrEmpty(text) || end <= 0) return 0;
            end = Math.Min(end, text.Length);
            int width = 0;
            for (int i = 0; i < end; i++)
            {
                if (i > 0 && Boundary(text[i - 1], text[i])) width += 9;
                width += Width(text[i]);
            }
            // The eighth game inserts its visual blank before the following Latin/Han
            // cell. A prefix position for that following cell must therefore include
            // the boundary even though the cell itself is outside [0,end).
            if (end > 0 && end < text.Length && Boundary(text[end - 1], text[end])) width += 9;
            return width;
        }

    }
}
