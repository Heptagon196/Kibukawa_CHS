namespace Kibu1ZhCN
{
    // Sixth-game instruction positions independently derived from its manifest
    // and original command replay, not inherited from another game's layout.
    public static class FixedCardLayout
    {
        public static bool IsActive(string script, int instruction)
        {
            switch (script)
            {
                case "scn0": return instruction >= 15719 && instruction <= 15736;
                case "scn1": return instruction >= 10336 && instruction <= 10495;
                case "scn2": return instruction >= 15624 && instruction <= 15641;
                case "scn3": return instruction >= 11355 && instruction <= 11514;
                case "scn4": return instruction >= 12313 && instruction <= 12330;
                case "scn5":
                    return (instruction >= 13334 && instruction <= 13445) ||
                           (instruction >= 15370 && instruction <= 15574);
                case "scn9":
                    return (instruction >= 1335 && instruction <= 1970) ||
                           (instruction >= 6028 && instruction <= 6062) || instruction == 8396;
                case "scn10": return (instruction >= 420 && instruction <= 438) || instruction == 10807;
                case "scn11": return instruction >= 19296 && instruction <= 19313;
                default: return false;
            }
        }
    }
}
