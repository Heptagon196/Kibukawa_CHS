namespace Kibu1ZhCN
{
    // Fourth-game positioned title/credit cards: original opcode 74 mode 1..0.
    // Addresses audited against both original resource archives.
    public static class FixedCardLayout
    {
        public static bool IsActive(string script, int instruction)
        {
            // Entire timed opening-credit sequence, including dialogue between
            // cards. Opcode 84 + original delays control its presentation.
            // Return to interactive dialogue at 18284 (opcode 73, mode 4).
            if (script == "scn0" && instruction >= 15365 && instruction <= 18282) return true;
            if (script == "scn0" && instruction >= 15388 && instruction <= 15437) return true;
            if (script == "scn0" && instruction >= 15672 && instruction <= 15722) return true;
            if (script == "scn0" && instruction >= 16025 && instruction <= 16069) return true;
            if (script == "scn0" && instruction >= 16185 && instruction <= 16224) return true;
            if (script == "scn0" && instruction >= 16411 && instruction <= 16453) return true;
            if (script == "scn0" && instruction >= 16724 && instruction <= 16785) return true;
            if (script == "scn0" && instruction >= 16974 && instruction <= 17015) return true;
            if (script == "scn0" && instruction >= 17150 && instruction <= 17189) return true;
            if (script == "scn0" && instruction >= 17753 && instruction <= 17797) return true;
            if (script == "scn0" && instruction >= 18235 && instruction <= 18282) return true;
            if (script == "scn0" && instruction >= 18698 && instruction <= 18742) return true;
            if (script == "scn7" && instruction >= 10880 && instruction <= 10902) return true;
            return false;
        }
    }
}
