using System;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using Kibukawa.Engine.Gmode20050817;
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
public class Game_advFixture { public void MoveNext() {} }
public class Game_commandFixture { public void MoveNext() {} }
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
        var method=typeof(NativeChoiceMemory).GetMethod("Rewrite",BindingFlags.Static|BindingFlags.NonPublic);
        return ((IEnumerable<HarmonyLib.CodeInstruction>)method.Invoke(null,new object[]{code,fixture.GetMethod("MoveNext")})).ToList();
    }
    static void RunIL(List<HarmonyLib.CodeInstruction> code,int start,int end,ChoiceCanvas c) {
        var stack=new Stack<object>(); var locals=new Dictionary<string,object>(); locals["1"]=c;
        int pc=start, steps=0;
        while(pc<end) {
            if(++steps>10000) throw new Exception("IL loop did not end");
            var ins=code[pc++];string op=ins.opcode.Name,arg=Convert.ToString(ins.operand);
            if(op=="ldloc.1") stack.Push(c);
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
    public static void RunMenu(string[] lines) {
        NativeMenuPosition.Install(new HarmonyLib.Harmony(),typeof(ChoiceCanvas),150);
        var original=Read(lines);
        var method=typeof(NativeMenuPosition).GetMethod("Rewrite",BindingFlags.Static|BindingFlags.NonPublic);
        var changed=((IEnumerable<HarmonyLib.CodeInstruction>)method.Invoke(null,new object[]{Read(lines)})).ToList();
        Check(changed.Count==original.Count+2,"Unexpected menu rewrite size");
        Check(changed[38].opcode==OpCodes.Pop && changed[39].opcode==OpCodes.Ldc_I4 && (int)changed[39].operand==150 && changed[40].opcode==OpCodes.Stloc_S,"Menu first row must be 150 (title 136)");
        for(int i=0;i<original.Count;i++) {
            if(i==38) continue;int j=i<38?i:i+2;
            Check(changed[j].opcode==original[i].opcode && Equals(changed[j].operand,original[i].operand),"Native menu loop/count/drawing modified at "+i);
        }
        Check(150+5*14==220,"Sixth item must stay visible without scrolling");
        Console.WriteLine("PASS: menu origin only; all original instructions outside origin assignment preserved, no five-item limit or scroll.");
    }
    static void Begin(ChoiceCanvas c,int start) {
        int end=c.Pos;c.Pos=start;
        typeof(NativeChoiceMemory).GetMethod("BeginMenu",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{c});
        c.Pos=end;
    }
    public static void Run(string[] adv,string[] command) {
        var c=new ChoiceCanvas();
        var original=Read(command);
        RunIL(original,323,394,c);
        Check(c.Sentaku_kioku_id.All(i=>i==0),"Original returnable menu unexpectedly remembered selection");
        Console.WriteLine("REPRODUCED: original native IL skips remembering second option when return label is 0.");
        NativeChoiceMemory.Install(new HarmonyLib.Harmony(),typeof(ChoiceCanvas));
        var changed=Rewrite(Read(command),typeof(Game_commandFixture));
        var restored=Rewrite(Read(adv),typeof(Game_advFixture));
        foreach(int label in new[]{0,23,-1}) {
            c=new ChoiceCanvas {komando_modori=label};Begin(c,8000);
            RunIL(changed,323,394,c);c.CommandCursorPos=0;
            RunIL(restored,1156,1198,c);
            Check(c.CommandCursorPos==1 && c.komando_modori==label,"Confirm/reopen failed or return target changed");
            c.CommandCursorPos=0;c.NowCommand=false;c.NowChobunCommand=true;
            RunIL(restored,1241,1283,c);Check(c.CommandCursorPos==1,"Long-text restore failed");
        }
        // Current save's c3-02b horizontal menu ends at opcode 5837 (Pos 5838).
        c=new ChoiceCanvas {NowCommand=false,komando_modori=-1,Pos=5838,CommandCursorPos=3,SentakuStock=6};
        for(int n=0;n<50;n++) c.Sentaku_kioku_id[n]=100+n;
        RunIL(changed,323,394,c);c.CommandCursorPos=0;
        RunIL(restored,1377,1419,c);
        Check(c.CommandCursorPos==3,"Full 50-entry table loses current horizontal menu selection");
        c.Script=new sbyte[]{1,2,3};
        for(int n=0;n<90;n++) { c.Pos=6000+n;c.CommandCursorPos=n%6;RunIL(changed,323,394,c); }
        c.Script=new sbyte[]{1,2,3}; // Reloading the same script retains its identity.
        for(int n=0;n<90;n++) {
            c.Pos=6000+n;c.CommandCursorPos=0;RunIL(restored,1377,1419,c);
            Check(c.CommandCursorPos==n%6,"Session memory must survive more than 50 menu identities");
        }
        Console.WriteLine("PASS: full native table and 90 horizontal menus retain selections across script reload.");
        // c1-05: both menus branch to label 32, so both native keys are 25514.
        c=new ChoiceCanvas {NowCommand=false,komando_modori=-1,Pos=25514,CommandCursorPos=2,SentakuStock=6};
        RunIL(changed,323,394,c);
        c.NowCommand=true;c.komando_modori=4;Begin(c,8598);c.CommandCursorPos=0;c.SentakuStock=5;
        RunIL(restored,1156,1198,c);
        Check(c.CommandCursorPos==0,"MO topic menu inherited horizontal third option");
        foreach(int selection in new[]{0,1,2,3,4}) {
            c.CommandCursorPos=selection;RunIL(changed,323,394,c);
            c.NowCommand=false;c.komando_modori=-1;c.CommandCursorPos=0;c.SentakuStock=6;
            RunIL(restored,1377,1419,c);
            Check(c.CommandCursorPos==2,"Topic selection changed horizontal menu");
            c.NowCommand=true;c.komando_modori=4;c.CommandCursorPos=0;c.SentakuStock=5;Begin(c,8598);
            RunIL(restored,1156,1198,c);
            Check(c.CommandCursorPos==selection,"Topic menu lost independent memory");
        }
        Begin(c,8692);c.CommandCursorPos=0;RunIL(restored,1156,1198,c);
        Check(c.CommandCursorPos==0,"Separate topic menus sharing a terminator collided");
        // Guard and identity loads only; native return-button IL stays unchanged.
        Check(changed.Where((v,i)=>v.opcode!=original[i].opcode).Count()==4,"Unexpected command edits");
        for(int i=461;i<command.Length;i++) if(i!=468) Check(changed[i].opcode==original[i].opcode && Equals(changed[i].operand,original[i].operand),"Back-button path modified");
        var rawAdv=Read(adv);Check(restored.Where((v,i)=>v.opcode!=rawAdv[i].opcode).Count()==8,"Unexpected restore edits");
        c=new ChoiceCanvas {NowCommand=false,komando_modori=0};RunIL(changed,323,394,c);
        Check(c.Sentaku_kioku_id.All(i=>i==0),"Non-text-menu policy changed");
        // Production hooks, native memory loops, and the real c2-02 page topology.
        string digest;
        using(var sha=System.Security.Cryptography.SHA256.Create()) digest=BitConverter.ToString(sha.ComputeHash(new byte[]{42})).Replace("-", "").ToLowerInvariant();
        NativePaginationData.Groups[digest]=new[]{new[]{1,1332,1403}};
        c=new ChoiceCanvas {Script=new sbyte[]{42},komando_modori=1,SentakuStock=6};
        c.LabelIndex[1]=1288;c.LabelIndex[2]=1331;c.LabelIndex[3]=1402;
        c.Sentaku_index[5]=3;
        Begin(c,1332);c.CommandCursorPos=5;RunIL(changed,323,394,c);
        c.Pos=1403;typeof(NativeChoiceMemory).GetMethod("BeginMenu",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{c});
        Check(c.Pos==1403,"Next page redirect failed");
        c.komando_modori=2;c.CommandCursorPos=3;
        ((MethodInfo)changed[468].operand).Invoke(null,new object[]{c});
        Check(c.komando_modori==1,"Cancel must exit the pagination group");
        c.Pos=1332;typeof(NativeChoiceMemory).GetMethod("BeginMenu",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{c});
        Check(c.Pos==1403,"Reentry must resume page two");
        c.CommandCursorPos=0;RunIL(restored,1156,1198,c);
        Check(c.CommandCursorPos==3,"Reentry must resume unconfirmed cursor on page two");
        c.Sentaku_index[5]=2;c.CommandCursorPos=5;RunIL(changed,323,394,c);
        c.Pos=1332;typeof(NativeChoiceMemory).GetMethod("BeginMenu",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{c});
        Check(c.Pos==1332,"Explicit Previous must not redirect back to page two");
        Console.WriteLine("PASS: paginated menu page/cursor restore, cancel, Next and Previous.");
        Console.WriteLine("PASS: MO shared terminator regression, independent topic/icon memory for all five options; production transpiler + native IL record/reopen, normal/long text, return targets 0/23/-1, non-paginated return labels unchanged, non-text menus unchanged.");
    }
}
