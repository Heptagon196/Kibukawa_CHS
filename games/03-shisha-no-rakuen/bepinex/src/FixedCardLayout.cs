namespace Kibu1ZhCN
{
    // kibu3 source-replay.json byte addresses, audited against original commands.
    // Preserve explicit blank rows, timed credits and positioned signatures.
    // Never inherit another game's offsets.
    public static class FixedCardLayout
    {
        public static bool IsActive(string script, int instruction)
        {
            // Prologue title.
            if (script == "scn0" && instruction >= 1103 && instruction <= 1153) return true;
            // Letter signature.
            if (script == "scn0" && instruction >= 7432 && instruction <= 7496) return true;
            // Repeated letter signature.
            if (script == "scn0" && instruction >= 10850 && instruction <= 10910) return true;
            // Chapter 1 title.
            if (script == "scn1" && instruction >= 4 && instruction <= 60) return true;
            // Repeated letter signature.
            if (script == "scn1" && instruction >= 3609 && instruction <= 3669) return true;
            // Two deliberately positioned threat pages.
            if (script == "scn3" && instruction >= 223 && instruction <= 268) return true;
            // Chapter 2 title.
            if (script == "scn3" && instruction >= 276 && instruction <= 332) return true;
            // Chapter 3 title.
            if (script == "scn5" && instruction >= 1284 && instruction <= 1338) return true;
            // Repeated threat pages.
            if (script == "scn5" && instruction >= 11982 && instruction <= 12027) return true;
            // Final chapter title.
            if (script == "scn7" && instruction >= 1014 && instruction <= 1067) return true;
            // Letter conclusion and signature.
            if (script == "scn7" && instruction >= 2667 && instruction <= 2723) return true;
            // Closing narration before credits.
            if (script == "scn10" && instruction >= 3935 && instruction <= 3970) return true;
            // Timed staff cards; keep original waits and clears.
            if (script == "scn10" && instruction >= 3980 && instruction <= 4524) return true;
            // Epilogue date and location.
            if (script == "scn10" && instruction >= 4539 && instruction <= 4587) return true;
            // Simultaneous scene and location.
            if (script == "scn10" && instruction >= 6694 && instruction <= 6765) return true;
            // The end.
            if (script == "scn10" && instruction >= 9140 && instruction <= 9164) return true;
            return false;
        }
    }
}
