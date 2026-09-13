using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using UnityEngine;
using Kibu1ZhCN;

namespace Kibu8ZhCN
{
    // Display-only name readings. Keys are the currently revealed profile title.
    internal static class NotebookReading
    {
        const int RomanBaseline = 35;
        const int NameBaseline = 57;
        static Type canvas;
        static BitmapFontAtlas names, roman;
        static FieldInfo origin;
        static readonly Dictionary<string,string> readings = new Dictionary<string,string> {
            {"白鹭洲伊纲","Sagishima Izuna"}, {"生王正生","Ikurumi Masao"},
            {"癸生川凌介","Kibukawa Ryosuke"}, {"林居孝一","Otonari Koichi"},
            {"尾场九岁","Oba Kokotoshi"}, {"矢口床子","Yaguchi Shoko"},
            {"莉绪","Rio"}, {"大榊晶","Osakaki Akira"}, {"小鹿野将来","Ogano Masaki"},
            {"濑堂小次郎丸","Sedo Kojiromaru"}, {"中村索亚子","Nakamura Soako"},
            {"江本佳隆","Emoto Yoshitaka"}, {"假面男子","Kamen no Otoko"},
            {"鹤见薰","Tsurumi Kaoru"}, {"鹤见瞳子","Tsurumi Hitomiko"},
            {"久我俊幸","Kuga Toshiyuki"}, {"羽泽有马","Hazawa Aruma"},
            {"羽泽美月","Hazawa Mizuki"}, {"羽泽昌泰","Hazawa Masayasu"},
            {"羽泽靖代","Hazawa Yasuyo"}, {"布雷特","Buretto"}, {"卡姆拉","Kamura"},
            {"阿尔马达","Arumada"}, {"艾纳","Aina"}, {"猫猫","Nekoneko"}, {"雪海豚","Yukiiruka"}
        };
        static object Get(object c,string n) { return AccessTools.Field(canvas,n).GetValue(c); }
        internal static void Install(Harmony h,Type type,BitmapFontAtlas font,string folder)
        {
            canvas=type; names=font; roman=new BitmapFontAtlas(System.IO.Path.Combine(folder,"fonts","roman"));
            h.Patch(AccessTools.Method(canvas,"DrawAdvString"),prefix:new HarmonyMethod(typeof(NotebookReading),"Draw"));
        }
        internal static void Dispose() { if(roman!=null) roman.Dispose(); roman=null; }
        static string Normalize(string s) { return s.Replace("　"," ").Trim(); }
        static int[] Bounds(string text,BitmapFontAtlas atlas)
        {
            int pen=0,left=int.MaxValue,right=0,bottom=int.MaxValue,top=int.MinValue;
            foreach(char c in text) {
                CharacterInfo g; if(!atlas.TryGet(c,out g)) throw new InvalidOperationException("Missing name glyph: "+c);
                if(g.maxX>g.minX && g.maxY>g.minY) { left=Math.Min(left,pen+g.minX);right=Math.Max(right,pen+g.maxX);bottom=Math.Min(bottom,g.minY);top=Math.Max(top,g.maxY); }
                pen+=g.advance;
            }
            return new[]{left,right,bottom,top};
        }
        static void Line(object graphics,string text,BitmapFontAtlas atlas,int baseline,int[] b)
        {
            if(origin==null) origin=AccessTools.Field(graphics.GetType(),"drawOrigin");
            // Match the native DrawCharImpl origin, without changing StFont metrics.
            Vector2 offset=origin==null?Vector2.zero:(Vector2)origin.GetValue(graphics);
            int x=(359-b[0]-b[1])/2;
            LegacyFontRenderer.Draw(graphics,text.ToCharArray(),x+(int)offset.x,baseline+(int)offset.y,null,atlas);
        }
        static bool Draw(object __instance,object __0,int __1,int __3)
        {
            if(__3!=0 || (int)Get(__instance,"MainTask")!=17 || (int)Get(__instance,"ListPos")!=0) return true;
            string text=Normalize(((string[])Get(__instance,"bg_itigyougun_mojiretu"))[0]??"");
            string reading; if(!readings.TryGetValue(text.Replace(" ",""),out reading)) return true;
            if(__1!=0) return false;
            // Collapse original alignment padding; center both ink bounds in the 102x24 name cell.
            while(text.Contains("  ")) text=text.Replace("  "," ");
            int[] a=Bounds(reading,roman),b=Bounds(text,names);
            AccessTools.Method(canvas,"SetColor").Invoke(__instance,new object[]{__0,((int[])Get(__instance,"ColorTable"))[1]});
            Line(__0,reading,roman,RomanBaseline,a);
            Line(__0,text,names,NameBaseline,b);
            return false;
        }
    }
}
