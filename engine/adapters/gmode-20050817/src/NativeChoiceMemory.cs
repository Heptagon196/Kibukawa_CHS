using System;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using HarmonyLib;

namespace Kibukawa.Engine.Gmode20050817
{
    // Extend the game's own table to cancellable text menus. Do not change the
    // return label: it is also used by the native back-button handler.
    internal static class NativeChoiceMemory
    {
        static FieldInfo returnLabel, normal, longText, position, script, cursor, top, stock;
        static readonly ConditionalWeakTable<object,Kibukawa.Engine.GmodeV2.MenuMemory> sessions = new ConditionalWeakTable<object,Kibukawa.Engine.GmodeV2.MenuMemory>();
        sealed class MenuIdentity { internal int Start; }
        static readonly ConditionalWeakTable<object, MenuIdentity> identities = new ConditionalWeakTable<object, MenuIdentity>();
        static void BeginMenu(object __instance)
        {
            NativePagination.Begin(__instance);
            identities.GetOrCreateValue(__instance).Start = (int)position.GetValue(__instance);
        }
        static int MemoryKey(object canvas)
        {
            // Cancellable menus were not in the native table before our extension.
            // They may branch to the same terminator as an icon menu or another
            // topic menu. Reserve negative keys for their own opening opcode.
            if ((int)returnLabel.GetValue(canvas) != -1 &&
                ((bool)normal.GetValue(canvas) || (bool)longText.GetValue(canvas)))
            {
                MenuIdentity identity;
                if (!identities.TryGetValue(canvas, out identity) || identity.Start <= 0)
                    throw new InvalidOperationException("Text menu identity was not captured");
                return -identity.Start;
            }
            return (int)position.GetValue(canvas);
        }
        internal static void Install(Harmony harmony, Type canvas)
        {
            NativePagination.Initialize(canvas);
            script=AccessTools.Field(canvas,"Script");
            cursor=AccessTools.Field(canvas,"CommandCursorPos");
            top=AccessTools.Field(canvas,"CommandTop");
            stock=AccessTools.Field(canvas,"SentakuStock");
            returnLabel = AccessTools.Field(canvas, "komando_modori");
            position = AccessTools.Field(canvas, "Pos");
            normal = AccessTools.Field(canvas, "NowCommand");
            longText = AccessTools.Field(canvas, "NowChobunCommand");
            if (returnLabel == null || normal == null || longText == null || position == null)
                throw new MissingFieldException("Native choice memory fields");
            foreach (string method in new[] { "KOMANDO", "CHOUBUN_KOMANDO" })
                harmony.Patch(AccessTools.Method(canvas, method),
                    prefix: new HarmonyMethod(typeof(NativeChoiceMemory), "BeginMenu"));
            foreach (string method in new[] { "Game_adv", "Game_command" })
                harmony.Patch(AccessTools.EnumeratorMoveNext(AccessTools.Method(canvas, method)),
                    transpiler: new HarmonyMethod(typeof(NativeChoiceMemory), "Rewrite"));
        }
        static int RecordGate(object canvas)
        {
            if (NativePagination.Record(canvas, false)) return 0;
            int gate=BasicGate(canvas);
            if(gate==-1)
            {
                sessions.GetOrCreateValue(canvas).Record((sbyte[])script.GetValue(canvas),MemoryKey(canvas),(int)cursor.GetValue(canvas),(int)top.GetValue(canvas));
            }
            return gate;
        }
        static int BackGate(object canvas)
        {
            NativePagination.Record(canvas, true);
            return (int)returnLabel.GetValue(canvas);
        }
        static int MemoryGate(object canvas)
        {
            if (NativePagination.Restore(canvas)) return 0;
            int gate=BasicGate(canvas);
            if(gate==-1)
            {
                int savedCursor,savedTop;
                if(sessions.GetOrCreateValue(canvas).Restore((sbyte[])script.GetValue(canvas),MemoryKey(canvas),(int)stock.GetValue(canvas),out savedCursor,out savedTop))
                {
                    cursor.SetValue(canvas,savedCursor);
                    top.SetValue(canvas,savedTop);
                    return 0;
                }
            }
            return gate;
        }
        static int BasicGate(object canvas)
        {
            if ((bool)normal.GetValue(canvas) || (bool)longText.GetValue(canvas)) return -1;
            return (int)returnLabel.GetValue(canvas);
        }
        static IEnumerable<CodeInstruction> Rewrite(IEnumerable<CodeInstruction> instructions, MethodBase __originalMethod)
        {
            var code = new List<CodeInstruction>(instructions);
            int count = 0;
            bool isCommand = __originalMethod.DeclaringType.Name.Contains("Game_command");
            int backGuards = 0;
            if (isCommand)
                for (int i = 0; i + 2 < code.Count; i++)
                    if (code[i].opcode == OpCodes.Ldfld && Equals(code[i].operand, returnLabel)
                        && code[i+1].opcode == OpCodes.Ldc_I4_M1
                        && (code[i+2].opcode == OpCodes.Beq || code[i+2].opcode == OpCodes.Beq_S))
                    {
                        code[i].opcode = OpCodes.Call;
                        code[i].operand = AccessTools.Method(typeof(NativeChoiceMemory), "BackGate");
                        backGuards++;
                    }
            if (isCommand && backGuards != 1) throw new InvalidOperationException("Unexpected cancel guard count");
            for (int i = 0; i + 3 < code.Count; i++)
            {
                // Only the guard immediately before a native memory-table loop.
                // In particular, leave the beq guard on the back-button path intact.
                if (code[i].opcode != OpCodes.Ldfld || !Equals(code[i].operand, returnLabel)
                    || code[i+1].opcode != OpCodes.Ldc_I4_M1
                    || (code[i+2].opcode != OpCodes.Bne_Un && code[i+2].opcode != OpCodes.Bne_Un_S)
                    || code[i+3].opcode != OpCodes.Ldc_I4_0) continue;
                bool table = false;
                for (int j = i + 4; j < Math.Min(i + 12, code.Count); j++)
                {
                    var field = code[j].operand as FieldInfo;
                    if (code[j].opcode == OpCodes.Ldfld && field != null && field.Name == "Sentaku_kioku_id") table = true;
                }
                if (!table) throw new InvalidOperationException("Choice memory guard no longer precedes native table");
                code[i].opcode = OpCodes.Call;
                code[i].operand = AccessTools.Method(typeof(NativeChoiceMemory), isCommand ? "RecordGate" : "MemoryGate");
                int keys = 0;
                bool recording = __originalMethod.DeclaringType.Name.Contains("Game_command");
                for (int j = i + 4; j < Math.Min(i + (recording ? 70 : 41), code.Count); j++)
                    if (code[j].opcode == OpCodes.Ldfld && Equals(code[j].operand, position))
                    {
                        code[j].opcode = OpCodes.Call;
                        code[j].operand = AccessTools.Method(typeof(NativeChoiceMemory), "MemoryKey");
                        keys++;
                    }
                if (keys != (recording ? 2 : 1))
                    throw new InvalidOperationException("Unexpected menu identity load count: " + keys);
                count++;
            }
            int expected = __originalMethod.DeclaringType.Name.Contains("Game_adv") ? 4 : 1;
            if (count != expected) throw new InvalidOperationException("Unexpected native choice memory guard count: " + count);
            return code;
        }
    }
}
