using System;
namespace Kibukawa.Engine.GmodeV2
{
    public static class TextBreaks
    {
        public const string Closing = "，。！？；：、,.!?;:）］｝〉》」』】〕〗〙〛’”ー—…";
        private const string Opening = "（［｛〈《「『【〔〖〘〚‘“";

        private static bool Blank(char c) { return c == ' ' || c == '\u3000'; }

        private static int KeepFacesTogether(string text, int start, int end, int limit, Func<char,int> measure)
        {
            // Include hands, sweat, open parentheses and multi-part faces.
            // Restrict the alphabet so surrounding prose is never consumed.
            foreach (System.Text.RegularExpressions.Match face in System.Text.RegularExpressions.Regex.Matches(
                text, @"[（）()⌒∇∀▽△ΔωΩДд益皿ﾟ゜°^＾;；´｀＞＜><TＴ・_＿￣－ー×＠◎ΣΞヾノ／＼〈〉＊ｏｍｂｖ≦≧￥☆⊂╬♪～ .\-　]+"))
            {
                int left=face.Index,right=face.Index+face.Length;
                while(left<right && Blank(text[left]))left++;
                while(right>left && Blank(text[right-1]))right--;
                if (left >= end || right <= end || left < start) continue;
                bool prose=false, expression=false; int width=0;
                foreach(char c in text.Substring(left,right-left)) {
                    prose |= Han(c) && "益皿".IndexOf(c)<0 || c >= 'あ' && c <= 'ゖ';
                    expression |= "⌒∇∀▽△ΔωΩДд益皿ﾟ゜°^＾´｀＞＜><TＴ_＿￣×＠◎≦≧".IndexOf(c)>=0;
                    width += measure(c);
                }
                if (!prose && expression && width <= limit) return left==start?right:left;
            }
            return end;
        }

        private static bool Han(char c) { return c >= '\u3400' && c <= '\u9fff' || c >= '\uf900' && c <= '\ufaff' || c == '〇'; }
        public static int Next(string text,int start,int limit,Func<char,int> measure,Func<char,bool> narrow)
        {
            if(limit<1 || start<0 || start>=text.Length) throw new ArgumentOutOfRangeException();
            int end=start,pixels=0;
            while(end<text.Length && pixels+measure(text[end])<=limit) {pixels+=measure(text[end]);end++;}
            if(end==start) end++;
            if(end<text.Length)
            {
                int candidate=end;
                while(candidate>start+1 && (Closing.IndexOf(text[candidate])>=0 || Opening.IndexOf(text[candidate-1])>=0)) candidate--;
                if(Closing.IndexOf(text[candidate])<0 && Opening.IndexOf(text[candidate-1])<0) end=candidate;
            }
            if(end<text.Length && narrow(text[end]) && narrow(text[end-1]))
            {
                int word=end;
                while(word>start && narrow(text[word-1])) word--;
                if(word>start) end=word;
            }
            return KeepFacesTogether(text,start,end,limit,measure);
        }
    }
}
