using System;
using System.IO;
using System.Reflection;
using System.Reflection.Emit;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using HarmonyLib;

public static class MenuHookTests
{
    private static string root, pluginDir, framework;
    public static void Main(string[] args)
    {
        root=args[0]; pluginDir=args[1]; framework=args[2];
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
            string name=new AssemblyName(e.Name).Name+".dll";
            foreach (string folder in new [] { Path.Combine(framework,"BepInEx/core"),Path.Combine(root,"kibu4_Data/Managed"),pluginDir })
            {
                string path=Path.Combine(folder,name);
                if (File.Exists(path)) return Assembly.LoadFrom(path);
            }
            return null;
        };
        Run();
    }
    private static void Run()
    {
        Assembly game=Assembly.LoadFrom(Path.Combine(root,"kibu4_Data/Managed/Assembly-CSharp.dll"));
        foreach (string typeName in new [] { "appli1.CanvasEx", "appli2.CanvasEx" })
        {
        Type canvas=game.GetType(typeName,true);
        MethodInfo iterator=AccessTools.EnumeratorMoveNext(AccessTools.Method(canvas,"Script"));
        var original=PatchProcessor.GetOriginalInstructions(iterator);
        Assembly plugin=Assembly.LoadFrom(Path.Combine(pluginDir,"Kibu4ZhCN.dll"));
        MethodInfo patch=plugin.GetType("Kibu1ZhCN.Plugin",true).GetMethod("RememberMenuInitialSelection",BindingFlags.NonPublic|BindingFlags.Static);
        var rewritten=new List<CodeInstruction>((IEnumerable<CodeInstruction>)patch.Invoke(null,new object[]{original}));
        int calls=0;
        for(int i=0;i<rewritten.Count;i++)
        {
            MethodInfo method=rewritten[i].operand as MethodInfo;
            if (rewritten[i].opcode==OpCodes.Call && method!=null && method.DeclaringType.Name=="MenuSelectionMemory" && method.Name=="Restore")
            {
                calls++;
                if(rewritten[i+1].opcode!=OpCodes.Stelem_I1) throw new Exception("Restore must feed the original selection store");
            }
        }
        if(calls!=2) throw new Exception("Both actual menu initializers must be rewritten");
        // Use each part's actual Paint IL and production literal transpiler.
        MethodInfo paint=AccessTools.Method(canvas,"Paint");
        var paintCode=PatchProcessor.GetOriginalInstructions(paint);
        string source=typeName=="appli1.CanvasEx" ? "前編をはじめる" : "後編をはじめる";
        string target=typeName=="appli1.CanvasEx" ? "开始前篇" : "开始后篇";
        var entries=new List<object>();
        for(int i=0;i<paintCode.Count;i++)
            if(paintCode[i].opcode==OpCodes.Ldstr && (string)paintCode[i].operand==source)
                entries.Add(new{ index=i, token=paint.MetadataToken, instruction=i, source, target, method=paint.Name });
        if(entries.Count!=2) throw new Exception("Expected title drawing and width measurement literals");
        var json=new JavaScriptSerializer();
        object pack=json.Deserialize(json.Serialize(new{schema=1,literals=entries}),plugin.GetType("Kibu1ZhCN.TranslationPack"));
        object catalog=Activator.CreateInstance(plugin.GetType("Kibu1ZhCN.TranslationCatalog"),new[]{pack});
        Type pluginType=plugin.GetType("Kibu1ZhCN.Plugin");
        pluginType.GetField("catalog",BindingFlags.NonPublic|BindingFlags.Static).SetValue(null,catalog);
        MethodInfo literals=pluginType.GetMethod("TranslateLiterals",BindingFlags.NonPublic|BindingFlags.Static);
        var translated=new List<CodeInstruction>((IEnumerable<CodeInstruction>)literals.Invoke(null,new object[]{paintCode,paint}));
        int hits=0;
        foreach(var instruction in translated)
            if(instruction.opcode==OpCodes.Ldstr && (string)instruction.operand==target) hits++;
        if(hits!=2) throw new Exception("Part-specific title literal routing failed");
        }
        Console.WriteLine("PASS: both parts' production menu transpilers and title draw/width literal replacements.");
    }
}
