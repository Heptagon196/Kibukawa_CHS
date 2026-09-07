using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;

namespace Kibu1ZhCN
{
    // The two canvases have identical field names but unrelated declaring types.
    // Never reuse a FieldInfo from one part on an instance of the other part.
    public static class DualCanvasHooks
    {
        private sealed class Access
        {
            public int FirstScenario;
            public FieldInfo Cursor, Scenario, Selected, Strings, Opcode;
        }
        private static readonly Dictionary<Type, Access> access = new Dictionary<Type, Access>();
        private static readonly HashSet<string> translatedScripts = new HashSet<string>();
        private static TranslationCatalog catalog;
        public static Type[] CanvasTypes { get; private set; }

        private static FieldInfo Field(Type type, string name)
        {
            var result = type.GetField(name, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            if (result == null) throw new MissingFieldException(type.FullName, name);
            return result;
        }

        public static void Initialize(TranslationPack pack, TranslationCatalog translations, Type first, Type second)
        {
            Reset();
            if (first == null || second == null || first.FullName != "appli1.CanvasEx" || second.FullName != "appli2.CanvasEx")
                throw new MissingMemberException("Both fourth-game CanvasEx types are required");
            CanvasTypes = new[] { first, second };
            for (int part = 0; part < CanvasTypes.Length; part++)
            {
                Type type = CanvasTypes[part];
                access.Add(type, new Access { FirstScenario=part*4, Cursor=Field(type,"ScCur"),
                    Scenario=Field(type,"Scenario"), Selected=Field(type,"ScSelect"),
                    Strings=Field(type,"ScStr"), Opcode=Field(type,"Cmd") });
                DialogueReflow.Initialize(type);
                MenuSelectionMemory.Initialize(type);
            }
            catalog = translations;
            foreach (var entry in pack.scripts ?? new ScriptEntry[0])
                if (entry.source != entry.target) translatedScripts.Add(entry.script);
        }

        public static string ScriptName(object canvas)
        {
            Access binding = access[canvas.GetType()];
            int selected = Convert.ToInt32(binding.Selected.GetValue(canvas));
            // Both physical subscn copies are byte-identical (verified by build).
            if (selected == 1 || selected == 2) return "subscn_" + selected;
            if (selected != 0) return null;
            int scenario = Convert.ToInt32(binding.Scenario.GetValue(canvas));
            return scenario >= binding.FirstScenario && scenario < binding.FirstScenario+4 ? "scn"+scenario : null;
        }

        public static int BeforeRead(object canvas) { return (int)access[canvas.GetType()].Cursor.GetValue(canvas); }

        public static int AfterRead(object canvas, int instruction)
        {
            Access binding = access[canvas.GetType()];
            string script = ScriptName(canvas);
            string[] values = (string[])binding.Strings.GetValue(canvas);
            int opcode = (int)binding.Opcode.GetValue(canvas);
            DialogueReflow.RecordSource(canvas, opcode, values.Length == 0 ? null : values[0],
                false, FixedCardLayout.IsActive(script, instruction));
            int count = script == null ? 0 : catalog.ApplyScript(script, instruction, opcode, values);
            MenuSelectionMemory.RecordMenu(canvas, instruction);
            // Only ScStr elements change. ScCur/ScData/ScInt and save offsets stay original.
            return count;
        }

        public static IEnumerator AfterScript(object canvas, IEnumerator original)
        {
            string script = ScriptName(canvas);
            if (!DialogueReflow.IsBypassed && script != null && translatedScripts.Contains(script))
                return DialogueReflow.Wrap(canvas, original);
            return original;
        }

        public static void ResetSession()
        {
            DialogueReflow.Reset();
            MenuSelectionMemory.Reset();
        }
        public static void Reset()
        {
            ResetSession();
            access.Clear(); translatedScripts.Clear(); catalog = null; CanvasTypes = new Type[0];
        }
    }
}
