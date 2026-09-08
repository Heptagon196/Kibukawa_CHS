namespace Kibu1ZhCN
{
    // kibu5 original instruction byte cursors, audited in source-replay.json.
    // These cards retain original blank rows, explicit line breaks and waits.
    // This does not change script bytes, jump targets or saved positions.
    public static class FixedCardLayout
    {
        public static bool IsActive(string script, int instruction)
        {
            if (script == "scn0")
            {
                // Prologue title and subtitle.
                if (instruction >= 892 && instruction <= 935) return true;
                // Three-line letter, including its separate signature row.
                if (instruction >= 15627 && instruction <= 15676) return true;
            }
            if (script == "scn1" && instruction >= 1391 && instruction <= 1416) return true;
            if (script == "scn3" && instruction >= 1655 && instruction <= 1678) return true;
            if (script == "scn5" && instruction >= 1489 && instruction <= 1515) return true;
            if (script == "scn6")
            {
                // Individually displayed number clue and culprit revelation.
                if (instruction >= 6069 && instruction <= 6091) return true;
                if (instruction >= 7930 && instruction <= 7956) return true;
                // Title / complete timed staff cards; ends at their original clear.
                if (instruction >= 21796 && instruction <= 22362) return true;
                // Ending card.
                if (instruction >= 22987 && instruction <= 23009) return true;
            }
            return false;
        }
    }
}
