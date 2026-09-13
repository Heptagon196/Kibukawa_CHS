using System;
using HarmonyLib;
using System.Collections.Generic;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Reflection;

namespace Kibu8ZhCN
{
    internal static class PuzzleNotebook
    {
        static Type canvas;
        const int MenuStart=29472, MenuEnd=29475, NotebookOpcode=3478;
        sealed class Jump { internal int[] Labels; internal int Slot; }
        static readonly ConditionalWeakTable<object,Jump> jumps=new ConditionalWeakTable<object,Jump>();
        const string Caption="打开笔记本";
        static object Get(object c,string n) { return AccessTools.Field(canvas,n).GetValue(c); }
        static void Set(object c,string n,object value) { AccessTools.Field(canvas,n).SetValue(c,value); }
        internal static void Install(Harmony h,Type type) {
            canvas=type;
            h.Patch(AccessTools.Method(canvas,"CHOUBUN_KOMANDO"),null,new HarmonyMethod(typeof(PuzzleNotebook),"AddChoice"),null,null,null);
            h.Patch(AccessTools.Method(canvas,"RISUTO"),new HarmonyMethod(typeof(PuzzleNotebook),"BeforeNotebook"),new HarmonyMethod(typeof(PuzzleNotebook),"AfterNotebook"),null,null,null);
            h.Patch(AccessTools.Method(canvas,"PaintLongCommand"),null,null,new HarmonyMethod(typeof(PuzzleNotebook),"FitRows"),null,null);
        }
        static bool IsPuzzle(object c) { return Scenario(c) && (int)Get(c,"SentakuStock")>0 && ((string[])Get(c,"Sentaku_nafuda"))[0]==Caption; }
        static int Origin(int original,object c) {
            if(!IsPuzzle(c)) return original;
            int height=(int)Get(null,"Height"),step=(int)Get(null,"FHeight")+2;
            return Math.Min(original,height-4-(int)Get(c,"SentakuStock")*step);
        }
        static IEnumerable<CodeInstruction> FitRows(IEnumerable<CodeInstruction> instructions) {
            var code=new List<CodeInstruction>(instructions);int matches=0;
            for(int i=0;i+2<code.Count;i++) {
                if(code[i].opcode!=OpCodes.Ldarg_0 || code[i+1].opcode!=OpCodes.Ldfld ||
                    !Equals(code[i+1].operand,AccessTools.Field(canvas,"SentakuStock")) || code[i+2].opcode!=OpCodes.Pop) continue;
                // This join follows all native origin branches. Move branch labels onto our adjustment.
                var first=new CodeInstruction(OpCodes.Ldloc_3);first.labels.AddRange(code[i].labels);code[i].labels.Clear();
                code.InsertRange(i,new[]{first,new CodeInstruction(OpCodes.Ldarg_0),
                    new CodeInstruction(OpCodes.Call,AccessTools.Method(typeof(PuzzleNotebook),"Origin")),new CodeInstruction(OpCodes.Stloc_3)});
                i+=4;matches++;
            }
            if(matches!=1) throw new InvalidOperationException("Long menu origin join mismatch: "+matches);
            return code;
        }
        static bool Scenario(object c) { return (string)Get(c,"SaveScenarioFileName")=="c3-02c"; }
        static void AddChoice(object __instance) {
            if(!Scenario(__instance) || (int)Get(__instance,"Pos")!=MenuEnd) return;
            // The six original SENTAKUSI instructions append after this entry, preserving their labels.
            if((int)Get(__instance,"SentakuStock")!=0) throw new InvalidOperationException("Unexpected puzzle choice initialization");
            ((string[])Get(__instance,"Sentaku_nafuda"))[0]=Caption;
            var jump=jumps.GetOrCreateValue(__instance);
            var labels=(int[])Get(__instance,"LabelIndex");
            if(!ReferenceEquals(labels,jump.Labels)) {
                jump.Slot=labels.Length;Array.Resize(ref labels,labels.Length+1);
                labels[jump.Slot]=NotebookOpcode;jump.Labels=labels;Set(__instance,"LabelIndex",labels);
            }
            ((int[])Get(__instance,"Sentaku_index"))[0]=jump.Slot;
            Set(__instance,"SentakuStock",1);
        }
        static void BeforeNotebook(object __instance,out bool __state) {
            Jump jump;
            __state=Scenario(__instance) && (int)Get(__instance,"Pos")==NotebookOpcode+1 &&
                jumps.TryGetValue(__instance,out jump) && ReferenceEquals(Get(__instance,"LabelIndex"),jump.Labels) &&
                (int)Get(__instance,"SentakuStock")==0 && (int)Get(__instance,"CommandCursorPos")==0 &&
                ((int[])Get(__instance,"Sentaku_index"))[0]==jump.Slot &&
                ((string[])Get(__instance,"Sentaku_nafuda"))[0]==Caption;
        }
        static void AfterNotebook(object __instance,bool __state) {
            if(__state) Set(__instance,"ListBackPos",MenuStart);
        }
    }
}
