using System;
using System.Collections.Generic;
using Kibukawa8.Runtime;
using Kibukawa.Engine.Gmode20050817;
using Kibukawa.Engine.Gmode20050817Direct;

public class DirectCanvasStub
{
 public static Socotra.UI.StFont font=Socotra.UI.StFont.GetFont(656);
 public sbyte[] Script=new sbyte[]{1,2,3}; public int Pos=123,NowNamae=-1,MainTask,FrameTask=2;
 public bool NowRoll; public int Color; public int[] ColorTable={0,1,2,3,4};
 public int MojiHani_tate,MojiHani_yoko,PrintDanYoyaku;public bool Resumed;
 public static int FWidth=6;
 public string info_struct_moji="原文";
 public sbyte BunsyouGun_gyousuu,BunsyouGun_max_mojisuu;
 public string[] bg_itigyougun_mojiretu=new string[8];
 public sbyte[] bg_itigyougun_zenkakusuu=new sbyte[8],bg_itigyougun_rubisuu=new sbyte[8];
 public sbyte[][] bg_itigyougun_color=new sbyte[8][],bg_itigyougun_control=new sbyte[8][];
 public int[][] bg_itigyougun_rubi_index=new int[8][];
 public void SetColor(object g,int c) { Color=c; }
}
public class DirectGraphicsStub
{
 public UnityEngine.Vector2 drawOrigin; public string Drawn=""; public bool Throw;
 public List<int> Xs=new List<int>();
 public List<int> Fonts=new List<int>();
 public void SetFont(Socotra.UI.StFont font) { Fonts.Add(font.Id); }
 public void DrawString(string s,int x,int y) { if(Throw)throw new Exception("draw failure");Drawn+=s;Xs.Add(x); }
}
public class DirectHarness : DirectCanvasRuntime
{
 static void Check(bool v,string message){if(!v)throw new Exception(message);}
 static RuntimeRow Row(string text,string source=null,byte terminal=0) {
  var row=new RuntimeRow{Text=text,SourceText=source??text,Colors=new byte[text.Length],Controls=new byte[text.Length],RubyJson="{}"};
  if(text.Length>0)row.Controls[text.Length-1]=terminal;return row;
 }
 static void Segment(RuntimeRow[] rows,string mask=null) {
  string text=String.Join("",Array.ConvertAll(rows,r=>r.Text));DirectLexicon.Masks[text]=mask??new string('0',text.Length+1);
 }
 static void LayoutChecks() {
  Check(DirectTextLayout.Measure("中文ABC测试",0,7)==113 && DirectTextLayout.Position("中文ABC测试",2)==43 && DirectTextLayout.Position("中文ABC测试",5)==79,"Visual Latin gaps must be counted and drawn identically without adding characters");
  var source=new[]{Row("调查工藤"),Row("贵树的证词",terminal:46)};
  var mask=new char[10];for(int i=0;i<mask.Length;i++)mask[i]='0';for(int i=3;i<6;i++)mask[i]='1';Segment(source,new string(mask));
  var result=DirectTextLayout.Wrap(source,68,4);
  Check(Array.Exists(result,r=>r.Text.Contains("工藤贵树")),"Names across old soft rows must remain intact");
  Check(String.Join("",Array.ConvertAll(result,r=>r.Text))=="调查工藤贵树的证词","No text or spaces may be invented");
  source=new[]{Row("工藤贵树")};Segment(source,"01110");result=DirectTextLayout.Wrap(source,34,2);
  Check(result.Length==2,"Protected words may split only when box dimensions require it");
  source=new[]{Row("已经结束。","終わった。"),Row("继续调查","続ける")};Segment(source);result=DirectTextLayout.Wrap(source,204,4);
  Check(result.Length==2 && result[0].Text=="已经结束。","Completed authored sentence breaks must survive");
  source=new[]{Row("先看这里","ここだ"),Row("……再看那里","…次だ")};Segment(source);result=DirectTextLayout.Wrap(source,204,4);
  Check(result.Length==2 && result[1].Text.StartsWith("……"),"Authored leading ellipsis and its exact count must survive");
  source=new[]{Row("中文ABC测试",terminal:59),Row("另一段",terminal:46)};Segment(source);result=DirectTextLayout.Wrap(source,204,4);
  Check(result.Length==2 && result[0].Controls[result[0].Text.Length-1]==59 && result[1].Controls[result[1].Text.Length-1]==46,"Wait events must stay bound to the same text");
  source=new[]{Row("标题","　見出し"),Row("下一行","次の行")};Segment(source);result=DirectTextLayout.Wrap(source,204,4);
  Check(Object.ReferenceEquals(result,source),"Source indentation must prevent merging even when translation is shorter");
 }
 public static string Run()
 {
  canvasType=typeof(DirectCanvasStub);fields.Clear();ready=true;
  LayoutChecks();
  layout=new RuntimeLayout(12,5,18,32,17,11,13,6,new string[0]);
  exactUi=new Dictionary<string,string>{{"音量設定","音量设置"},{"ゲームのロード","读取存档"},{"シナリオ選択に戻る","返回章节选择"},{"タイトルに戻る","返回标题画面"},{"ゲームを続ける","继续游戏"}};
  foreach(var pair in exactUi){string label=pair.Key;BeforeShadowString(ref label);Check(label==pair.Value,"DocomoString menu label translation failed: "+pair.Key);}
  var c=new DirectCanvasStub();var bytes=c.Script;
  font=new Kibu1ZhCN.BitmapFontAtlas("body16");smallFont=new Kibu1ZhCN.BitmapFontAtlas("ui12");
  drawOrigin=typeof(DirectGraphicsStub).GetField("drawOrigin");
  BeforeDraw(new DirectGraphicsStub(),new[]{'项'},0,0);
  Check(Object.ReferenceEquals(Kibu1ZhCN.LegacyFontRenderer.Primary,font)&&Object.ReferenceEquals(Kibu1ZhCN.LegacyFontRenderer.Small,smallFont),"Non-body drawing must offer native 16px and 12px atlases, not force the 12px atlas");
  var translation=new ScriptTranslation();
  translation.Strings.Add(123,new StringTranslation{Opcode=73,Source="日本語",Target="中文副标题"});
  var state=states.GetValue(c,key=>new CanvasState());state.Script=bytes;state.Translation=translation;
  string value="日本語";int offset;BeforeDirectString(c,out offset);AfterDirectString(c,offset,ref value);
  Check(value=="中文副标题" && c.Pos==123 && Object.ReferenceEquals(bytes,c.Script),"Subtitle must preserve offsets and original bytes");
  translation.Strings.Add(124,new StringTranslation{Opcode=8,Source="話す",Target="交谈"});
  c.Pos=124;value="話す";BeforeDirectString(c,out offset);AfterDirectString(c,offset,ref value);
  Check(value=="交谈" && c.Pos==124,"Scenario option must bind translated text without changing script offsets");c.Pos=123;
  var row=new RuntimeRow{SourceText="原文",Text="中文A",Colors=new byte[]{0,2,3},Controls=new byte[]{0,0,46}};
  infoRows.Clear();infoRows.Add("原文",row);var g=new DirectGraphicsStub();
  Check(!DrawDirectInfo(c,g)&&g.Drawn=="中文A"&&!smallFontScope,"INFO must draw lone ASCII safely and restore font scope");
  Check(c.info_struct_moji=="原文" && c.Color==3,"INFO original text and palette");
  g.Throw=true;try{DrawDirectInfo(c,g);}catch(System.Reflection.TargetInvocationException){}
  Check(!smallFontScope,"INFO exception must restore font scope");
  c.NowRoll=true;g.Throw=false;g.Drawn="";DrawDirectInfo(c,g);Check(g.Drawn=="","INFO visibility");
  c.NowRoll=false;g.Drawn="";g.Xs.Clear();
  var nativeInfoRow=new RuntimeRow{SourceText="原文",Text="中A。",Colors=new byte[]{0,2,3},Controls=new byte[]{0,0,46}};
  infoRows["原文"]=nativeInfoRow;
  Check(!Kibu10ZhCN.Plugin.DrawKibu10Info(c,g)&&g.Drawn=="中A。","Kibu10 INFO renderer must replace the shared prefix");
  Check(g.Xs.Count==3 && g.Xs[0]==208 && g.Xs[1]==220 && g.Xs[2]==226,"Kibu10 INFO must use native 12px full-width and 6px half-width advances");
  Check(g.Fonts.Count==2 && g.Fonts[0]==32 && g.Fonts[1]==656,"Kibu10 INFO must select the native top-bar font and restore the previous font");
  g.Throw=true;try{Kibu10ZhCN.Plugin.DrawKibu10Info(c,g);}catch(System.Reflection.TargetInvocationException){}
  Check(g.Fonts.Count==4 && g.Fonts[2]==32 && g.Fonts[3]==656 && !smallFontScope,"Kibu10 INFO must restore the native font and scope after draw failure");
  g.Throw=false;
  Check(Kibu10ZhCN.Plugin.NativeInfoWidth('Ａ')==12 && Kibu10ZhCN.Plugin.NativeInfoWidth('ｱ')==6 && Kibu10ZhCN.Plugin.NativeInfoWidth('?')==6 && Kibu10ZhCN.Plugin.NativeInfoWidth('　')==12,"Kibu10 INFO width classification must match native cells, including full-width spaces");
  var read=new ReadState{Display=new DisplayTranslation{Opcode=255,Rows=new[]{row}}};
  DirectLexicon.Masks[row.Text]="0000";
  AfterDirectDialogue(c,read);
  Check(c.bg_itigyougun_mojiretu[0].Contains("中文"),"Dialogue translated");
  bool control=false,color=false;
  for(int i=0;i<c.BunsyouGun_gyousuu;i++)
  {
   Check(c.bg_itigyougun_rubisuu[i]==0,"Original ruby hidden");
   foreach(int ruby in c.bg_itigyougun_rubi_index[i])Check(ruby==-1,"Ruby map cleared");
   foreach(sbyte v in c.bg_itigyougun_control[i])control|=v==46;
   foreach(sbyte v in c.bg_itigyougun_color[i])color|=v==2;
  }
  Check(control&&color,"Reflow must retain color and control events");
  Check(Object.ReferenceEquals(bytes,c.Script)&&c.Pos==123,"Dialogue must preserve save offsets");
  var helpSource=new[]{Row("今作、「永劫会事件」は"),Row("２人の登場人物を中心に"),Row("最大４人の人物の視点"),Row("からゲームを進めるシス"),Row("テムになっています。",terminal:46)};
  var helpTarget=new[]{Row("本作《永劫会事件》"),Row("以两位角色为中心，"),Row("最多可从四位角色的视角"),Row("展开"),Row("游戏。",terminal:46)};
  for(int i=0;i<helpTarget.Length;i++)helpTarget[i].SourceText=helpSource[i].Text;
  for(int i=0;i<helpTarget[2].Colors.Length;i++)helpTarget[2].Colors[i]=2;
  Segment(helpTarget);
  translation.Displays.Add(164,new DisplayTranslation{Offset=164,Opcode=255,Rows=helpTarget});
  c.Pos=170;c.MainTask=17;c.BunsyouGun_gyousuu=5;
  for(int i=0;i<helpSource.Length;i++)c.bg_itigyougun_mojiretu[i]=helpSource[i].Text;
  AfterDirectDialogue(c,null);
  Check(c.BunsyouGun_gyousuu==4 && c.bg_itigyougun_mojiretu[0]=="本作《永劫会事件》" && c.bg_itigyougun_mojiretu[2]=="最多可从四位角色的视角" && c.bg_itigyougun_mojiretu[3]=="展开游戏。","Help text must recover by exact source rows and merge its obsolete soft line break");
  c.MainTask=0;c.Pos=123;
  c.BunsyouGun_gyousuu=8;c.PrintDanYoyaku=6;c.NowNamae=0;
  BeforeDirectViewport(c);Check(c.Resumed,"Viewport must request native full redraw after scrolling");
  int x=0,y=0;DirectDrawState scale;
  Check(!BeforeDirectDraw(c,0,0,ref x,ref y,out scale),"Scrolled-out glyphs must be hidden");
  RestoreDirectScale(scale);
  c.BunsyouGun_gyousuu=1;c.PrintDanYoyaku=0;BeforeDirectViewport(c);
  Check(BeforeDirectDraw(c,0,0,ref x,ref y,out scale)&&y==152,"New page resets top and keeps fixed speaker row");
  BeforeDraw(new DirectGraphicsStub(),new[]{'文'},0,0);
  Check(Kibu1ZhCN.LegacyFontRenderer.Small==null,"Ruby-bearing body must use 16px");
  bool previous;BeforeSmallFontPage(out previous);
  BeforeDraw(new DirectGraphicsStub(),new[]{'项'},0,0);
  Check(Object.ReferenceEquals(Kibu1ZhCN.LegacyFontRenderer.Primary,font)&&Object.ReferenceEquals(Kibu1ZhCN.LegacyFontRenderer.Small,smallFont),"Nested menu must use its native size inside body scope");
  RestoreSmallFontPage(previous);
  RestoreDirectScale(scale);
  BeforeDraw(new DirectGraphicsStub(),new[]{'栏'},0,0);
  Check(Object.ReferenceEquals(Kibu1ZhCN.LegacyFontRenderer.Small,smallFont),"Body finalizer must restore native header font selection");
  bool speakerState;BeforeDirectSpeaker(c,0,ref y,out speakerState);
  BeforeDraw(new DirectGraphicsStub(),new[]{'名'},0,0);
  Check(Kibu1ZhCN.LegacyFontRenderer.Small==null,"Dialogue nameplate must use the 16px body font");
  RestoreDirectSpeaker(speakerState);
  BeforeDraw(new DirectGraphicsStub(),new[]{'项'},0,0);
  Check(Object.ReferenceEquals(Kibu1ZhCN.LegacyFontRenderer.Small,smallFont),"Speaker finalizer must restore native font-size selection");
  int length=999;Check(BeforeMenuLength("游戏推进方式",ref length)&&length==999,"Non-menu string byte lengths must remain untouched");
  bool measureState;BeforeMenuMeasure(out measureState);
  Check(!BeforeMenuLength("游戏推进方式",ref length)&&length==12,"Chinese longest option must measure as six native fullwidth cells");
  Check(!BeforeMenuLength("关于存档",ref length)&&length==8,"Shorter option retains group alignment");
  Check(!BeforeMenuLength("ＡAｱ中",ref length)&&length==6,"Mixed native fullwidth and halfwidth widths");
  RestoreMenuMeasure(measureState);
  Check(BeforeMenuLength("中文",ref length),"Menu finalizer must restore native script byte measurements");
  c.bg_itigyougun_mojiretu[0]="中文ABC测试";c.BunsyouGun_gyousuu=1;c.MojiHani_yoko=3;
  x=0;FitDirectText(c,2,0,false,ref x);Check(x==53,"Runtime placement must include exactly the measured 9px Latin gap");
  x=0;FitDirectText(c,5,0,false,ref x);Check(x==89,"The gap after an English word must match the layout width");
  c.MojiHani_tate=1;
  var full=new[]{Row("第一行"),Row("第二行"),Row("第三行"),Row("第四行"),Row("第五行"),Row("第六行（译注：原有长说明。）",terminal:46)};
  AfterDirectDialogue(c,new ReadState{Display=new DisplayTranslation{Rows=full}});
  Check(c.BunsyouGun_gyousuu==6,"Full-screen rows must bypass normal four-row capacity");
  for(int i=0;i<full.Length;i++)Check(c.bg_itigyougun_mojiretu[i]==full[i].Text,"Full-screen authored row changed");
  x=37;y=91;BeforeDirectDraw(c,0,0,ref x,ref y,out scale);RestoreDirectScale(scale);
  Check(x==37 && y==91,"Full-screen native coordinates must bypass dialogue positioning");
  int clicks=0;foreach(var plane in c.bg_itigyougun_control)if(plane!=null)foreach(var controlByte in plane)if(controlByte==59)clicks++;
  Check(clicks==0,"Full-screen notes must not introduce any automatic click");
  return "Direct runtime: subtitle, INFO ASCII/palette/exception, immutable script, reflow, controls, ruby PASS";
 }
}
