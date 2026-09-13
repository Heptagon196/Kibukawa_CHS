using System;
using System.Collections.Generic;
namespace KibukawaHistory
{
    // Eighth-game idle softkeys are empty, unlike the older VM's "---".
    public static class Gmode20050817HistoryCapture
    {
        // Values are copied into HistoryBuffer; later palette/buffer changes
        // cannot recolor or rewrite previously executed text.
        public static void Capture(HistoryBuffer history,string[] rows,sbyte[] counts,sbyte[][] colors,int[] palette,int count)
        {
            if (count < 0 || count > rows.Length || count > counts.Length || count > colors.Length) throw new ArgumentException("Invalid row count");
            history.Break();
            bool wrote=false;
            for(int r=0;r<count;r++)
            {
                string text=rows[r] ?? String.Empty;
                int slots=counts[r],cursor=0;
                if(slots < 0 || slots > (colors[r] == null ? 0 : colors[r].Length)) throw new ArgumentException("Invalid color count");
                var value=new System.Text.StringBuilder();var rgb=new List<int>();
                for(int i=0;i<slots && cursor<text.Length;i++)
                {
                    int paletteIndex=(byte)colors[r][i];
                    if(paletteIndex>=palette.Length) throw new ArgumentException("Invalid palette index");
                    int n=(text[cursor]<=127 || text[cursor]>=0xff61 && text[cursor]<=0xff9f)?2:1;
                    for(int j=0;j<n && cursor<text.Length;j++) { value.Append(text[cursor++]);rgb.Add(palette[paletteIndex]&0xffffff); }
                }
                if(value.Length==0) continue;
                if(wrote) history.Append("\n",new[]{0xffffff});
                history.Append(value.ToString(),rgb.ToArray());wrote=true;
            }
            history.Break();
        }
    }
    public sealed class DrawnHistoryTracker : DrawnTextHistory
    {
        public void Draw(HistoryBuffer history,int row,int charIndex,char value,int color,string speaker,int speakerColor,int mainTask=0,int terminalControl=0)
        {
            if(mainTask==17) return;
            base.Draw(history,row,charIndex,value,color,speaker,speakerColor,terminalControl==0x3b || terminalControl==0x2e);
        }
    }
}
