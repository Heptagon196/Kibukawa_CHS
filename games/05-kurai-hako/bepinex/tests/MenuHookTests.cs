using System;
using System.IO;
using System.Reflection;
using System.Reflection.Emit;
using System.Collections.Generic;
using HarmonyLib;

public static class MenuHookTests
{
    private static string root, pluginDir, framework;
    public static void Main(string[] args)
    {
        root=args[0]; pluginDir=args[1]; framework=args[2];
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender, ResolveEventArgs e) {
            string name=new AssemblyName(e.Name).Name+".dll";
            foreach (string folder in new [] { Path.Combine(framework,"BepInEx/core"),Path.Combine(root,"kibu5_Data/Managed"),pluginDir })
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
        Assembly game=Assembly.LoadFrom(Path.Combine(root,"kibu5_Data/Managed/Assembly-CSharp.dll"));
        Type canvas=game.GetType("appli1.CanvasEx",true);
        MethodInfo iterator=AccessTools.EnumeratorMoveNext(AccessTools.Method(canvas,"Script"));
        var original=PatchProcessor.GetOriginalInstructions(iterator);
        Assembly plugin=Assembly.LoadFrom(Path.Combine(pluginDir,"Kibu5ZhCN.dll"));
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
        Console.WriteLine("PASS: production transpiler rewrites both original menu initializers before input processing.");
    }
}
