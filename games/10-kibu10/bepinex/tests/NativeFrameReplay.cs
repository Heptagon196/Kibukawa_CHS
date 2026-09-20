using System;
using System.Collections.Generic;
using System.Reflection;
using Kibukawa8.Runtime;
using Kibukawa.Engine.Gmode20050817Direct;

// Execute the extracted original instructions, with the production display hooks.
// Graphics/audio are sinks; unknown non-rendering calls fail instead of being guessed.
public class NativeFrameReplay : DirectCanvasRuntime
{
 Dictionary<string,string[]> methods;
 Dictionary<string,object> extra=new Dictionary<string,object>();
 DirectCanvasStub canvas;
 long clock=10000;
 int glyphs;
 object Get(string signature) {
  string name=signature.Substring(signature.IndexOf("::",StringComparison.Ordinal)+2);
  var f=typeof(DirectCanvasStub).GetField(name);
  if(f!=null)return f.GetValue(canvas);
  object value;if(extra.TryGetValue(name,out value))return value;
  if(signature.StartsWith("System.String "))return "";
  return 0;
 }
 void Set(string signature,object value) {
  string name=signature.Substring(signature.IndexOf("::",StringComparison.Ordinal)+2);
  var f=typeof(DirectCanvasStub).GetField(name);
  if(f!=null)f.SetValue(canvas,Convert.ChangeType(value,f.FieldType));else extra[name]=value;
 }
 static long N(object x){return Convert.ToInt64(x);}
 static int Index(string op,string operand){return Int32.Parse(operand.Length>0?operand.Substring(operand.IndexOf(':')+1):op.Substring(op.LastIndexOf('.')+1));}
 object Run(string name,params object[] args) {
  string[] code=methods[name];var stack=new Stack<object>();var locals=new object[32];
  for(int k=0;k<locals.Length;k++)locals[k]=0;
  for(int pc=0,steps=0;pc<code.Length;pc++) {
   if(++steps>40000)throw new Exception("Native instruction loop: "+name+":"+pc);
   string line=code[pc].Trim(),op=line.Split(' ')[0],v=line.Length>op.Length?line.Substring(op.Length+1):"";
   if(op=="nop")continue;
   if(op.StartsWith("ldarg")){stack.Push(args[Index(op,v)]);continue;}
   if(op.StartsWith("ldloc")){stack.Push(locals[Index(op,v)]);continue;}
   if(op.StartsWith("stloc")){locals[Index(op,v)]=stack.Pop();continue;}
   if(op.StartsWith("ldc.i4")){stack.Push(v.Length>0?Int32.Parse(v):op.EndsWith("m1")?-1:Int32.Parse(op.Substring(7)));continue;}
   if(op=="ldnull"){stack.Push(null);continue;}
   if(op=="ldstr"){stack.Push(v);continue;}
   if(op=="ldfld" || op=="ldsfld"){if(op=="ldfld")stack.Pop();stack.Push(Get(v));continue;}
   if(op=="stfld"){object val=stack.Pop();stack.Pop();Set(v,val);continue;}
   if(op=="pop"){stack.Pop();continue;}
   if(op.StartsWith("conv."))continue;
   if(op.StartsWith("ldelem")){int i=(int)N(stack.Pop());var a=(Array)stack.Pop();stack.Push(a.GetValue(i));continue;}
   if(op=="add" || op=="sub" || op=="mul" || op=="div" || op=="and" || op=="or"){
    long b=N(stack.Pop()),a=N(stack.Pop());stack.Push(op=="add"?a+b:op=="sub"?a-b:op=="mul"?a*b:op=="div"?a/b:op=="and"?a&b:a|b);continue;
   }
   if(op=="ret")return stack.Count>0?stack.Pop():null;
   if(op.StartsWith("br") || op.StartsWith("leave") || op.StartsWith("beq") || op.StartsWith("bne") || op.StartsWith("bge") || op.StartsWith("bgt") || op.StartsWith("ble") || op.StartsWith("blt")){
    bool jump=true;
    if(op.StartsWith("brfalse"))jump=N(stack.Pop())==0;
    else if(op.StartsWith("brtrue"))jump=N(stack.Pop())!=0;
    else if(!op.StartsWith("br") && !op.StartsWith("leave")){
     long b=N(stack.Pop()),a=N(stack.Pop());jump=op.StartsWith("beq")?a==b:op.StartsWith("bne")?a!=b:op.StartsWith("bge")?a>=b:op.StartsWith("bgt")?a>b:op.StartsWith("ble")?a<=b:a<b;
    }
    if(jump)pc=Int32.Parse(v.Substring(7))-1;continue;
   }
   if(op=="call" || op=="callvirt") {
    int paren=v.IndexOf('(');string signature=v.Substring(0,paren),parameters=v.Substring(paren+1,v.Length-paren-2);
    int argc=parameters.Length==0?0:parameters.Split(',').Length;
    bool instanceCall=signature.Contains("CanvasEx::") || op=="callvirt";
    var callArgs=new object[argc+(instanceCall?1:0)];for(int j=callArgs.Length-1;j>=0;j--)callArgs[j]=stack.Pop();
    object result=null;string method=signature.Substring(signature.IndexOf("::",StringComparison.Ordinal)+2);
    if(method=="get_Instance")result=this;
    else if(method=="CurrentTimeMillis")result=clock;
    else if(method=="get_Length")result=((string)callArgs[0]).Length;
    else if(method=="get_Chars")result=(int)((string)callArgs[0])[(int)N(callArgs[1])];
    else if(method=="PaintADV_text") {BeforeDirectPaintText(canvas);Run(method,callArgs);AfterDirectPaintText(canvas);}
    else if(method=="DrawAdvString") {
     int character=(int)N(callArgs[2]),row=(int)N(callArgs[4]),x=(int)N(callArgs[5]),y=(int)N(callArgs[6]);DirectDrawState ds;
     if(BeforeDirectDraw(canvas,character,row,ref x,ref y,out ds))glyphs++;
     RestoreDirectScale(ds);
    }
    else if(method=="BUNSYOU_PERIOD") {extra["ReachedWait"]=1;return true;}
    else if(method=="Play" || method=="SetColor" || method=="DrawAdvNafuda" || method=="PaintMain_kyara" || signature.Contains("Socotra.UI.StGraphics::")){}
    else throw new Exception("Unsupported call "+v);
    if(!signature.StartsWith("System.Void "))stack.Push(result);continue;
   }
   throw new Exception("Unsupported IL "+name+":"+pc+" "+line);
  }
  return null;
 }
 public static void Check(Dictionary<string,string[]> methods) {
  foreach(int vertical in new[]{0,1,2})foreach(bool firstRedraw in new[]{false,true})CheckCase(methods,vertical,firstRedraw);
 }
 static void CheckCase(Dictionary<string,string[]> methods,int vertical,bool firstRedraw) {
  var replay=new NativeFrameReplay();replay.methods=methods;replay.canvas=new DirectCanvasStub();var c=replay.canvas;
  canvasType=typeof(DirectCanvasStub);fields.Clear();ready=true;
  var state=states.GetValue(c,key=>new CanvasState());state.Script=c.Script;state.Dialogue=true;
  c.MainTask=6;c.MojiHani_tate=vertical;c.MojiHani_yoko=3;
  string[] text={"将把此前的所有数据清除","初始化，之后游戏将会","重新从头开始游戏。","是否确定要继续？"};
  var rows=new RuntimeRow[text.Length];
  for(int i=0;i<rows.Length;i++)rows[i]=new RuntimeRow{Text=text[i],SourceText=text[i],Colors=new byte[text[i].Length],Controls=new byte[text[i].Length],RubyJson="{}"};
  rows[3].Controls[7]=46;preserveDirectDialogueRows.Add(DirectDialogueKey(9454,rows));
  AfterDirectDialogue(c,new ReadState{Display=new DisplayTranslation{Offset=9454,Opcode=255,Rows=rows}});
  if(firstRedraw){c.Resumed=true;BeforeDirectPaintText(c);replay.Run("PaintADV_text",c,new object());AfterDirectPaintText(c);c.Resumed=false;}
  // Game() advances before Idle() paints; a redraw must commit its cursor too.
  for(int frame=0;frame<100;frame++) {
   replay.clock+=1000;replay.Run("Game_adv",c);
   if(replay.extra.ContainsKey("ReachedWait")){Console.WriteLine("PASS native confirmation mode="+vertical+" firstRedraw="+firstRedraw+" frames="+frame+" glyphs="+replay.glyphs);return;}
   BeforeDirectViewport(c);BeforeDirectPaintText(c);
   replay.Run("PaintADV_text",c,new object());
   AfterDirectPaintText(c);c.Resumed=false;
  }
  throw new Exception("Confirmation did not reach original click wait; row="+c.PrintDanYoyaku+" char="+c.PrintMojiKetaYoyaku);
 }
}
