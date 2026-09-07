using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Serialization;
using System.Web.Script.Serialization;
using HarmonyLib;

public sealed class ReadFixtures { public Dictionary<string,string> scripts; public int[][] definitions; }
public sealed class ReadCommand { public string script; public int instruction, opcode, nextCursor; public string[] strings; public int[] integers; }
public sealed class ReadReplay { public ReadCommand[] commands; }
public static class DualRuntimeTests
{
    static readonly BindingFlags Flags=BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.Static;
    static Type adapter, plugin, catalogType, packType;
    static Type[] canvases;
    static Assembly assembly;
    static int checks;
    static void Check(bool value,string message) { checks++; if(!value) throw new Exception(message); }
    static void Set(object obj,string name,object value)
    {
        var field=obj.GetType().GetField(name,Flags);
        field.SetValue(obj,field.FieldType.IsPrimitive ? Convert.ChangeType(value,field.FieldType) : value);
    }
    static object Get(object obj,string name) { return obj.GetType().GetField(name,Flags).GetValue(obj); }
    static object Call(string name,params object[] args) { return adapter.GetMethod(name,Flags).Invoke(null,args); }
    static object Canvas(int part, ReadFixtures fixtures)
    {
        var obj=FormatterServices.GetUninitializedObject(canvases[part]);
        Set(obj,"CmdData",fixtures.definitions.Select(row=>row.Select(x=>unchecked((sbyte)x)).ToArray()).ToArray());
        Set(obj,"ScInt",new int[20]); Set(obj,"ScStr",new string[20]); Set(obj,"Select",new sbyte[2]);
        Set(obj,"Truth",true); Set(obj,"Scene",2); Set(obj,"Scenario",part*4);
        return obj;
    }
    static object Pack(JavaScriptSerializer json, object value) { return json.Deserialize(json.Serialize(value),packType); }
    static void Bind(object pack) { Call("Initialize",pack,Activator.CreateInstance(catalogType,new[]{pack}),canvases[0],canvases[1]); }
    static string Target(string script,int address,int slot) { return "验证"+script+":"+address+":"+slot; }
    public static void Main(string[] args)
    {
        try { Run(args); }
        catch(Exception e) { Console.Error.WriteLine(e); Environment.ExitCode=1; }
    }
    static void Run(string[] args)
    {
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender,ResolveEventArgs e) {
            string name=new AssemblyName(e.Name).Name+".dll";
            foreach(string dir in new[]{Path.Combine(args[2],"BepInEx/core"),Path.Combine(args[0],"kibu4_Data/Managed"),args[1]})
                if(File.Exists(Path.Combine(dir,name))) return Assembly.LoadFrom(Path.Combine(dir,name));
            return null;
        };
        assembly=Assembly.LoadFrom(Path.Combine(args[1],"Kibu4ZhCN.dll"));
        var game=Assembly.LoadFrom(Path.Combine(args[0],"kibu4_Data/Managed/Assembly-CSharp.dll"));
        canvases=new[]{game.GetType("appli1.CanvasEx",true),game.GetType("appli2.CanvasEx",true)};
        adapter=assembly.GetType("Kibu1ZhCN.DualCanvasHooks",true); plugin=assembly.GetType("Kibu1ZhCN.Plugin",true);
        catalogType=assembly.GetType("Kibu1ZhCN.TranslationCatalog",true); packType=assembly.GetType("Kibu1ZhCN.TranslationPack",true);
        var json=new JavaScriptSerializer{MaxJsonLength=100000000};
        var fixtures=json.Deserialize<ReadFixtures>(File.ReadAllText(args[3]));
        var replay=json.Deserialize<ReadReplay>(File.ReadAllText(args[4]));
        var entries=new List<object>();
        foreach(var c in replay.commands)
            for(int slot=0;slot<c.strings.Length;slot++)
                if(!string.IsNullOrEmpty(c.strings[slot])) entries.Add(new {index=entries.Count+1, script=c.script,
                    instruction=c.instruction, opcode=c.opcode, slot, source=c.strings[slot], target=Target(c.script,c.instruction,slot)});
        var pack=Pack(json,new{schema=1,scripts=entries}); Bind(pack);
        var objects=new[]{Canvas(0,fixtures),Canvas(1,fixtures)};
        var harmony=new Harmony("local.kibu4.offline.tests");
        plugin.GetField("ready",Flags).SetValue(null,true);
        try
        {
            // Execute actual game Read with actual production Harmony prefix/postfix.
            foreach(var type in canvases)
                harmony.Patch(type.GetMethod("Read",Flags),
                    new HarmonyMethod(plugin.GetMethod("BeforeRead",Flags)),new HarmonyMethod(plugin.GetMethod("AfterRead",Flags)));
            int commands=0, replaced=0;
            foreach(var c in replay.commands)
            {
                int first=c.script.StartsWith("subscn_") ? 0 : (int.Parse(c.script.Substring(3))<4 ? 0 : 1);
                int last=c.script.StartsWith("subscn_") ? 1 : first;
                for(int part=first;part<=last;part++)
                {
                    object canvas=objects[part];
                    Set(canvas,"Scenario",c.script.StartsWith("subscn_") ? part*4 : int.Parse(c.script.Substring(3)));
                    Set(canvas,"ScSelect",c.script.StartsWith("subscn_") ? int.Parse(c.script.Substring(7)) : 0);
                    byte[] raw=Convert.FromBase64String(fixtures.scripts[c.script]);
                    var data=new sbyte[raw.Length]; Buffer.BlockCopy(raw,0,data,0,raw.Length);
                    Set(canvas,"ScData",data); Set(canvas,"ScCur",c.instruction);
                    canvases[part].GetMethod("Read",Flags).Invoke(canvas,null);
                    Check((int)Get(canvas,"ScCur")==c.nextCursor,"Read cursor changed: "+c.script+":"+c.instruction);
                    Check((int)Get(canvas,"Cmd")==c.opcode,"Opcode changed");
                    var ints=(int[])Get(canvas,"ScInt");
                    for(int j=0;j<c.integers.Length;j++) Check(ints[j]==c.integers[j],"Jump/integer argument changed");
                    var values=(string[])Get(canvas,"ScStr");
                    for(int j=0;j<c.strings.Length;j++)
                    {
                        string expected=string.IsNullOrEmpty(c.strings[j]) ? c.strings[j] : Target(c.script,c.instruction,j);
                        Check(values[j]==expected,"Wrong part/slot/source: "+part+":"+c.script+":"+c.instruction);
                        if(expected!=c.strings[j]) replaced++;
                    }
                    Check(data.SequenceEqual(raw.Select(x=>unchecked((sbyte)x))),"Original script bytes changed");
                    commands++;
                }
            }
            Check(commands>=19469 && replaced>=7419,"Incomplete dual reader coverage");
            // Reject wrong-part scenario routes, even when the catalog has that address.
            Set(objects[0],"ScSelect",0); Set(objects[0],"Scenario",4);
            Set(objects[1],"ScSelect",0); Set(objects[1],"Scenario",0);
            Check(Call("ScriptName",objects[0])==null && Call("ScriptName",objects[1])==null,"Cross-part route accepted");
            // Interleave per-instance menu choices and verify both survive independently.
            var menu=assembly.GetType("Kibu1ZhCN.MenuSelectionMemory",true);
            for(int i=0;i<2;i++)
            {
                Set(objects[i],"Scenario",i*4); Set(objects[i],"Cmd",106);
                Set(objects[i],"ScStr",new[]{"甲","乙"}); Set(objects[i],"ScInt",new[]{20,40,0});
                menu.GetMethod("RecordMenu").Invoke(null,new[]{objects[i],(object)100});
                Set(objects[i],"Select",new sbyte[]{0,(sbyte)i}); menu.GetMethod("Remember").Invoke(null,new[]{objects[i]});
            }
            Check((int)menu.GetMethod("Restore").Invoke(null,new[]{objects[0]})==0,"Front menu state leaked");
            Check((int)menu.GetMethod("Restore").Invoke(null,new[]{objects[1]})==1,"Back menu state lost");
            Call("ResetSession");
            Check((int)menu.GetMethod("Restore").Invoke(null,new[]{objects[1]})==0,"Session reset failed");
            // Sparse/empty production packs must leave native coroutines untouched.
            Bind(Pack(json,new{schema=1,scripts=new object[0]}));
            IEnumerator original=new object[0].GetEnumerator();
            Check(Object.ReferenceEquals(Call("AfterScript",objects[0],original),original),"Untranslated script was reflowed");
            Check(Object.ReferenceEquals(Call("AfterScript",objects[1],original),original),"Untranslated back script was reflowed");
            Console.WriteLine("PASS: "+commands+" actual game Read calls; "+replaced+" synthetic contextual replacements; "+checks+" assertions; both physical subscn routes, cursor/jumps/bytes unchanged, part and menu isolation.");
        }
        finally { harmony.UnpatchSelf(); plugin.GetField("ready",Flags).SetValue(null,false); Call("Reset"); }
    }
}
