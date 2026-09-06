using System;
using System.Collections.Generic;
using System.Reflection;

namespace Kibu1ZhCN
{
    // Session-only UI state. No script offsets, flags or save files are modified.
    public static class MenuSelectionMemory
    {
        private const BindingFlags Members = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
        private sealed class Access
        {
            public FieldInfo Cmd, Scene, Truth, Scenario, ScSelect, ScStr, ScInt, Select;
        }
        private sealed class State
        {
            public readonly Dictionary<string,Family> Menus = new Dictionary<string,Family>();
            public readonly List<Family> Families = new List<Family>();
            public string Key;
            public string[] Options;
            public string[] Labels;
            public Family Current;
        }
        private sealed class Family
        {
            public string Context, LastChoice, LastLabel, LastInstruction;
            public readonly List<string[]> Variants = new List<string[]>();
        }
        private static readonly Dictionary<Type,Access> accesses = new Dictionary<Type,Access>();
        private static readonly Dictionary<object,State> states = new Dictionary<object,State>();
        private static FieldInfo Field(Type type, string name)
        {
            FieldInfo field = type.GetField(name,Members);
            if (field == null) throw new MissingFieldException(type.FullName,name);
            return field;
        }
        private static Access GetAccess(Type type)
        {
            Access access;
            if (accesses.TryGetValue(type,out access)) return access;
            access = new Access { Cmd=Field(type,"Cmd"), Scene=Field(type,"Scene"),
                Truth=Field(type,"Truth"), Scenario=Field(type,"Scenario"), ScSelect=Field(type,"ScSelect"),
                ScStr=Field(type,"ScStr"), ScInt=Field(type,"ScInt"), Select=Field(type,"Select") };
            accesses.Add(type,access);
            return access;
        }
        public static void Initialize(Type type) { GetAccess(type); }
        public static void Reset() { states.Clear(); }
        private static bool IsMenu(object canvas, Access access)
        {
            int command = Convert.ToInt32(access.Cmd.GetValue(canvas));
            return command >= 105 && command < 130 &&
                Convert.ToInt32(access.Scene.GetValue(canvas)) == 2 && (bool)access.Truth.GetValue(canvas);
        }
        public static void RecordMenu(object canvas, int instruction)
        {
            Access access = GetAccess(canvas.GetType());
            State state;
            if (!states.TryGetValue(canvas,out state)) { state = new State(); states.Add(canvas,state); }
            state.Key = null; state.Options = null; state.Current = null;
            if (!IsMenu(canvas,access)) return;
            int command = Convert.ToInt32(access.Cmd.GetValue(canvas));
            int count = command - (command < 120 ? 105 : 120) + 1;
            string[] labels = (string[])access.ScStr.GetValue(canvas);
            int[] targets = (int[])access.ScInt.GetValue(canvas);
            if (labels.Length < count || targets.Length <= count) return;
            state.Key = access.Scenario.GetValue(canvas) + ":" + access.ScSelect.GetValue(canvas) + ":" + instruction;
            string context = access.Scenario.GetValue(canvas) + ":" + access.ScSelect.GetValue(canvas) + ":" +
                (command < 120 ? "grid" : "list") + ":" + targets[count];
            state.Options = new string[count];
            state.Labels = new string[count];
            for (int i=0; i<count; i++)
            {
                state.Labels[i] = labels[i];
                state.Options[i] = labels[i] == null ? null : targets[i] + ":" + labels[i];
            }
            Family family;
            if (!state.Menus.TryGetValue(state.Key,out family))
            {
                // Conditional scripts emit a different menu instruction when
                // clues appear. Match their shared actions AND return destination.
                Family candidate=null; bool ambiguous=false;
                foreach (Family known in state.Families)
                {
                    if (known.Context != context) continue;
                    bool matches=false;
                    foreach (string[] variant in known.Variants)
                        if (Related(variant,state.Options)) { matches=true; break; }
                    if (!matches) continue;
                    if (candidate!=null && candidate!=known) { ambiguous=true; break; }
                    candidate=known;
                }
                family=ambiguous ? null : candidate;
                if (family==null)
                {
                    family=new Family { Context=context };
                    state.Families.Add(family);
                }
                state.Menus[state.Key]=family;
            }
            bool seen=false;
            foreach (string[] variant in family.Variants)
                if (String.Join("\n",variant)==String.Join("\n",state.Options)) { seen=true; break; }
            if (!seen) family.Variants.Add((string[])state.Options.Clone());
            state.Current=family;
        }
        private static bool Related(string[] left,string[] right)
        {
            var a=new HashSet<string>(left); var b=new HashSet<string>(right);
            a.Remove(null); b.Remove(null);
            int smaller=Math.Min(a.Count,b.Count);
            a.IntersectWith(b);
            // Subsets cover even one-item menus; allow one changed action in
            // larger variants when at least two original actions still agree.
            return smaller>0 && (a.Count==smaller || (a.Count>=2 && a.Count>=smaller-1));
        }
        public static int Restore(object canvas)
        {
            State state;
            if (!states.TryGetValue(canvas,out state) || state.Key == null ||
                state.Current==null || state.Current.LastChoice==null) return 0;
            int found = Array.IndexOf(state.Options,state.Current.LastChoice);
            // A newly unlocked variant may update the dialogue branch of an
            // existing item (e.g. the TV). A unique label in this same family wins.
            if (found<0 && state.Current.LastInstruction!=state.Key)
            {
                int named=Array.IndexOf(state.Labels,state.Current.LastLabel);
                if (named>=0 && Array.LastIndexOf(state.Labels,state.Current.LastLabel)==named) found=named;
            }
            return found < 0 ? 0 : found;
        }
        public static void Remember(object canvas)
        {
            State state;
            if (!states.TryGetValue(canvas,out state) || state.Key == null) return;
            Access access = GetAccess(canvas.GetType());
            if (!IsMenu(canvas,access)) return;
            int index = ((sbyte[])access.Select.GetValue(canvas))[1];
            if (index >= 0 && index < state.Options.Length && state.Options[index] != null)
            {
                state.Current.LastChoice=state.Options[index];
                state.Current.LastLabel=state.Labels[index];
                state.Current.LastInstruction=state.Key;
            }
        }
    }
}
