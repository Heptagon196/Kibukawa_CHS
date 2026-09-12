using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.Serialization;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using Kibu1ZhCN;

public sealed class EngineCommand
{
    public int instruction, opcode, nextCursor;
    public string[] strings, expected;
    public int[] integers, jumps;
}
public sealed class EngineScript { public string name, bytes; public EngineCommand[] commands; }
public sealed class EngineInput { public int[][] definitions; public EngineScript[] scripts; }

// Executes the shipped managed Read/Jump/ExeText methods on an uninitialized
// CanvasEx with only managed buffers populated. No constructor, scene, Unity
// lifecycle method, renderer, sound, input, file write to the game, or window.
public static class OriginalEngineTests
{
    private static Type canvas;
    private static object instance;
    private const BindingFlags Flags=BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.Static;
    private static void Set(string name, object value) { canvas.GetField(name,Flags).SetValue(instance,value); }
    private static object Get(string name) { return canvas.GetField(name,Flags).GetValue(instance); }
    private static void Check(bool result, string message) { if(!result) throw new Exception(message); }
    private static sbyte[] Signed(byte[] bytes) { return bytes.Select(b=>unchecked((sbyte)b)).ToArray(); }
    public static void Main(string[] args)
    {
        try { Run(args); }
        catch(Exception e) { Console.Error.WriteLine(e.ToString()); Environment.Exit(1); }
    }
    private static void Run(string[] args)
    {
        string managed=Path.Combine(args[0],"kibu7_Data/Managed");
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object sender,ResolveEventArgs e) {
            string p=Path.Combine(managed,new AssemblyName(e.Name).Name+".dll");
            return File.Exists(p)?Assembly.LoadFrom(p):null;
        };
        var serializer=new JavaScriptSerializer{MaxJsonLength=100000000};
        var input=serializer.Deserialize<EngineInput>(File.ReadAllText(args[1]));
        var pack=TranslationPackReader.Load(args[2]);
        var catalog=new TranslationCatalog(pack);
        canvas=Assembly.LoadFrom(Path.Combine(managed,"Assembly-CSharp.dll")).GetType("appli1.CanvasEx",true);
        instance=FormatterServices.GetUninitializedObject(canvas);
        Set("CmdData",input.definitions.Select(d=>d.Select(n=>unchecked((sbyte)n)).ToArray()).ToArray());
        Set("ScStr",new string[16]); Set("ScInt",new int[16]);
        Set("Text",Enumerable.Range(0,9).Select(n=>new char[20]).ToArray());
        Set("TextC",Enumerable.Range(0,9).Select(n=>new sbyte[20]).ToArray());
        Set("TextLen",new sbyte[9]); Set("TextPos",new sbyte[]{4,0}); Set("TextLine",(sbyte)4);
        var read=canvas.GetMethod("Read",Flags); var jump=canvas.GetMethod("Jump",Flags);
        var text=canvas.GetMethod("ExeText",Flags);
        int commands=0, changed=0, jumpChecks=0, textChecks=0, growth=0, shrink=0;
        foreach(var script in input.scripts)
        {
            var original=Signed(Convert.FromBase64String(script.bytes));
            var data=(sbyte[])original.Clone(); Set("ScData",data); Set("ScCur",0);
            var boundaries=new HashSet<int>(script.commands.Select(c=>c.instruction));
            foreach(var c in script.commands)
            {
                string at=script.name+":"+c.instruction;
                Check((int)Get("ScCur")==c.instruction,"Sequential cursor: "+at);
                // The original reader must clear old string slots itself.
                var strings=(string[])Get("ScStr");
                for(int k=0;k<strings.Length;k++) strings[k]="stale";
                read.Invoke(instance,null);
                Check((int)Get("Cmd")==c.opcode && (int)Get("ScCur")==c.nextCursor,"Read opcode/cursor: "+at);
                strings=(string[])Get("ScStr");
                for(int k=0;k<strings.Length;k++) Check(strings[k]==(k<c.strings.Length?c.strings[k]:null),"Actual SJIS/string slot: "+at+":"+k);
                var integers=(int[])Get("ScInt");
                for(int k=0;k<c.integers.Length;k++) Check(integers[k]==c.integers[k],"Actual integer slot: "+at+":"+k);
                var saved=(int[])integers.Clone();
                changed+=catalog.ApplyScript(script.name,c.instruction,c.opcode,strings);
                Check((int)Get("ScCur")==c.nextCursor && ReferenceEquals(Get("ScData"),data),"Translation changed original cursor/buffer: "+at);
                Check(integers.SequenceEqual(saved),"Translation changed integer operands: "+at);
                for(int k=0;k<c.expected.Length;k++)
                {
                    Check(strings[k]==c.expected[k],"Translation at actual Read address: "+at+":"+k);
                    if(strings[k]!=null)
                    {
                        if(c.strings[k]!=null && strings[k].Length>c.strings[k].Length) growth++;
                        if(c.strings[k]!=null && strings[k].Length<c.strings[k].Length) shrink++;
                        Set("TextLen",new sbyte[9]); Set("TextPos",new sbyte[]{4,0});
                        Check(strings[k].Length<=20,"Target exceeds native UTF16 buffer: "+at);
                        text.Invoke(instance,new object[]{strings[k],2});
                        int size=((sbyte[])Get("TextLen"))[4];
                        Check(size==strings[k].Length && new string(((char[][])Get("Text"))[4],0,size)==strings[k],"Actual ExeText lost glyphs: "+at);
                        Check(((sbyte[][])Get("TextC"))[4].Take(size).All(n=>n==2),"Actual ExeText lost color: "+at);
                        Check((int)Get("ScCur")==c.nextCursor,"ExeText changed script cursor: "+at); textChecks++;
                    }
                }
                foreach(int destination in c.jumps)
                {
                    Check(destination==65535 || boundaries.Contains(destination),"Jump not on original command boundary: "+at);
                    Set("oldCur",-123);
                    bool result=(bool)jump.Invoke(instance,new object[]{false,destination});
                    // Non-sentinel Jump returns true even when Truth is false:
                    // the return is a handled-command result, not taken-branch.
                    Check(result==(destination!=65535) && (int)Get("ScCur")==c.nextCursor && (int)Get("oldCur")==-123,"Untaken jump changed state: "+at);
                    result=(bool)jump.Invoke(instance,new object[]{true,destination});
                    Check(result,"Taken jump did not return true: "+at);
                    if(destination==65535) Check((int)Get("ScCur")==c.nextCursor && (int)Get("oldCur")==-123,"Jump sentinel changed state: "+at);
                    else Check((int)Get("ScCur")==destination && (int)Get("oldCur")==c.nextCursor,"Original return/jump cursor changed: "+at);
                    Set("ScCur",c.nextCursor); jumpChecks++;
                }
                // Stress arbitrary growth/shrink/empty replacement after Read.
                if(c.strings.Length>0)
                {
                    strings[0]=new string('中',2000);
                    Check((int)Get("ScCur")==c.nextCursor,"Long decoded target affected cursor: "+at);
                    strings[0]="";
                    Check((int)Get("ScCur")==c.nextCursor,"Empty decoded target affected cursor: "+at);
                }
                commands++;
            }
            Check((int)Get("ScCur")==data.Length && data.SequenceEqual(original),"Original script bytes changed: "+script.name);
        }
        Check(changed==pack.scripts.Length,"Not every production translation replayed");
        Check(catalog.SourceMismatches==0,"Source mismatch in actual engine replay");
        Check(growth>0 && shrink>0,"No real growing and shrinking strings exercised");
        var report=new{game_runtime_tested=false,originalManagedMethodsExecuted=new[]{"appli1.CanvasEx.Read","appli1.CanvasEx.Jump","appli1.CanvasEx.ExeText"},scripts=input.scripts.Length,commands,translatedSlots=changed,jumpChecks,textChecks,growingTargets=growth,shrinkingTargets=shrink,originalBytesUnchanged=true,cursorsAndReturnOffsetsPreserved=true,scope="Managed buffer methods only; every stored instruction, not a playthrough or visual validation."};
        File.WriteAllText(args[3],serializer.Serialize(report));
        Console.WriteLine("PASS: actual original Read/Jump/ExeText; "+commands+" commands, "+jumpChecks+" branch operands, "+textChecks+" text slots; original bytes and cursors conserved.");
    }
}
