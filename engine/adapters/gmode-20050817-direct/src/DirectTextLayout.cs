using System;
using System.Collections.Generic;
using System.Text;
using Kibukawa8.Runtime;
using Kibukawa.Engine.Gmode20050817;

namespace Kibukawa.Engine.Gmode20050817Direct
{
 internal static class DirectTextLayout
 {
  // Mixed-script separation is always one half-cell in the active grid:
  // 9px beside the 17px dialogue cell, 6px beside the native 12px cell.
  const int MixedGap=9;
  const string Close="，。！？；：、）》」』】〕〉”’…—％%!?.,;:)]}";
  const string Open="（《「『【〔〈“‘([{\"";
  static bool Han(char c) {return c>='\u3400' && c<='\u9fff' || c=='〇';}
  internal static bool Gap(char a,char b) {return Han(a) && LatinMetrics.Narrow(b) || LatinMetrics.Narrow(a) && Han(b);}
  internal static int Cell(char c) {return LatinMetrics.Width(c);}
  static bool Blank(char c) {return c==' ' || c=='　';}
  static bool MixedBlank(string text,int index)
  {
   if(!Blank(text[index]) || index==0 || index+1>=text.Length)return false;
   char a=text[index-1],b=text[index+1];
   return Han(a) && LatinMetrics.Narrow(b) || LatinMetrics.Narrow(a) && Han(b);
  }
  static int GridCell(char c,bool native) {return native?(LatinMetrics.Narrow(c)||c==' '?6:12):Cell(c);}
  static int GridGap(bool native) {return native?6:MixedGap;}
  static int Advance(string text,int index,bool native) {return MixedBlank(text,index)?GridGap(native):GridCell(text[index],native);}
  static int GridMeasure(string text,int start,int end,bool native)
  {
   int width=0,gap=GridGap(native);
   for(int i=start;i<end;i++){if(i>start && Gap(text[i-1],text[i]))width+=gap;width+=Advance(text,i,native);}
   return width;
  }
  internal static int Measure(string text,int start,int end)
  { return GridMeasure(text,start,end,false); }
  internal static int MeasureNative(string text,int start,int end)
  { return GridMeasure(text,start,end,true); }
  static int GridPosition(string text,int slot,bool native)
  {
   slot=Math.Min(slot,text.Length);
   int width=GridMeasure(text,0,slot,native);
   if(slot>0 && slot<text.Length && Gap(text[slot-1],text[slot]))width+=GridGap(native);
   return width;
  }
  internal static int Position(string text,int slot)
  { return GridPosition(text,slot,false); }
  internal static int PositionNative(string text,int slot)
  { return GridPosition(text,slot,true); }
  static bool End(string s) {s=(s??"").TrimEnd();return s.Length>0 && "。！？!?」』”’".IndexOf(s[s.Length-1])>=0;}
  static bool Spaced(string s) {return !String.IsNullOrEmpty(s) && (s.IndexOf('　')>=0 || Char.IsWhiteSpace(s[0]));}
  static bool Leading(string s) {s=(s??"").TrimStart();return s.Length>0 && (s[0]=='…' || Open.IndexOf(s[0])>=0);}
  static bool Hard(RuntimeRow a,RuntimeRow b)
  {
   if(String.IsNullOrWhiteSpace(a.Text)||String.IsNullOrWhiteSpace(b.Text))return true;
   if(Spaced(a.SourceText)||Spaced(b.SourceText))return true;
   if(End(a.SourceText)||End(a.Text)||Leading(b.SourceText))return true;
   bool uniform=a.Colors.Length>0;foreach(byte c in a.Colors)uniform &= c==a.Colors[0];
   return uniform && b.Colors.Length>0 && a.Colors[0]!=b.Colors[0];
  }
  internal static RuntimeRow[] Wrap(RuntimeRow[] source,int width,int capacity,bool nativeGrid=false)
  {
   if(source.Length==0)return source;
   var text=new StringBuilder();var colors=new List<byte>();var controls=new List<byte>();
   var hard=new HashSet<int>();var old=new HashSet<int>();
   for(int r=0;r<source.Length;r++)
   {
    var row=source[r];
    if(row.Text.Length!=row.Colors.Length || row.Text.Length!=row.Controls.Length)throw new ArgumentException("Mismatched layout planes");
    // Empty authored rows and explicitly spaced cards keep their exact slots.
    string jp=row.SourceText??"";
    if(String.IsNullOrWhiteSpace(jp) || jp.Length>0 && Char.IsWhiteSpace(jp[0]) ||
       System.Text.RegularExpressions.Regex.IsMatch(jp,@"^[^\s　](?:　+[^\s　]){2,}　*$"))return source;
    if(r>0){old.Add(text.Length);if(Hard(source[r-1],row))hard.Add(text.Length);}
    for(int i=0;i<row.Text.Length;i++)
    {
     text.Append(row.Text[i]);colors.Add(row.Colors[i]);controls.Add(row.Controls[i]);
     if(row.Controls[i]!=0 && row.Controls[i]!=47)hard.Add(text.Length);
    }
   }
   string value=text.ToString(),mask;
   if(!DirectLexicon.Masks.TryGetValue(value,out mask))throw new InvalidOperationException("Unsegmented dialogue text");
   int n=value.Length,max=Math.Max(source.Length,capacity);
   int mixedGap=GridGap(nativeGrid);
   var pixels=new int[n+1];for(int i=0;i<n;i++)pixels[i+1]=pixels[i]+Advance(value,i,nativeGrid)+(i>0 && Gap(value[i-1],value[i])?mixedGap:0);
   var cost=new double[n+1,max+1];var next=new int[n+1,max+1];
   for(int i=0;i<=n;i++)for(int r=0;r<=max;r++)cost[i,r]=Double.PositiveInfinity;
   for(int r=0;r<=max;r++)cost[n,r]=0;
   for(int r=1;r<=max;r++)for(int start=n-1;start>=0;start--)
   {
    int leadingGap=start>0 && Gap(value[start-1],value[start])?mixedGap:0;
    for(int end=start+1;end<=n && pixels[end]-pixels[start]-leadingGap<=width;end++)
    {
     if(end>start+1 && hard.Contains(end-1))break;
     if(end<n && !hard.Contains(end) && (Close.IndexOf(value[end])>=0 || Open.IndexOf(value[end-1])>=0))continue;
     if(Double.IsPositiveInfinity(cost[end,r-1]))continue;
     double spare=width-(pixels[end]-pixels[start]-leadingGap);
     double penalty=2000+spare*spare/(nativeGrid?144.0:289.0)+(end<n && mask[end]=='1' && !hard.Contains(end)?1e12:0);
     double candidate=cost[end,r-1]+penalty;
     if(candidate<cost[start,r]){cost[start,r]=candidate;next[start,r]=end;}
    }
   }
   // Hard boundaries/vertical reservations win over typography. Never manufacture
   // a click or grow an authored box when constraints cannot be satisfied.
   if(Double.IsPositiveInfinity(cost[0,max]))return source;
   bool slash=controls.Contains(47);
   var result=new List<RuntimeRow>();int pos=0,remaining=max;
   while(pos<n)
   {
    int end=next[pos,remaining--],length=end-pos;
    var cs=colors.GetRange(pos,length).ToArray();var events=controls.GetRange(pos,length).ToArray();
    for(int i=0;i<events.Length;i++)if(events[i]==47)events[i]=0;
    if(slash && end<n && events[length-1]==0)events[length-1]=47;
    if(end==n && controls[n-1]==47)events[length-1]=47;
    result.Add(new RuntimeRow{Text=value.Substring(pos,length),SourceText=String.Join("",Array.ConvertAll(source,r=>r.SourceText)),Colors=cs,Controls=events,RubyJson="{}"});pos=end;
   }
   return result.ToArray();
  }
 }
}
