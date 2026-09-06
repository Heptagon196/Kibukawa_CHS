using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Kibu1ZhCN
{
    public static class UiFontPolicy
    {
        private sealed class Original
        {
            public Font Font;
            public int Size, Min, Max;
            public float Spacing;
            public bool BestFit;
            public FontStyle Style;
        }
        private static readonly Dictionary<Text, Original> originals = new Dictionary<Text, Original>();
        public static void Capture(Text text)
        {
            if (text == null || originals.ContainsKey(text)) return;
            originals[text] = new Original { Font=text.font, Size=text.fontSize, Spacing=text.lineSpacing,
                BestFit=text.resizeTextForBestFit, Min=text.resizeTextMinSize, Max=text.resizeTextMaxSize, Style=text.fontStyle };
        }
        private static bool HasChinese(string value)
        {
            if (value == null) return false;
            foreach (char c in value) if (c >= '\u3400' && c <= '\u9fff') return true;
            return false;
        }
        public static void Apply(Text text, Font fallback)
        {
            Capture(text);
            Original original = originals[text];
            bool chinese = fallback != null && HasChinese(text.text);
            Font desired = chinese ? fallback : original.Font;
            if (text.font != desired) text.font = desired;
            // ASCII-only clocks, dates, loading and button labels keep their exact
            // original pixel font and layout. Chinese labels receive their own fit.
            float spacing = chinese ? Mathf.Max(original.Spacing, 1.2f) : original.Spacing;
            if (text.lineSpacing != spacing) text.lineSpacing = spacing;
            if (chinese)
            {
                text.resizeTextMinSize = Mathf.Max(10, original.Size * 3 / 5);
                text.resizeTextMaxSize = original.Size;
                text.resizeTextForBestFit = true;
                if (text.name == "Title(Text)" || text.name == "AboutGame(Text)") text.fontStyle = FontStyle.Bold;
            }
            else
            {
                text.fontSize = original.Size;
                text.resizeTextMinSize = original.Min;
                text.resizeTextMaxSize = original.Max;
                text.resizeTextForBestFit = original.BestFit;
                text.fontStyle = original.Style;
            }
        }
    }
}
