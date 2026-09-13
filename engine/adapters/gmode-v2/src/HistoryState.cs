using System;
using System.Collections.Generic;
namespace KibukawaHistory
{
    public sealed class SoftKeyHintState
    {
        private string original;
        private bool replaced;
        public string Original(string current)
        {
            if (!replaced || current != LeftSoftKeyHint.Caption) { original=current;replaced=false; }
            return original;
        }
        public static bool Allowed(string label,string inactive)
        { return inactive != null && (label == inactive || label == "---"); }
        public string Render(string current,bool available,string inactive)
        {
            string source=Original(current);replaced=available && Allowed(source,inactive);
            return replaced ? LeftSoftKeyHint.Caption : source;
        }
    }
    public class DrawnTextHistory
    {
        private readonly HashSet<long> drawn = new HashSet<long>();
        private bool active, started, pendingBreak;
        public void Begin() { drawn.Clear(); active=true;started=false;pendingBreak=false; }
        public bool Seen(int row,int charIndex) { return drawn.Contains(((long)row<<32)|(uint)charIndex); }
        public void Draw(HistoryBuffer history,int row,int charIndex,char value,int color,string speaker,int speakerColor,bool breakAfter=false)
        {
            if(!active || row<0 || charIndex<0) return;
            long key=((long)row<<32)|(uint)charIndex;
            if(!drawn.Add(key)) return;
            if(!started)
            {
                history.Break();started=true;
                if(!String.IsNullOrEmpty(speaker))
                {
                    string caption=speaker+"\n";int[] colors=new int[caption.Length];
                    for(int i=0;i<colors.Length;i++) colors[i]=speakerColor;
                    history.Append(caption,colors);
                }
            }
            // Reflow physical rows, but retain the next revealed utterance's
            // logical boundary. Redraws never insert duplicate separators.
            if(pendingBreak) { history.Append("\n",new[]{0xffffff});pendingBreak=false; }
            if(value>='０' && value<='９' || value>='Ａ' && value<='Ｚ' || value>='ａ' && value<='ｚ') value=(char)(value-0xfee0);
            if(value=='　') value=' ';
            history.Append(value.ToString(),new[]{color});
            pendingBreak=breakAfter;
        }
    }
}
