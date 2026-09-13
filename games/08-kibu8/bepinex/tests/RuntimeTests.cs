using System;
using System.IO;
using System.Reflection;
using System.Text;
using System.Collections.Generic;
using Kibukawa8.Runtime;

// Plain CLR objects only: no real CanvasEx constructor or Unity runtime.
public class RuntimeCanvasStub
{
 public sbyte[] Script;
 public int Pos, NowStockingGyou, MojiHani_yoko;
 public static int FWidth=6, Width=240, FAscent=12, FDocomo=0;
 public string[] Sentaku_nafuda;
 public void SetColor(object g,int color) { }
 public int MainTask, ListPos; public string Command_taisyoumei="调查";
 public int SpeakerPaints, SpeakerY;
 public void DrawAdvNafuda(object g,int x,int y) { SpeakerPaints++;SpeakerY=y; }
 public int MojiHani_tate, Moji_y=168, NowNamae=-1; public static int FHeight=12;
 public int PrintDanYoyaku, ScrollDan; public bool Resumed;
 public sbyte BunsyouGun_gyousuu, BunsyouGun_max_mojisuu;
 public string[] bg_itigyougun_mojiretu=new string[40], rollitigyougun_mojiretu=new string[150];
 public sbyte[] bg_itigyougun_zenkakusuu=new sbyte[40], bg_itigyougun_rubisuu=new sbyte[40], rollitigyougun_zenkakusuu=new sbyte[150], rollitigyougun_rubisuu=new sbyte[150];
 public sbyte[][] bg_itigyougun_color=new sbyte[40][], bg_itigyougun_control=new sbyte[40][], rollitigyougun_color=new sbyte[150][];
 public int[][] bg_itigyougun_rubi_index=new int[40][], rollitigyougun_rubi_index=new int[150][];
 public string info_struct_moji;
 public int info_struct_zenkaku_suu;
 public sbyte[] info_struct_mojiretu=new sbyte[100], info_struct_iro=new sbyte[50];
}
public class RuntimeGraphicsStub {
 public List<int> X=new List<int>();
 public void DrawString(string text,int x,int y) {
  var scope=typeof(Kibukawa.Engine.Gmode20050817.CanvasRuntime).GetMethod("ScopedSmallFont",BindingFlags.Static|BindingFlags.NonPublic);
  if(scope.Invoke(null,null)==null) throw new Exception("Choice must draw using the 12px small font");
  X.Add(x);
 }
 public UnityEngine.Vector2 drawOrigin; public int ClipHeight; public void SetClip(int x,int y,int w,int h) { ClipHeight=h; } }
public class RuntimeInfoCoroutineStub { public RuntimeCanvasStub Owner; }
public static class RuntimeTests
{
 static Type P=typeof(Kibukawa.Engine.Gmode20050817.CanvasRuntime);
 static BindingFlags Flags=BindingFlags.Static|BindingFlags.NonPublic;
 static object Call(string name,params object[] args) { return P.GetMethod(name,Flags).Invoke(null,args); }
 static void Set(string field,object value) { P.GetField(field,Flags).SetValue(null,value); }
 static void Check(bool ok,string error) { if(!ok) throw new Exception(error); }
 static sbyte[] Signed(byte[] b) { sbyte[] s=new sbyte[b.Length];Buffer.BlockCopy(b,0,s,0,b.Length);return s; }
 public static string Run(string gamePath)
 {
  foreach(string source in new[]{"关键词。","「关键词」","“关键词”"}) {
   var row=new RuntimeRow {SourceText=source,Text="“关键词。”",Colors=new byte[]{2,2,2,2,0,0},Controls=new byte[]{0,0,0,0,0,46}};
   var block=new DisplayTranslation {Rows=new[]{row}};block.NormalizeAddedQuoteColors();
   if(row.Colors[0]!=(source=="关键词。"?0:2) || row.Colors[1]!=2 || row.Controls[5]!=46 || row.Text!="“关键词。”")throw new Exception("Added quote color/source preservation");
  }
  var quoteRows=new[]{new RuntimeRow {SourceText="「引用",Text="“‘引用",Colors=new byte[]{2,2,2,2},Controls=new byte[4]},new RuntimeRow {SourceText="文」",Text="文’”",Colors=new byte[]{2,2,2},Controls=new byte[]{0,0,46}}};
  new DisplayTranslation {Rows=quoteRows}.NormalizeAddedQuoteColors();
  if(quoteRows[0].Colors[0]!=0 || quoteRows[0].Colors[1]!=2 || quoteRows[1].Colors[1]!=2 || quoteRows[1].Colors[2]!=0 || quoteRows[1].Controls[2]!=46)throw new Exception("Outer quotes across rows, keep inner quotation and control");
  NativeDialogueLayoutTests.Run();
  var smallAtlas = new Kibu1ZhCN.BitmapFontAtlas("test");
  Set("smallFont", smallAtlas);
  Check(Call("ScopedSmallFont") == null, "Ordinary dialogue must use Unifont");
  object[] outer = { false }; Call("BeforeSmallFontPage", outer);
  Check(ReferenceEquals(Call("ScopedSmallFont"), smallAtlas), "Settings/loading must use native small-font");
  object[] inner = { false }; Call("BeforeSmallFontPage", inner);
  Call("RestoreSmallFontPage", inner[0]);
  Check(ReferenceEquals(Call("ScopedSmallFont"), smallAtlas), "Nested drawing must preserve page scope");
  Call("RestoreSmallFontPage", outer[0]);
  Check(Call("ScopedSmallFont") == null, "Page exit/finalizer must restore Unifont");
  var reference=new Dictionary<string,string>();
  foreach(string line in File.ReadAllLines(Path.Combine(gamePath,"reports/runtime-row-reference.tsv")))
  {
   string[] parts=line.Split('\t');Check(parts.Length==4,"Invalid row reference");
   reference.Add(parts[0]+":"+parts[1]+":"+parts[2],parts[3]);
  }
  RuntimePack pack=RuntimePack.Load(Path.Combine(gamePath,"bepinex/build/plugin/translations.bin"),ScriptIdentityData.Names);
  Set("pack",pack);Set("canvasType",typeof(RuntimeCanvasStub));Set("ready",true);Set("instance",new Kibu8ZhCN.Plugin());
  var choiceCanvas=new RuntimeCanvasStub { Sentaku_nafuda=new[]{"从１２楼被害者家中的阳台"} };
  var choiceGraphics=new RuntimeGraphicsStub();
  Check(!(bool)Call("BeforeChoiceCenter",choiceCanvas,choiceGraphics,0,20,7),"Centered mixed choice must use proportional positions");
  Check(choiceGraphics.X.Count==60,"Choice must retain all glyphs and five outline/foreground passes");
  Check(choiceGraphics.X[2]-choiceGraphics.X[1]==7,"Choice 12 must advance 7px");
  Check(choiceGraphics.X[1]-choiceGraphics.X[0]==19 && choiceGraphics.X[3]-choiceGraphics.X[2]==13,"Choice must have spaces on both numeric boundaries");
  Check(choiceGraphics.X[48]==42,"Choice centered using actual 156px width");
  Check(Call("ScopedSmallFont")==null,"Choice must restore font scope after drawing");
  choiceGraphics.X.Clear();
  Check(!(bool)Call("BeforeChoiceLeft",choiceCanvas,choiceGraphics,0,10,20,7),"Left choice must also use boundary spacing");
  Check(choiceGraphics.X[48]==10,"Left choice must preserve origin");
  var ageCanvas=new RuntimeCanvasStub { MainTask=17, ListPos=0 };
  ageCanvas.bg_itigyougun_mojiretu[1]="２２岁";
  object[] ageScope={false};Call("BeforeSmallFontPage",ageScope);
  object[] firstDigit={ageCanvas,0,1,132,80,0f}, secondDigit={ageCanvas,1,1,145,80,0f};
  Call("BeforeAdvDraw",firstDigit);Call("BeforeAdvDraw",secondDigit);
  Check((int)secondDigit[3]-(int)firstDigit[3]==7,"Notebook 22 must advance 7px between digits; actual="+((int)secondDigit[3]-(int)firstDigit[3]));
  Check((int)firstDigit[4]==78,"Age must retain its 2px upward adjustment");
  Call("RestoreSmallFontPage",ageScope[0]);
  string[] jobs={"・调查官　　　・学生","・刑警　　　　・记者","・侦探　　　　・自由职业者"};
  float column=-1;
  foreach(string job in jobs) {
   float x=(float)Call("RowAdvance",job,job.IndexOf('・',1),17f,220f);
   if(column<0)column=x;
   Check(x==column,"Two-column occupation bullets must align; actual="+x+", expected="+column);
  }
  Set("infoOwner",typeof(RuntimeInfoCoroutineStub).GetField("Owner"));
  Set("drawOrigin",typeof(RuntimeGraphicsStub).GetField("drawOrigin"));
  Set("exactUi", Kibu8ZhCN.UiLocalizationData.Exact);
  object[] menuScope={new RuntimeCanvasStub(),null};Call("BeforeMenuTitle",menuScope);
  Check(ReferenceEquals(Call("FontForDraw",(object)"调查".ToCharArray()),smallAtlas),"Menu title must use native small-font");
  Check(Call("FontForDraw",(object)"旧对白".ToCharArray())==null,"Menu title scope leaked to background dialogue");
  Call("RestoreMenuTitle",menuScope[1]);
  Check(Call("FontForDraw",(object)"调查".ToCharArray())==null,"Menu title scope not restored");
  // Ds_sub splits its input into single glyphs for both shadow and foreground.
  // The whole-string hook must translate before that split and centering.
  object[] loadingArgs = new object[] { "データ確認中…" };
  MethodInfo loadingHook = P.GetMethod("BeforeShadowString", Flags);
  Check(loadingHook != null, "Missing pre-split Ds_sub localization hook");
  loadingHook.Invoke(null, loadingArgs);
  Check((string)loadingArgs[0] == "正在检查数据……", "Loading status remains Japanese before glyph splitting");
  object[] unknownArgs = new object[] { "unmapped player text" };
  loadingHook.Invoke(null, unknownArgs);
  Check((string)unknownArgs[0] == "unmapped player text", "Unknown display text changed");
  Dictionary<string,RuntimeRow> infos=(Dictionary<string,RuntimeRow>)P.GetField("infoRows",Flags).GetValue(null);
  var yearCanvas=new RuntimeCanvasStub {info_struct_moji="year-spacing-test"};
  infos[yearCanvas.info_struct_moji]=new RuntimeRow {Text="２００３年",Colors=new byte[5],Controls=new byte[5]};
  object[] yearState={new RuntimeInfoCoroutineStub {Owner=yearCanvas},null};Call("BeforeInfo",yearState);
  var yearInfo=(Kibukawa.Engine.Gmode20050817.CanvasRuntime.InfoState)yearState[1];
  Check(yearInfo.Positions[1]-yearInfo.Positions[0]==7,"INFO must not space digits within a number");
  Check(yearInfo.Positions[4]-yearInfo.Positions[3]==13,"INFO needs a 6px blank between 2003 and 年");
  Call("RestoreInfo",yearState[1]);infos.Remove("year-spacing-test");
  var transition=new RuntimeCanvasStub();
  foreach(string scenario in new[]{"c1-02","c1-03"}) {
   byte[] rawTransition=File.ReadAllBytes(Path.Combine(gamePath,"raw/scratch3_1.dat/"+scenario+".bin"));
   int skip=17+2*(rawTransition[15]+rawTransition[16]*256);
   byte[] bodyTransition=new byte[rawTransition.Length-skip];Array.Copy(rawTransition,skip,bodyTransition,0,bodyTransition.Length);
   transition.Script=Signed(bodyTransition);Call("AfterLoad",transition);
  }
  transition.Pos=73;object[] welcome={transition,null};Call("BeforeDialogue",welcome);
  Check(welcome[1]!=null,"Native scenario transition must bind MO welcome without test prebinding");
  Call("AfterDialogue",transition,welcome[1]);
  Check(transition.bg_itigyougun_mojiretu[0].Contains("迷雾在线"),"MO welcome must display Chinese after scenario transition");
  int strings=0, displays=0, infoCount=0, rows=0, rollCount=0, scrollCount=0;
  Encoding sjis=Encoding.GetEncoding(932);
  foreach(string path in Directory.GetFiles(Path.Combine(gamePath,"raw"),"*.bin",SearchOption.AllDirectories))
  {
   byte[] raw=File.ReadAllBytes(path);int start=17+2*(raw[15]+raw[16]*256);
   byte[] body=new byte[raw.Length-start];Array.Copy(raw,start,body,0,body.Length);
   string hash=(string)Call("Hash",body);ScriptTranslation script=pack.Bind(body);Check(script!=null,"Loader hash mismatch: "+path);
   RuntimeCanvasStub canvas=new RuntimeCanvasStub {Script=Signed(body)};
   sbyte[] originalScript=canvas.Script;Call("AfterLoad",canvas);
   foreach(StringTranslation text in script.Strings.Values)
   {
    int end=text.Offset;while(body[end]!=0) ++end;
    string source=sjis.GetString(body,text.Offset,end-text.Offset);
    Check(source==text.Source,"StringRead offset/source mismatch");canvas.Pos=text.Offset;
    object[] before={canvas,0};Call("BeforeString",before);Check((int)before[1]==text.Offset,"Prefix position mismatch");
    canvas.Pos=end+1;object[] after={canvas,before[1],source};Call("AfterString",after);
    Check((string)after[2]==((text.Opcode==5||text.Opcode==8)?text.Target:source),"String persistence policy mismatch");
    Check(canvas.Pos==end+1,"String hook changed Pos");strings++;
   }
   foreach(DisplayTranslation display in script.Displays.Values)
   {
    Check(body[display.Offset]==display.Opcode,"Display opcode offset mismatch");
    for(int ri=0;ri<display.Rows.Length;ri++)
    {
     RuntimeRow expectedRow=display.Rows[ri];
     using(var stream=new MemoryStream())
     {
      byte[] utf8=Encoding.UTF8.GetBytes(expectedRow.Text);stream.Write(utf8,0,utf8.Length);stream.WriteByte(0);
      stream.Write(expectedRow.Colors,0,expectedRow.Colors.Length);stream.WriteByte(0);
      stream.Write(expectedRow.Controls,0,expectedRow.Controls.Length);
      string rowHash=(string)Call("Hash",stream.ToArray());
      Check(reference[hash+":"+display.Offset+":"+ri]==rowHash,"Original tagged-compiler row mismatch: "+path+":"+display.Offset+":"+ri);
     }
    }
    if(display.Opcode==72)
    {
     RuntimeRow row=display.Rows[0];int n=body[display.Offset+1];
     Check(sjis.GetString(body,display.Offset+2,n*2)==row.SourceText,"INFO source decode mismatch");
     RuntimeRow old;if(infos.TryGetValue(row.SourceText,out old)) Check(old.Text==row.Text,"Ambiguous INFO: "+row.SourceText+" => "+old.Text+" / "+row.Text);
     infos[row.SourceText]=row;canvas.info_struct_moji=row.SourceText;canvas.info_struct_zenkaku_suu=n;
     sbyte[] originalRaw=canvas.info_struct_mojiretu,originalColors=canvas.info_struct_iro;
     object[] state={new RuntimeInfoCoroutineStub {Owner=canvas},null};Call("BeforeInfo",state);
     Check(canvas.info_struct_moji==row.Text && canvas.info_struct_zenkaku_suu==row.Text.Length,"INFO substitution failed");
     Check(canvas.info_struct_iro.Length>=row.Text.Length,"INFO capacity");
     if(row.Text.Length>=2 && row.Text.Length<=13) {
      int originalStart=238-row.Text.Length*12;
      Call("BeforeDraw",new RuntimeGraphicsStub(),new[]{row.Text[0]},originalStart,8);
      int left=Kibu1ZhCN.LegacyFontRenderer.X;
      Call("BeforeDraw",new RuntimeGraphicsStub(),new[]{row.Text[1]},originalStart+12,8);
      Check(Kibu1ZhCN.LegacyFontRenderer.X-left==(Kibukawa.Engine.Gmode20050817.LatinMetrics.Narrow(row.Text[0])?7:13),"INFO 12px glyphs must advance 13px");
     }
     var infoState=(Kibukawa.Engine.Gmode20050817.CanvasRuntime.InfoState)state[1];
     Check(infoState.Width<=236,"INFO must fit the 236px header at native pixel size");
     for(int i=0;i<row.Text.Length;i++) {
      Call("BeforeDraw",new RuntimeGraphicsStub(),new[]{row.Text[i]},238-row.Text.Length*12+i*12,8);
      int x=Kibu1ZhCN.LegacyFontRenderer.X;
      Check(x>=2 && x+(row.Text[i]=='\u3000'?6:12)<=238,"INFO ink cropped at horizontal edge");
      Check(Kibu1ZhCN.LegacyFontRenderer.Scale==1f,"INFO must not horizontally resample pixels");
      Check(Kibu1ZhCN.LegacyFontRenderer.Y==11 && ReferenceEquals(Kibu1ZhCN.LegacyFontRenderer.Small,smallAtlas),"INFO must use native native small-font with baseline 11");
     }
     var infoGraphics=new RuntimeGraphicsStub();
     object[] clip={infoGraphics,0,0,240,14};Call("BeforeInfoClip",clip);
     Check((int)clip[4]==16,"INFO transition clip must contain native native small-font descenders");
     Call("RestoreInfo",state[1]);Check(infoGraphics.ClipHeight==14,"INFO transition clip must restore after coroutine step");Check(canvas.info_struct_moji==row.SourceText && canvas.info_struct_zenkaku_suu==n,"INFO restore failed");
     Check(ReferenceEquals(originalRaw,canvas.info_struct_mojiretu)&&ReferenceEquals(originalColors,canvas.info_struct_iro),"INFO original arrays not restored");infoCount++;
    }
    else if(display.Opcode==75 || display.Opcode==120)
    {
     VerifyRoll(canvas,display);
     if(display.Opcode==75) rollCount++; else scrollCount++;
    }
    else if(display.Opcode==255)
    {
     if(path.IndexOf("sousamemo",StringComparison.OrdinalIgnoreCase)>=0) {
      canvas.MainTask=17;
      RuntimeRow[] notebook=(RuntimeRow[])Call("PrepareDialogueRows",canvas,display.Rows);
      Check(notebook.Length==display.Rows.Length,"Notebook must retain field and line boundaries");
      for(int memoRow=0;memoRow<notebook.Length;memoRow++) {
       string expected=System.Text.RegularExpressions.Regex.Replace(display.Rows[memoRow].Text,
        @"(?<=[\u3400-\u9fff])(?=[A-Za-z0-9Ａ-Ｚａ-ｚ０-９])|(?<=[A-Za-z0-9Ａ-Ｚａ-ｚ０-９])(?=[\u3400-\u9fff])","　");
       int width=0;foreach(char c in notebook[memoRow].Text) width+=Kibukawa.Engine.Gmode20050817.LatinMetrics.NotebookWidth(c,13);
       Check(notebook[memoRow].Text==expected && width<=208,"Notebook spacing incorrect or exceeds native page width");
      }
      canvas.MainTask=0;
     }
     canvas.Pos=display.Offset+1;object[] before={canvas,null};Call("BeforeDialogue",before);
     Check(before[1]!=null,"Dialogue capture offset mismatch");canvas.Pos=display.Offset+100;
     // Simulate native buffers before the postfix, including a dirty fade sentinel.
     for(int nativeRow=0;nativeRow<canvas.bg_itigyougun_mojiretu.Length;nativeRow++) canvas.bg_itigyougun_mojiretu[nativeRow]="「仮面の世界」";
     Call("AfterDialogue",canvas,before[1]);Check(canvas.Pos==display.Offset+100,"Dialogue hook moved Pos");
     if(display.Rows.Length>0 && display.Rows[0].Text.TrimStart().StartsWith("・")) {
      int oldMode=canvas.MojiHani_tate;canvas.MojiHani_tate=1;
      object[] listPosition={canvas,0,0,0,8,0f};Call("BeforeAdvDraw",listPosition);
      Check((int)listPosition[3]==10,"Progressive list must keep fixed x across fade stages");
      Check((int)listPosition[4]==24,"Progressive list must start below INFO header");
      canvas.MojiHani_tate=oldMode;
     }
     RuntimeRow[] layout=(RuntimeRow[])Call("PrepareDialogueRows",canvas,display.Rows);
     Check(canvas.BunsyouGun_gyousuu==layout.Length,"Row count mismatch");
     Check(canvas.bg_itigyougun_mojiretu[layout.Length]==String.Empty,"Native fade loop reads row <= count: stale Japanese sentinel must be cleared");
     for(int retired=layout.Length;retired<canvas.bg_itigyougun_mojiretu.Length;retired++) {
      Check(canvas.bg_itigyougun_mojiretu[retired]==String.Empty && canvas.bg_itigyougun_zenkakusuu[retired]==0 && canvas.bg_itigyougun_rubisuu[retired]==0,"Retired fade row text/count/ruby must be empty");
      foreach(sbyte control in canvas.bg_itigyougun_control[retired]) Check(control==0,"Retired fade row must not retain controls");
      foreach(int ruby in canvas.bg_itigyougun_rubi_index[retired]) Check(ruby==-1,"Retired fade row must not draw Japanese ruby");
     }
     if(layout.Length>4 && layout.Length!=display.Rows.Length) {
      int savedPos=canvas.Pos;canvas.PrintDanYoyaku=4;canvas.ScrollDan=0;canvas.Resumed=false;
      Call("BeforeDialogueViewport",canvas);
      Check(canvas.ScrollDan==0 && !canvas.Resumed,"Five body rows must fit without scrolling");
      Check(canvas.Pos==savedPos && canvas.PrintDanYoyaku==4,"Viewport must not advance script or reveal cursor");
      foreach(int verticalMode in new[]{1,2}) {
       canvas.MojiHani_tate=verticalMode;canvas.NowNamae=0;
       canvas.PrintDanYoyaku=canvas.BunsyouGun_gyousuu-1;canvas.ScrollDan=0;canvas.Resumed=false;
       Call("BeforeDialogueViewport",canvas);
       Check(canvas.ScrollDan==0 && !canvas.Resumed,"Full-screen text must not use the five-row dialogue scroll limit");
      }
      canvas.MojiHani_tate=0;
      canvas.NowNamae=0;canvas.PrintDanYoyaku=4;canvas.ScrollDan=0;canvas.Resumed=false;
      Call("BeforeDialogueViewport",canvas);
      Check(canvas.ScrollDan==1 && canvas.Resumed,"Named dialogue must scroll before fifth body row exceeds viewport");
      object[] draw={canvas,0,4,0,-999,0f};Call("BeforeAdvDraw",draw);
      Check((int)draw[4]==208,"Scrolled named row must retain native vertical baseline");
      object[] speaker={canvas,10,-999};Call("BeforeSpeaker",speaker);
      Check((int)speaker[2]==136,"Speaker must occupy first row");
      int painted=canvas.SpeakerPaints;Call("AfterDialoguePaint",canvas,new object());
      Check(canvas.SpeakerPaints==painted+1 && canvas.SpeakerY==136,"Speaker must survive body scroll");
      for(int line=1;line<=4;line++) {
       object[] position={canvas,0,line,0,-999,0f};Call("BeforeAdvDraw",position);
       Check((int)position[4]==154+(line-1)*18 && (int)position[4]+16<=226,"Five-row layout exceeds text frame");
      }
      foreach(int task in new[]{4,5,16,17,18,11,12}) {
       canvas.MainTask=task;canvas.Resumed=false;int scroll=canvas.ScrollDan;
       Call("BeforeDialogueViewport",canvas);
       Check(canvas.ScrollDan==scroll && !canvas.Resumed,"Menu viewport changed");
       object[] menuDraw={canvas,0,1,77,99,0f};Call("BeforeAdvDraw",menuDraw);
       Check((int)menuDraw[3]==77 && (int)menuDraw[4]==99,"Dialogue coordinates must not alter menus");
       int count=canvas.SpeakerPaints;Call("AfterDialoguePaint",canvas,new object());
       Check(canvas.SpeakerPaints==count,"Stale speaker painted on menu");
      }
      canvas.MainTask=0;
      canvas.NowNamae=-1;
      canvas.PrintDanYoyaku=0;canvas.ScrollDan=0;canvas.Resumed=false;
     }
     for(int r=0;r<layout.Length;r++)
     {
      RuntimeRow row=layout[r];string actual=canvas.bg_itigyougun_mojiretu[r];
      for(int slot=0;slot<actual.Length;slot++) {
       object[] placement={canvas,slot,r,false,0};Call("FitDraw",placement);
       if(slot>0 && actual[slot-1]!='\u3000' && actual[slot-1]!=' ') {
        object[] previous={canvas,slot-1,r,false,0};Call("FitDraw",previous);
        Check((int)placement[4]-(int)previous[4]==(Kibukawa.Engine.Gmode20050817.LatinMetrics.Narrow(actual[slot-1])?9:17),"Uneven centered character advance: "+actual+" slot="+slot+" advance="+((int)placement[4]-(int)previous[4]));
       }
       Check((float)P.GetField("drawScale",Flags).GetValue(null)==1f,"Native pixel glyphs must never be horizontally scaled");
       if(actual[slot]!='\u3000' && actual[slot]!=' ') Check((int)placement[4]>=10 && (int)placement[4]+(Kibukawa.Engine.Gmode20050817.LatinMetrics.Narrow(actual[slot])?8:16)<=230,"Native glyph must stay inside dialogue width");
      }
      if(actual.Length>=2 && actual.Length<=12) {
       int oldAlign=canvas.MojiHani_yoko;canvas.MojiHani_yoko=3;
       object[] first={canvas,0,r,false,0}, second={canvas,1,r,false,0};
       Call("FitDraw",first);Call("FitDraw",second);
       Check((int)second[4]-(int)first[4]>=(Kibukawa.Engine.Gmode20050817.LatinMetrics.Narrow(actual[0]) || actual[0]=='　' || actual[0]==' ' ? 9:17),"Native glyph advance");
       canvas.MojiHani_yoko=oldAlign;
      }
      Check(actual.Length==canvas.bg_itigyougun_zenkakusuu[r],"Slot count mismatch");
      List<byte> expected=new List<byte>(),found=new List<byte>();
      foreach(byte c in row.Controls) if(c!=0) expected.Add(c);
      for(int i=0;i<actual.Length;i++) {
       Check(actual[i]>127 && !(actual[i]>=0xff61 && actual[i]<=0xff9f),"Halfwidth character violates native slot assumption");
       Check((byte)canvas.bg_itigyougun_color[r][i]==row.Colors[i],"Palette slot mismatch");
       if(canvas.bg_itigyougun_control[r][i]!=0) found.Add((byte)canvas.bg_itigyougun_control[r][i]);Check(canvas.bg_itigyougun_rubi_index[r][i]==-1,"Ruby not disabled");
      }
      Check(String.Join(",",expected)==String.Join(",",found),"Control sequence lost during notes/reflow");
      Check(canvas.bg_itigyougun_rubisuu[r]==0,"Ruby group count not disabled");rows++;
     }
     displays++;
    }
   }
   Check(ReferenceEquals(originalScript,canvas.Script),"Unexpected Script replacement");
   byte[] unchanged=new byte[canvas.Script.Length];Buffer.BlockCopy(canvas.Script,0,unchanged,0,unchanged.Length);
   Check((string)Call("Hash",unchanged)==hash,"Original Script bytes mutated");
  }
  VerifySyntheticRoll(pack);
  return String.Format("PASS: {0} StringRead offsets, {1} dialogue blocks/{2} rows, {3} INFO substitutions/restores, all 59 original loader hashes; real ROLL={4}, SCROLL={5}; synthetic ROLL/SCROLL growth, control overwrite/padding, row capture and state reset passed",strings,displays,rows,infoCount,rollCount,scrollCount);
 }
 static void VerifyRoll(RuntimeCanvasStub canvas,DisplayTranslation display)
 {
  canvas.NowStockingGyou=149;canvas.Pos=display.Offset+1;
  object[] capture={canvas,null};Call(display.Opcode==75?"BeforeRoll":"BeforeScroll",capture);
  Check(capture[1]!=null,"Roll opcode offset capture failed");
  canvas.NowStockingGyou=150;canvas.Pos=display.Offset+100;
  Call("AfterRoll",canvas,capture[1]);
  Check(canvas.Pos==display.Offset+100 && canvas.NowStockingGyou==150,"Roll postfix changed VM position/stock count");
  RuntimeRow row=display.Rows[0];
  Check(canvas.rollitigyougun_mojiretu[149]==row.Text,"Roll writes wrong captured row");
  Check(canvas.rollitigyougun_zenkakusuu[149]==row.Text.Length,"Roll slot count mismatch");
  Check(canvas.rollitigyougun_rubisuu[149]==0,"Roll ruby count not cleared");
  for(int i=0;i<row.Text.Length;i++) {
   Check((byte)canvas.rollitigyougun_color[149][i]==row.Colors[i],"Roll color mismatch");
   Check(canvas.rollitigyougun_rubi_index[149][i]==-1,"Roll ruby index not cleared");
   if(display.Opcode==120) Check((byte)canvas.bg_itigyougun_control[149][i]==row.Controls[i],"SCROLL writes wrong control plane");
  }
  object state=Call("State",canvas);
  HashSet<int> marked=(HashSet<int>)state.GetType().GetField("RollRows").GetValue(state);
  Check(marked.Contains(149),"Roll fitting state not marked");
 }
 static void VerifySyntheticRoll(RuntimePack pack)
 {
  byte[] body={75,120};string hash=(string)Call("Hash",body);
  RuntimeRow row=new RuntimeRow { SourceText="原文",Text=new string('中',40),Colors=new byte[40],Controls=new byte[40],RubyJson="{}" };
  for(int i=0;i<40;i++) row.Colors[i]=(byte)(i%4);
  ScriptTranslation translation=new ScriptTranslation();
  DisplayTranslation roll=new DisplayTranslation {Offset=0,Opcode=75,Rows=new[]{row}};
  DisplayTranslation scroll=new DisplayTranslation {Offset=1,Opcode=120,Rows=new[]{row}};
  translation.Displays.Add(0,roll);translation.Displays.Add(1,scroll);
  RuntimeCanvasStub canvas=new RuntimeCanvasStub {Script=Signed(body)};
  object syntheticState=Call("State",canvas);syntheticState.GetType().GetField("Translation").SetValue(syntheticState,translation);
  sbyte[] originalBgControls=new sbyte[23];originalBgControls[0]=59;canvas.bg_itigyougun_control[0]=originalBgControls;
  VerifyRoll(canvas,roll);
  Check(canvas.bg_itigyougun_control.Length==40 && ReferenceEquals(originalBgControls,canvas.bg_itigyougun_control[0]),"ROLL unexpectedly changed bg controls");
  row.Controls[10]=58;row.Controls[39]=46;VerifyRoll(canvas,scroll);
  Check(canvas.bg_itigyougun_control.Length==150 && canvas.bg_itigyougun_control[149].Length>=40,"SCROLL control array growth failed");
  RuntimeRow shortRow=new RuntimeRow {SourceText="短句",Text="短句",Colors=new byte[]{2,1},Controls=new byte[]{0,47},RubyJson="{}"};
  scroll.Rows=new[]{shortRow};VerifyRoll(canvas,scroll);
  for(int i=2;i<canvas.bg_itigyougun_control[149].Length;i++) Check(canvas.bg_itigyougun_control[149][i]==0,"Old SCROLL control leaked into padded tail");
  canvas.Script=Signed(body);Call("AfterLoad",canvas);
  object state=Call("State",canvas);
  Check(((HashSet<int>)state.GetType().GetField("RollRows").GetValue(state)).Count==0,"Scenario reload retained stale RollRows");
 }
}
