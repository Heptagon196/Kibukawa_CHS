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
