namespace Kibu1ZhCN
{
    public static class FixedCardLayout
    {
        // These ranges belong to the hash-verified original scn11. They are
        // timed credit cards and the final title card, not flowing dialogue.
        // The build validates every translated row against native buffer/width.
        public static bool IsActive(string script,int instruction)
        {
            return script=="scn11" && ((instruction>=6690 && instruction<=7123) ||
                (instruction>=7474 && instruction<=7529));
        }
    }
}
