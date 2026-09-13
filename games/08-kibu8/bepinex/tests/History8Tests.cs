using System;
using KibukawaHistory;
public static class History8Tests
{
 static void Check(bool b,string message) { if(!b) throw new Exception(message); }
 public static void Main()
 {
  var history=new HistoryBuffer(2000);
  string[] rows={"中文色彩","次行","ABＣ"};sbyte[] counts={4,2,2};
  sbyte[][] colors={new sbyte[]{0,1,1,0},new sbyte[]{1,0},new sbyte[]{0,1}};int[] palette={0xffffff,0xff00aa};
  Gmode20050817HistoryCapture.Capture(history,rows,counts,colors,palette,2);
  Check(history.Entries.Count==1 && history.Entries[0]=="中文色彩\n次行","Buffered executed rows");
  Check(history.Colors[0][1]==0xff00aa && history.Colors[0][5]==0xff00aa,"Captured palette");
  rows[0]="变更";palette[1]=0;Check(history.Entries[0].StartsWith("中文") && history.Colors[0][1]==0xff00aa,"Snapshots must be immutable");
  Gmode20050817HistoryCapture.Capture(history,new[]{rows[2]},new sbyte[]{2},new[]{colors[2]},palette,1);
  Check(history.Entries.Count==2 && history.Entries[1]=="ABＣ" && history.Colors[1].Count==3,"Fallback halfwidth pair maps one palette slot");
  var hint=new SoftKeyHintState();Check(hint.Render("",true,"")==LeftSoftKeyHint.Caption,"Empty native idle hint");
  Check(hint.Render(LeftSoftKeyHint.Caption,false,null)=="","Restore empty native hint");
  Check(hint.Render("戻る",true,"")=="戻る","Do not replace native return");
  Check(hint.Render("",true,null)=="","Unsupported canvas hint");
  var input=new LeftSoftKeyInput();Check(input.Pressed(1,21)&&!input.Pressed(1,21),"Softkey edge");input.Pressed(2,21);Check(input.Pressed(1,21),"Softkey release");
  var shown=new HistoryBuffer(2000);var tracker=new DrawnHistoryTracker();tracker.Begin();
  Check(shown.Entries.Count==0,"Starting a multi-click block must not reveal buffered rows");
  tracker.Draw(shown,0,0,'首',0xabcdef,"布雷特",0x123456);
  Check(shown.Entries[0]=="布雷特\n首","Only actually drawn first character and current speaker");
  tracker.Draw(shown,0,0,'首',0x000000,"布雷特",0);
  Check(shown.Entries[0]=="布雷特\n首" && shown.Colors[0][4]==0xabcdef,"Redraw deduplication and RGB snapshot");
  tracker.Draw(shown,0,1,'句',0xff0000,"布雷特",0);
  Check(shown.Entries[0]=="布雷特\n首句","Later click row must remain absent until drawn");
  tracker.Draw(shown,1,0,'后',0x00ff00,null,0);
  Check(shown.Entries[0]=="布雷特\n首句后","Later row appears only after actual draw");
  tracker.Begin();Check(shown.Entries.Count==1,"Empty new block adds nothing");
  tracker.Draw(shown,0,0,'首',0xffffff,null,0);
  Check(shown.Entries.Count==2 && shown.Entries[1]=="首","New block resets position deduplication");
  var wrapped=new HistoryBuffer(2000);var replay=new DrawnHistoryTracker();replay.Begin();
  string[] screenRows={"我们考虑到凶器可能被扔","掉，把附近找了个遍……"};
  for(int r=0;r<screenRows.Length;r++)
   for(int c=0;c<screenRows[r].Length;c++) replay.Draw(wrapped,r,c,screenRows[r][c],0xffffff,"刑警",0x00bfff);
  Check(wrapped.Entries[0]=="刑警\n我们考虑到凶器可能被扔掉，把附近找了个遍……","History must not inherit narrow dialogue wrapping");
  Check(wrapped.Colors[0].Count==wrapped.Entries[0].Length,"Joined history color offsets");
  replay.Begin();replay.Draw(wrapped,0,0,'但',0xffffff,"刑警",0x00bfff);
  Check(wrapped.Entries.Count==2 && wrapped.Entries[1]=="刑警\n但","Keep native click boundaries even for same speaker");
  var chat=new HistoryBuffer(2000);var chatTracker=new DrawnHistoryTracker();chatTracker.Begin();
  string[] chatRows={"莉绪：说明", "结束。", "伊库鲁米：明白。", "伊库鲁米：还有呢？"};
  for(int r=0;r<chatRows.Length;r++) {
   for(int c=0;c<chatRows[r].Length;c++)
    chatTracker.Draw(chat,r,c,chatRows[r][c],r+1,null,0,0,c==chatRows[r].Length-1?(r==0?47:59):0);
   // Repainting a completed row cannot consume or duplicate its separator.
   chatTracker.Draw(chat,r,chatRows[r].Length-1,chatRows[r][chatRows[r].Length-1],99,null,0,0,59);
   Check(!chat.Entries[0].EndsWith("\n"),"Do not disclose pending next speech before it is drawn");
  }
  Check(chat.Entries[0]=="莉绪：说明结束。\n伊库鲁米：明白。\n伊库鲁米：还有呢？","MO click segments must start new history lines, including repeated speakers");
  Check(chat.Colors[0].Count==chat.Entries[0].Length,"MO history separator color alignment");
  var notebook=new HistoryBuffer(2000);var noteTracker=new DrawnHistoryTracker();noteTracker.Begin();
  noteTracker.Draw(notebook,0,0,'鹭',0xffffff,null,0,17);
  noteTracker.Draw(notebook,1,0,'岁',0xffffff,null,0,17);
  Check(notebook.Entries.Count==0 && !noteTracker.Seen(0,0),"Notebook must not enter history or consume dialogue positions");
  noteTracker.Draw(notebook,0,0,'续',0xffffff,null,0,0);
  Check(notebook.Entries.Count==1 && notebook.Entries[0]=="续","Dialogue capture resumes after notebook");
  Console.WriteLine("PASS: Kibu8 executed buffer snapshot, RGB immutability, row boundaries, halfwidth fallback, native empty L hint and input edges");
  Console.WriteLine("PASS: draw-only disclosure, multi-click block gating, per-position redraw dedupe, speaker, RGB snapshot and block reset");
 }
}
