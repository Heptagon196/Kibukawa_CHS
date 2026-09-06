namespace Kibu1ZhCN
{
    // Original kibu2 positioned title/time/poem/credit pages; preserve explicit rows.
    public static class FixedCardLayout
    {
        public static bool IsActive(string script, int instruction)
        {
            // Room-assignment lists: each original 78 confirms and advances one row.
            if (script == "scn4" && instruction >= 8049 && instruction <= 8208) return true;
            if (script == "scn5" && instruction >= 9708 && instruction <= 9867) return true;
            if (script == "scn0" && instruction >= 1005 && instruction <= 1054) return true;
            if (script == "scn1" && instruction >= 6 && instruction <= 53) return true;
            if (script == "scn2" && instruction >= 9715 && instruction <= 9748) return true;
            if (script == "scn2" && instruction >= 9749 && instruction <= 9793) return true;
            if (script == "scn2" && instruction >= 9794 && instruction <= 9838) return true;
            if (script == "scn2" && instruction >= 9839 && instruction <= 9883) return true;
            if (script == "scn2" && instruction >= 9884 && instruction <= 9928) return true;
            if (script == "scn2" && instruction >= 12536 && instruction <= 12578) return true;
            if (script == "scn3" && instruction >= 999 && instruction <= 1046) return true;
            if (script == "scn3" && instruction >= 8098 && instruction <= 8146) return true;
            if (script == "scn4" && instruction >= 13174 && instruction <= 13200) return true;
            if (script == "scn4" && instruction >= 13201 && instruction <= 13262) return true;
            if (script == "scn4" && instruction >= 13277 && instruction <= 13309) return true;
            if (script == "scn5" && instruction >= 671 && instruction <= 718) return true;
            if (script == "scn5" && instruction >= 6395 && instruction <= 6463) return true;
            if (script == "scn6" && instruction >= 9 && instruction <= 76) return true;
            if (script == "scn6" && instruction >= 6180 && instruction <= 6249) return true;
            if (script == "scn6" && instruction >= 13925 && instruction <= 13957) return true;
            if (script == "scn7" && instruction >= 1533 && instruction <= 1582) return true;
            if (script == "scn7" && instruction >= 1583 && instruction <= 1637) return true;
            if (script == "scn9" && instruction >= 1675 && instruction <= 1722) return true;
            if (script == "scn9" && instruction >= 11434 && instruction <= 11476) return true;
            if (script == "scn9" && instruction >= 19766 && instruction <= 19813) return true;
            if (script == "scn9" && instruction >= 21881 && instruction <= 22373) return true;
            if (script == "scn9" && instruction >= 22578 && instruction <= 22616) return true;
            return false;
        }
    }
}
