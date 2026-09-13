using System;
using System.Collections.Generic;
using System.Reflection.Emit;
using HarmonyLib;
namespace Kibukawa.Engine.Gmode20050817
{
    internal static class NativeMenuPosition
    {
        static int firstRow;
        internal static void Install(Harmony harmony, Type canvas, int firstOptionY)
        {
            firstRow=firstOptionY;
            harmony.Patch(AccessTools.Method(canvas,"PaintCommand"),transpiler:new HarmonyMethod(typeof(NativeMenuPosition),"Rewrite"));
        }
        static IEnumerable<CodeInstruction> Rewrite(IEnumerable<CodeInstruction> instructions)
        {
            var code=new List<CodeInstruction>(instructions);int matches=0;
            for(int i=2;i<code.Count;i++)
            {
                // Replace only the bottom-menu origin assignment. Native loops,
                // option count, selection indices and highlight drawing stay intact.
                if(code[i].opcode!=OpCodes.Stloc_S || code[i-1].opcode!=OpCodes.Sub || code[i-2].opcode!=OpCodes.Ldc_I4_S || Convert.ToInt32(code[i-2].operand)!=14) continue;
                object local=code[i].operand;
                code[i].opcode=OpCodes.Pop;code[i].operand=null;
                code.Insert(i+1,new CodeInstruction(OpCodes.Ldc_I4,firstRow));
                code.Insert(i+2,new CodeInstruction(OpCodes.Stloc_S,local));
                i+=2;matches++;
            }
            if(matches!=1) throw new InvalidOperationException("Native menu origin pattern mismatch: "+matches);
            return code;
        }
    }
}
