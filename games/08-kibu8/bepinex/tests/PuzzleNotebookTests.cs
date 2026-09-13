using System;
using System.Reflection;
using Kibu8ZhCN;
public static class PuzzleNotebookTests
{
    public sealed class Canvas {
        public string SaveScenarioFileName="c3-02c";
        public int Pos=29475,SentakuStock,CommandCursorPos,CommandTop,Key_select,MainTask=5,ListBackPos;
        public static int Height=240,FHeight=12;
        public int SubTask=3,ListPage,ListPos; public bool SystemResumed; public string ListScenarioFileName="c3-02c"; public string[] bg_itigyougun_mojiretu=new[]{"name","age","body"};
        public int Command=59;
        public int[] LabelIndex=new int[500];
        public bool NowChobunCommand=true;
        public string[] Sentaku_nafuda=new string[20]; public int[] Sentaku_index=new int[20];
        public void KeyFlush() { Key_select=0; }
        public void RISUTO() { ListBackPos=Pos; MainTask=17; }
        public void SENTAKUSI() {} public void PaintLongCommand() {}
        public void CHOUBUN_KOMANDO() {} public void GetKeyStatus() {}
    }
    static void Call(string method,Canvas c) { typeof(PuzzleNotebook).GetMethod(method,BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{c}); }
    static void Require(bool b) { if(!b) throw new Exception("Puzzle notebook regression"); }
    public static void Run() {
        PuzzleNotebook.Install(new HarmonyLib.Harmony("test"),typeof(Canvas));
        var c=new Canvas(); Call("AddChoice",c);Require(c.SentakuStock==1 && c.Sentaku_index[0]==500 && c.LabelIndex[500]==3478);
        int[] labels={80,80,81,80,80,80};
        for(int i=0;i<6;i++) { c.Sentaku_index[c.SentakuStock]=labels[i];c.Sentaku_nafuda[c.SentakuStock++]="名字"; }
        int origin=(int)typeof(PuzzleNotebook).GetMethod("Origin",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{156,c});Require(origin==138 && origin+7*14<=Canvas.Height);
        // Native Game_command resolves the selected label and finishes its normal cleanup.
        Require(c.Sentaku_index[3]==81);
        c.CommandCursorPos=0;c.Key_select=1;
        c.KeyFlush();c.MainTask=0;c.NowChobunCommand=false;
        c.Pos=c.LabelIndex[c.Sentaku_index[c.CommandCursorPos]];c.SentakuStock=0;
        Require(c.Pos==3478 && c.MainTask==0 && c.Key_select==0);
        // Native interpreter reads the existing RISUTO opcode at that address.
        c.Command=114;c.Pos++;
        object[] args={c,false};typeof(PuzzleNotebook).GetMethod("BeforeNotebook",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,args);
        Require((bool)args[1]);c.RISUTO();
        typeof(PuzzleNotebook).GetMethod("AfterNotebook",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,args);
        Require(c.MainTask==17 && c.ListBackPos==29472 && c.Command==114);
        c.MainTask=0;c.Pos=c.ListBackPos+3;Call("AddChoice",c);
        Require(c.SentakuStock==1 && c.LabelIndex.Length==501 && c.Sentaku_index[0]==500);
        Require(typeof(PuzzleNotebook).GetMethod("PaintNotebook",BindingFlags.Static|BindingFlags.NonPublic)==null);
        var other=new Canvas { SaveScenarioFileName="c3-02b" };Call("AddChoice",other);Require(other.SentakuStock==0);
        other=new Canvas { Pos=10 };Call("AddChoice",other);Require(other.SentakuStock==0);
        Console.WriteLine("PASS: notebook uses native rendering; puzzle notebook entry, answer labels, no answer on open, repeat return and scenario isolation.");
    }
}
