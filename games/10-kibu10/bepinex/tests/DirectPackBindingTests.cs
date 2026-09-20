using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using System.Text;
using Kibukawa8.Runtime;
using Kibukawa.Engine.Gmode20050817;
using Kibukawa.Engine.Gmode20050817Direct;
public static class DirectPackBindingTests
{
 static string Planes(RuntimeRow[] rows) {
  var result=new StringBuilder();foreach(var row in rows)for(int i=0;i<row.Text.Length;i++){
   result.Append(row.Text[i]);result.Append((char)(256+row.Colors[i]));result.Append((char)(512+(row.Controls[i]==47?0:row.Controls[i])));
  }return result.ToString();
 }
 public static string Run(string game,string original)
 {
  var assembly=Assembly.LoadFrom(original);
  var decoder=(Func<byte[],string>)Delegate.CreateDelegate(typeof(Func<byte[],string>),assembly.GetType("USEncoder.ToEncoding").GetMethod("ToUnicode",new[]{typeof(byte[])}));
  var pack=RuntimePack.Load(Path.Combine(game,"bepinex/build/plugin/translations.bin"),Kibu10ZhCN.ScriptIdentityData.Names,decoder);
  var audit=new List<string>();int changed=0,retained=0,overflow=0,protectedSplits=0;
  int count=0,displays=0,strings=0,reflowed=0,maxRows=0;var seen=new HashSet<ScriptTranslation>();
  foreach(string file in Directory.GetFiles(Path.Combine(game,"raw"),"*.bin",SearchOption.AllDirectories))
  {
   byte[] raw=File.ReadAllBytes(file);int skip=13+2*(raw[11]+raw[12]*256);
   byte[] body=new byte[raw.Length-skip];Array.Copy(raw,skip,body,0,body.Length);
   byte[] pristine=(byte[])body.Clone();
   var script=pack.Bind(body);
   if(script==null)throw new Exception("Unbound BIN: "+file);
   if(Path.GetFileName(file)=="help.bin")
   {
    DisplayTranslation help;
    if(!script.Displays.TryGetValue(164,out help) || help.Rows.Length!=5
        || help.Rows[0].Text!="本作《永劫会事件》" || help.Rows[2].Text!="最多可从四位角色的视角")
     throw new Exception("Help page body is not translated through the actual runtime script binding");
    var laidOutHelp=DirectTextLayout.Wrap(help.Rows,204,5,true);
    if(laidOutHelp.Length!=4 || laidOutHelp[3].Text!="展开游戏。")
     throw new Exception("Help page obsolete Japanese soft break was not merged");
    DisplayTranslation controls;
    if(!script.Displays.TryGetValue(2222,out controls))throw new Exception("Help controls page missing");
    var controlRows=DirectTextLayout.Wrap(controls.Rows,204,controls.Rows.Length,true);
    string controlText=String.Join("",Array.ConvertAll(controlRows,row=>row.Text));
    string visibleControlText=controlText.Replace('　',' ').Replace('Ｅ','E').Replace('Ｒ','R');
    if(!visibleControlText.Contains("键盘 E 键（或手柄 R 肩键）") || controlRows.Length>6)
     throw new Exception("PC/controller help wording or row capacity is invalid: rows="+controlRows.Length+" text="+controlText);
    foreach(var row in controlRows)if(DirectTextLayout.MeasureNative(row.Text,0,row.Text.Length)>204)
     throw new Exception("PC/controller help wording overflows the help page");
   }
   if(Path.GetFileName(file)=="append.bin" && script.Displays.ContainsKey(9454))
   {
    var clearRows=script.Displays[9454].Rows;
    if(clearRows.Length!=4 || clearRows[0].Text!="将把此前的所有数据清除" || clearRows[1].Text!="初始化，之后游戏将会" || clearRows[2].Text!="重新从头开始游戏。" || clearRows[3].Text!="是否确定要继续？")
     throw new Exception("Clear-save confirmation authored rows changed unexpectedly");
    string[] clearSource={"これまでのデータを全て","初期化して、ゲームを","最初から始めます。","よろしいですか？"};
    for(int i=0;i<clearRows.Length;i++)if(clearRows[i].Text.Length!=clearSource[i].Length)
     throw new Exception("Clear-save confirmation changed a native typewriter row length");
    for(int i=0;i<clearRows.Length-1;i++)foreach(byte control in clearRows[i].Controls)
     if(control!=0 && control!=47)throw new Exception("Clear-save confirmation gained an intermediate wait");
    if(clearRows[3].Controls[clearRows[3].Controls.Length-1]!=46)
     throw new Exception("Clear-save confirmation lost its terminal click");
   }
   foreach(var display in script.Displays.Values)
   {
    foreach(var row in display.Rows)
     if(row.Text.Length!=row.Colors.Length || row.Text.Length!=row.Controls.Length)throw new Exception("Row plane mismatch");
    if(display.Opcode==255 && !seen.Contains(script))
    {
     var rows=DirectTextLayout.Wrap(display.Rows,204,4);
     foreach(int availableWidth in new[]{204,220})foreach(int capacity in new[]{4,5}){
      var variant=DirectTextLayout.Wrap(display.Rows,availableWidth,capacity);
      if(variant.Length>Math.Max(display.Rows.Length,capacity) || Planes(variant)!=Planes(display.Rows))throw new Exception("Layout variant violated text/event planes or row reservation");
      if(capacity==5)foreach(var line in variant)
       if(DirectTextLayout.Measure(line.Text,0,line.Text.Length)>availableWidth)throw new Exception("Five-row layout overflow at "+display.Offset);
     }
     if(Object.ReferenceEquals(rows,display.Rows))retained++;else changed++;
     if(!Object.ReferenceEquals(rows,display.Rows))
     {
      string joined="";foreach(var originalRow in display.Rows)joined+=originalRow.Text;
      string mask;if(!DirectLexicon.Masks.TryGetValue(joined,out mask))throw new Exception("Missing lexical mask at "+display.Offset);
      var originalBreaks=new HashSet<int>();int originalPosition=0;
      for(int i=0;i<display.Rows.Length-1;i++){originalPosition+=display.Rows[i].Text.Length;originalBreaks.Add(originalPosition);}
      int outputPosition=0;
      for(int i=0;i<rows.Length-1;i++)
      {
       outputPosition+=rows[i].Text.Length;
       if(!originalBreaks.Contains(outputPosition) && outputPosition<mask.Length && mask[outputPosition]=='1')protectedSplits++;
      }
     }
     for(int ri=0;ri<rows.Length;ri++)if(DirectTextLayout.Measure(rows[ri].Text,0,rows[ri].Text.Length)>204){
      if(Path.GetFileName(file)!="s01.bin" || display.Offset!=21531)throw new Exception("New four-row pressure case needs its real speaker/box context verified");
      overflow++;audit.Add(Path.GetFileName(file)+"\t"+display.Offset+"\t"+ri+"\t"+rows[ri].SourceText+"\t"+rows[ri].Text);
     }
     if(rows.Length>Math.Max(display.Rows.Length,4))throw new Exception("Expanded vertical reservation");
     if(rows.Length>127)throw new Exception("Reflow VM row count overflow");
     var before=new StringBuilder();var after=new StringBuilder();
     var controls=new List<byte>();var afterControls=new List<byte>();
     foreach(var row in display.Rows)for(int i=0;i<row.Text.Length;i++)
     {
      before.Append(row.Text[i]);before.Append((char)(256+row.Colors[i]));before.Append((char)(512+(row.Controls[i]==47?0:row.Controls[i])));
      if(row.Controls[i]!=0 && row.Controls[i]!=47)controls.Add(row.Controls[i]);
     }
     foreach(var row in rows)
     {
      if(row.Text.Length>127 || row.Text.Length!=row.Colors.Length || row.Text.Length!=row.Controls.Length)throw new Exception("Reflow plane overflow/mismatch");
      for(int i=0;i<row.Text.Length;i++)
      {
       after.Append(row.Text[i]);after.Append((char)(256+row.Colors[i]));after.Append((char)(512+(row.Controls[i]==47?0:row.Controls[i])));
       if(row.Controls[i]!=0 && row.Controls[i]!=47)afterControls.Add(row.Controls[i]);
      }
     }
     if(before.ToString()!=after.ToString())throw new Exception("Reflow lost/changed text or per-glyph color at "+display.Offset);
     int next=0;foreach(byte control in afterControls)
     {
      if(next<controls.Count && control==controls[next])next++;
      else throw new Exception("Reflow control order changed or introduced a new click");
     }
     if(next!=controls.Count)throw new Exception("Reflow lost original controls");
     reflowed++;maxRows=Math.Max(maxRows,rows.Length);
    }
   }
   for(int i=0;i<body.Length;i++)if(body[i]!=pristine[i])throw new Exception("Original script mutated");
   seen.Add(script);
   count++;displays+=script.Displays.Count;strings+=script.Strings.Count;
  }
  File.WriteAllLines(Path.Combine(game,"reports/layout-four-row-pressure.tsv"),audit);
  Console.WriteLine("LAYOUT planned="+changed+" authored_or_retained="+retained+" five_row_narrator_case_rows="+overflow+" protected_new_splits="+protectedSplits+"; all five-row variants fit, all text/color/event anchors identical");
  // Four inactive raw copies are byte-identical to their canonical file BIN.
  if(count!=40 || pack.Scripts.Count!=36)throw new Exception("Expected 40 BINs / 36 canonical scripts, got "+count+" / "+pack.Scripts.Count);
  return "PASS: original game SJIS decoder binds "+count+" BINs; "+displays+" displays and "+strings+" strings; "+reflowed+" canonical dialogues reflowed (max "+maxRows+" rows), text/control order preserved, original bytes unchanged";
 }
}
