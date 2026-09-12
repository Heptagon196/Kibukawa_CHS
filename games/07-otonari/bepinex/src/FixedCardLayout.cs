namespace Kibu1ZhCN
{
    // Seventh-game visual cards independently traced to reviewed source units.
    // Keep native line placement on chapter/location/credit cards. The
    // instruction page uses reflow with an explicit body paragraph boundary.
    public static class FixedCardLayout
    {
        // Reuse the shared explicit paragraph-start hook so its unread-row
        // budget includes the heading; bypassing only the heading loses a row.
        public static bool StartsParagraph(string script, int instruction)
        {
            return script == "scn0" && instruction == 2685;
        }
        public static bool IsActive(string script, int instruction)
        {
            switch (script)
            {
                case "scn0": return (instruction >= 378 && instruction <= 411) ||
                    (instruction >= 9321 && instruction <= 9360) ||
                    (instruction >= 11974 && instruction <= 12010);
                case "scn1": return (instruction >= 19 && instruction <= 58) ||
                    (instruction >= 3069 && instruction <= 3105) ||
                    (instruction >= 10866 && instruction <= 10897) ||
                    (instruction >= 10923 && instruction <= 10963);
                case "scn2": return (instruction >= 22 && instruction <= 51) ||
                    (instruction >= 12212 && instruction <= 12251) ||
                    (instruction >= 12935 && instruction <= 12971);
                case "scn3": return (instruction >= 522 && instruction <= 554) ||
                    (instruction >= 573 && instruction <= 612) ||
                    (instruction >= 15734 && instruction <= 15836) ||
                    (instruction >= 15854 && instruction <= 15903) ||
                    (instruction >= 15914 && instruction <= 15952) ||
                    (instruction >= 15963 && instruction <= 16004) ||
                    (instruction >= 16015 && instruction <= 16051) ||
                    (instruction >= 16062 && instruction <= 16094);
                // Full-screen notebook: heading, blank row and six conditional
                // clues occupy native rows 0..7, followed by one original click.
                case "subscn_3": return instruction >= 46 && instruction <= 289;
                default: return false;
            }
        }
    }
}
