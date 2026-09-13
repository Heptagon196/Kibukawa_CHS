using System;
using System.Collections.Generic;
using System.Reflection;
using System.Reflection.Emit;
using System.Runtime.CompilerServices;
using HarmonyLib;
using Kibukawa.Engine.GmodeV2;

namespace Kibukawa.Engine.Gmode20050117
{
    /// <summary>
    /// Extend the game's own choice-memory table to cancellable text menus.
    ///
    /// CanvasEx guards both the record and the restore path with
    /// ``if (komando_modori != -1) skip``, so a menu that has a return target never
    /// remembers where the cursor was. The transpiler rewrites only that guard read,
    /// and the two ``Pos`` reads that identify a table slot, leaving the memory loops,
    /// their tables, the return targets and the cancel branch byte-for-byte intact.
    ///
    /// Unlike 20050817 this version has no pagination and no coroutines here:
    /// Game_adv and Game_command are plain methods, so the transpiler patches them
    /// directly. It has no back-button guard to rewrite, because there is no page
    /// memory to record on the cancel path.
    /// </summary>
    internal static class NativeChoiceMemory
    {
        private static FieldInfo returnLabel, normal, longText, position, script, cursor, top, stock;
        private static readonly ConditionalWeakTable<object, MenuMemory> sessions = new ConditionalWeakTable<object, MenuMemory>();
        private static readonly ConditionalWeakTable<object, MenuIdentity> identities = new ConditionalWeakTable<object, MenuIdentity>();

        private sealed class MenuIdentity { internal int Start; }

        // Verified against the shipped assembly: two guards with one identity read each
        // in Game_adv, one guard with two identity reads in Game_command.
        private const int AdvanceGuards = 2;
        private const int CommandGuards = 1;

        private static void BeginMenu(object __instance)
        {
            identities.GetOrCreateValue(__instance).Start = (int)position.GetValue(__instance);
        }

        private static int MemoryKey(object canvas)
        {
            // A cancellable text menu was never in the native table, and it can branch to
            // the same terminator as another menu. Reserve negative keys for the offset of
            // the call that opened it.
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

        private static int BasicGate(object canvas)
        {
            if ((bool)normal.GetValue(canvas) || (bool)longText.GetValue(canvas)) return -1;
            return (int)returnLabel.GetValue(canvas);
        }

        private static int RecordGate(object canvas)
        {
            int gate = BasicGate(canvas);
            if (gate == -1)
                sessions.GetOrCreateValue(canvas).Record((sbyte[])script.GetValue(canvas), MemoryKey(canvas),
                                                         (int)cursor.GetValue(canvas), (int)top.GetValue(canvas));
            return gate;
        }

        private static int MemoryGate(object canvas)
        {
            int gate = BasicGate(canvas);
            if (gate == -1)
            {
                int savedCursor, savedTop;
                if (sessions.GetOrCreateValue(canvas).Restore((sbyte[])script.GetValue(canvas), MemoryKey(canvas),
                                                              (int)stock.GetValue(canvas), out savedCursor, out savedTop))
                {
                    cursor.SetValue(canvas, savedCursor);
                    top.SetValue(canvas, savedTop);
                    return 0;
                }
            }
            return gate;
        }

        internal static void Install(Harmony harmony, Type canvas)
        {
            script = AccessTools.Field(canvas, "Script");
            cursor = AccessTools.Field(canvas, "CommandCursorPos");
            top = AccessTools.Field(canvas, "CommandTop");
            stock = AccessTools.Field(canvas, "SentakuStock");
            returnLabel = AccessTools.Field(canvas, "komando_modori");
            position = AccessTools.Field(canvas, "Pos");
            normal = AccessTools.Field(canvas, "NowCommand");
            longText = AccessTools.Field(canvas, "NowChobunCommand");
            foreach (FieldInfo field in new[] { script, cursor, top, stock, returnLabel, position, normal, longText })
                if (field == null) throw new MissingFieldException(canvas.FullName, "native choice memory field");
            foreach (string method in new[] { "KOMANDO", "CHOUBUN_KOMANDO" })
            {
                MethodInfo target = AccessTools.Method(canvas, method);
                if (target == null) throw new MissingMethodException(canvas.FullName, method);
                harmony.Patch(target, prefix: new HarmonyMethod(typeof(NativeChoiceMemory), "BeginMenu"));
            }
            foreach (string method in new[] { "Game_adv", "Game_command" })
            {
                MethodInfo target = AccessTools.Method(canvas, method);
                if (target == null) throw new MissingMethodException(canvas.FullName, method);
                harmony.Patch(target, transpiler: new HarmonyMethod(typeof(NativeChoiceMemory), "Rewrite"));
            }
        }

        private static IEnumerable<CodeInstruction> Rewrite(IEnumerable<CodeInstruction> instructions, MethodBase __originalMethod)
        {
            var code = new List<CodeInstruction>(instructions);
            bool recording = __originalMethod.Name == "Game_command";
            int guards = 0;
            for (int i = 0; i + 3 < code.Count; i++)
            {
                // Only the guard immediately before a native memory-table loop.
                if (code[i].opcode != OpCodes.Ldfld || !Equals(code[i].operand, returnLabel)
                    || code[i + 1].opcode != OpCodes.Ldc_I4_M1
                    || (code[i + 2].opcode != OpCodes.Bne_Un && code[i + 2].opcode != OpCodes.Bne_Un_S)
                    || code[i + 3].opcode != OpCodes.Ldc_I4_0) continue;
                bool table = false;
                for (int j = i + 4; j < Math.Min(i + 76, code.Count); j++)
                {
                    FieldInfo field = code[j].operand as FieldInfo;
                    if (code[j].opcode == OpCodes.Ldfld && field != null && field.Name == "Sentaku_kioku_id") table = true;
                }
                if (!table) throw new InvalidOperationException("Choice memory guard no longer precedes native table");
                code[i].opcode = OpCodes.Call;
                code[i].operand = AccessTools.Method(typeof(NativeChoiceMemory), recording ? "RecordGate" : "MemoryGate");
                int keys = 0;
                for (int j = i + 4; j < Math.Min(i + (recording ? 70 : 41), code.Count); j++)
                    if (code[j].opcode == OpCodes.Ldfld && Equals(code[j].operand, position))
                    {
                        code[j].opcode = OpCodes.Call;
                        code[j].operand = AccessTools.Method(typeof(NativeChoiceMemory), "MemoryKey");
                        keys++;
                    }
                int expectedKeys = recording ? 2 : 1;
                if (keys != expectedKeys)
                    throw new InvalidOperationException("Unexpected menu identity load count: " + keys + " (expected " + expectedKeys + ")");
                guards++;
            }
            int expected = recording ? CommandGuards : AdvanceGuards;
            if (guards != expected)
                throw new InvalidOperationException("Unexpected native choice memory guard count: " + guards + " (expected " + expected + ")");
            return code;
        }
    }
}
