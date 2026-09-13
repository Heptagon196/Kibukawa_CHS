namespace Kibukawa.Engine.Gmode20050817
{
    public static class LatinMetrics
    {
        public static char Display(char c) {
            if(c>='０' && c<='９' || c>='Ａ' && c<='Ｚ' || c>='ａ' && c<='ｚ') return (char)(c-0xfee0);
            return c;
        }
        public static bool Narrow(char c) {
            c=Display(c);return c>='0' && c<='9' || c>='A' && c<='Z' || c>='a' && c<='z';
        }
        public static int NotebookWidth(char c, int fullWidth) { return c==' ' || c=='　' ? 6 : Narrow(c) ? 7 : fullWidth; }
        public static int Width(char c) { return Narrow(c) || c==' ' || c=='　' ? 9 : 17; }
    }
    // Rendering policy is supplied by the game entry point, not inferred from its name.
    public sealed class RuntimeLayout
    {
        public readonly int RowAdvance, TopOffset, DialogueRows, DialogueColumns, BodyAdvance, InfoBaseline, InfoAdvance, InfoSpaceAdvance;
        public readonly string[] SmallFontMethods;
        public RuntimeLayout(int columns, int dialogueRows, int rowAdvance, int topOffset, int bodyAdvance, int infoBaseline, int infoAdvance, int infoSpaceAdvance, string[] smallFontMethods)
        {
            RowAdvance=rowAdvance; TopOffset=topOffset; DialogueColumns=columns; DialogueRows=dialogueRows; BodyAdvance=bodyAdvance; InfoBaseline=infoBaseline;
            InfoAdvance=infoAdvance; InfoSpaceAdvance=infoSpaceAdvance;
            SmallFontMethods=(string[])smallFontMethods.Clone();
        }
    }
}
