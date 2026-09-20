using System;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using Kibukawa.Engine.Gmode20050817Direct;
namespace HarmonyLib {
    public class CodeInstruction { public OpCode opcode; public object operand; public CodeInstruction() {} public CodeInstruction(OpCode op,object value) {opcode=op;operand=value;} }
    public class Harmony { public void Patch(MethodInfo m, HarmonyMethod transpiler=null, HarmonyMethod prefix=null) {} }
    public class HarmonyMethod { public HarmonyMethod(Type t,string n) {} }
    public static class AccessTools {
        public static FieldInfo Field(Type t,string n) { return t.GetField(n,BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static|BindingFlags.Instance); }
        public static MethodInfo Method(Type t,string n) { return t.GetMethod(n,BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static|BindingFlags.Instance); }
        public static MethodInfo EnumeratorMoveNext(MethodInfo m) { return m; }
    }
}
public class ChoiceCanvas {
    public sbyte[] Script; public int[] LabelIndex=new int[10], Sentaku_index=new int[6];
    public int komando_modori, Pos=8043, CommandCursorPos=1, CommandTop=0, SentakuStock=2;
    public bool NowCommand=true, NowChobunCommand=false;
    public int[] Sentaku_kioku_id=new int[50], Sentaku_kioku_pos=new int[50], Sentaku_kioku_top_pos=new int[50];
    public void KOMANDO() {} public void CHOUBUN_KOMANDO() {} public void Game_adv() {} public void Game_command() {}
}
public class Game_advFixture { public void Game_adv() {} public void Game_command() {} }
public class Game_commandFixture { public void Game_adv() {} public void Game_command() {} }
public static class ChoiceMemoryTests {
    static void Check(bool b,string s) { if(!b) throw new Exception(s); }
    static List<HarmonyLib.CodeInstruction> Read(string[] lines) {
        var ops=typeof(OpCodes).GetFields().Where(f=>f.FieldType==typeof(OpCode)).Select(f=>(OpCode)f.GetValue(null)).ToDictionary(o=>o.Name);
        var result=new List<HarmonyLib.CodeInstruction>();
        foreach(var line in lines) {
            int split=line.IndexOf(' '); string name=split<0?line:line.Substring(0,split), arg=split<0?"":line.Substring(split+1).Trim();
            object operand=arg;
            if(arg.StartsWith("branch:")) operand=Int32.Parse(arg.Substring(7));
            else if(name=="ldfld" || name=="stfld") operand=typeof(ChoiceCanvas).GetField(arg.Substring(arg.LastIndexOf("::")+2)) as object ?? arg;
            result.Add(new HarmonyLib.CodeInstruction { opcode=ops[name],operand=operand });
        }
        return result;
    }
    static List<HarmonyLib.CodeInstruction> Rewrite(List<HarmonyLib.CodeInstruction> code, Type fixture) {
        var method=typeof(DirectChoiceMemory).GetMethod("Rewrite",BindingFlags.Static|BindingFlags.NonPublic);
        return ((IEnumerable<HarmonyLib.CodeInstruction>)method.Invoke(null,new object[]{code,fixture.GetMethod(fixture.Name.Replace("Fixture",""))})).ToList();
    }
    static void RunIL(List<HarmonyLib.CodeInstruction> code,int start,int end,ChoiceCanvas c) {
        var stack=new Stack<object>(); var locals=new Dictionary<string,object>(); locals["1"]=c;
        int pc=start, steps=0;
        while(pc<end) {
            if(++steps>10000) throw new Exception("IL loop did not end");
            var ins=code[pc++];string op=ins.opcode.Name,arg=Convert.ToString(ins.operand);
            if(op=="ldarg.0") stack.Push(c);
            else if(op.StartsWith("ldloc.")) stack.Push(locals[op.Substring(6)]);
            else if(op.StartsWith("stloc.")) locals[op.Substring(6)]=stack.Pop();
            else if(op=="ldfld") stack.Push(((FieldInfo)ins.operand).GetValue(stack.Pop()));
            else if(op=="stfld") { object v=stack.Pop();((FieldInfo)ins.operand).SetValue(stack.Pop(),v); }
            else if(op=="ldc.i4.m1") stack.Push(-1);
            else if(op=="ldc.i4.s" || op=="ldc.i4") stack.Push(Int32.Parse(arg));
            else if(op.StartsWith("ldc.i4.")) stack.Push(Int32.Parse(op.Substring(7)));
            else if(op=="ldelem.i4") {int i=(int)stack.Pop();stack.Push(((int[])stack.Pop())[i]);}
            else if(op=="stelem.i4") {int v=(int)stack.Pop(),i=(int)stack.Pop();((int[])stack.Pop())[i]=v;}
            else if(op=="add") {int b=(int)stack.Pop(),a=(int)stack.Pop();stack.Push(a+b);}
            else if(op=="call") stack.Push(((MethodInfo)ins.operand).Invoke(null,new[]{stack.Pop()}));
            else if(op=="br" || op=="br.s") pc=(int)ins.operand;
            else if(op=="brtrue.s") {if((int)stack.Pop()!=0) pc=(int)ins.operand;}
            else if(op.StartsWith("bne.un") || op.StartsWith("blt")) {int b=(int)stack.Pop(),a=(int)stack.Pop();if(op.StartsWith("bne")?a!=b:a<b) pc=(int)ins.operand;}
            else throw new Exception("Unsupported native IL: "+op);
        }
        Check(stack.Count==0,"Unbalanced stack");
    }
    static void Begin(ChoiceCanvas c,int start) {
        int end=c.Pos;c.Pos=start;
        typeof(DirectChoiceMemory).GetMethod("BeginMenu",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{c});c.Pos=end;
    }
    public static void Run(string[] adv,string[] command) {
        DirectChoiceMemory.Install(new HarmonyLib.Harmony(),typeof(ChoiceCanvas));
        var raw=Read(command);var changed=Rewrite(Read(command),typeof(Game_commandFixture));
        var restored=Rewrite(Read(adv),typeof(Game_advFixture));
        var c=new ChoiceCanvas();RunIL(raw,63,134,c);
        Check(c.Sentaku_kioku_id.All(i=>i==0),"Native cancellable menu reproduction");
        foreach(int label in new[]{0,23,-1}) {
            c=new ChoiceCanvas{komando_modori=label};Begin(c,8000);
            RunIL(changed,63,134,c);c.CommandCursorPos=0;RunIL(restored,838,872,c);
            Check(c.CommandCursorPos==1 && c.komando_modori==label,"Confirm/reopen or return-label corruption");
            c.CommandCursorPos=0;c.NowCommand=false;c.NowChobunCommand=true;RunIL(restored,907,941,c);
            Check(c.CommandCursorPos==1,"Long menu restore");
        }
        c=new ChoiceCanvas{Script=new sbyte[]{1,2,3},NowCommand=false,komando_modori=-1,SentakuStock=6};
        for(int n=0;n<90;n++){c.Pos=6000+n;c.CommandCursorPos=n%6;RunIL(changed,63,134,c);}
        c.Script=new sbyte[]{1,2,3};
        for(int n=0;n<90;n++){c.Pos=6000+n;c.CommandCursorPos=0;RunIL(restored,838,872,c);Check(c.CommandCursorPos==n%6,"Reload/90-menu session memory");}
        c=new ChoiceCanvas{Pos=9000,komando_modori=1};Begin(c,7000);RunIL(changed,63,134,c);
        Begin(c,7100);c.CommandCursorPos=0;RunIL(restored,838,872,c);Check(c.CommandCursorPos==0,"Shared-terminator collision");
        Begin(c,7000);RunIL(restored,838,872,c);Check(c.CommandCursorPos==1,"Independent identity lost");
        c.Script=new sbyte[]{9};c.CommandCursorPos=0;c.Sentaku_kioku_id=new int[50];RunIL(restored,838,872,c);Check(c.CommandCursorPos==0,"Script identity collision");
        Check(changed.Count==raw.Count,"Instruction count changed");
        Check(changed.Where((v,i)=>v.opcode!=raw[i].opcode).Count()==4,"Unexpected command edits");
        for(int i=172;i<command.Length;i++) if(i!=173) Check(changed[i].opcode==raw[i].opcode&&Equals(changed[i].operand,raw[i].operand),"Native cancel target changed");
        var rawAdv=Read(adv);Check(restored.Where((v,i)=>v.opcode!=rawAdv[i].opcode).Count()==4,"Unexpected restore edits");
        Console.WriteLine("PASS: real direct-method IL, cancellable and long menus, 90 menu identities, script reload/isolation, distinct open offsets, native cancel branch preserved.");
    }
}
