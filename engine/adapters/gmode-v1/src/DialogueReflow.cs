using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Text;

namespace Kibu1ZhCN
{
    // Shared with the offline replay. Width is the game's advance, not the ink
    // bounding box of an individual Unifont glyph.
    public static class DialogueLayout
    {
        // CanvasEx keeps the original 44px left origin. A ten-full-glyph line
        // spans 160px and leaves 36px to the right on the 240px canvas.
        public const int MaximumHalfCells = 20;
        public const int MaximumCharacters = 20;
        private const string Closing = "，。！？；：、．｡､｣･﹐﹑﹒﹔﹕﹖﹗）］｝〉》」』】〕〗〙〛’”％%!?;:,.…";
        private const string Opening = "（［｛〈《「｢『【〔〖〘〚‘“";
        public static int HalfWidth(char value)
        {
            return ((value >= ' ' && value <= '~') || (value >= '\uff66' && value <= '\uff9f')) ? 1 : 2;
        }
        public static int Width(string value)
        {
            int width = 0;
            if (value != null) foreach (char character in value) width += HalfWidth(character);
            return width;
        }
        public static bool IsClosingPunctuation(char value) { return Closing.IndexOf(value) >= 0 || value == ')' || value == ']' || value == '}'; }
        public static bool IsOpeningPunctuation(char value) { return Opening.IndexOf(value) >= 0 || value == '(' || value == '[' || value == '{'; }
        public static bool HasBreakPunctuation(string value)
        {
            if (string.IsNullOrEmpty(value)) return false;
            int last = value.Length - 1;
            while (last >= 0 && char.IsWhiteSpace(value[last])) last--;
            return last >= 0 && IsClosingPunctuation(value[last]);
        }
        public static int FitPrefix(string value, int availableHalfCells, int availableCharacters)
        {
            int count = 0, width = 0;
            while (count < value.Length && count < availableCharacters && width + HalfWidth(value[count]) <= availableHalfCells)
                width += HalfWidth(value[count++]);
            // Wrap strictly at capacity; punctuation never moves an earlier glyph.
            return count;
        }
    }

    // The original interpreter stores only one currently animating row. Execute
    // each fitting run through its own original Script(72) coroutine so wrapping
    // does not skip typewriter animation, color changes, or the game's input loop.
    // Script bytes, jump addresses and save offsets are never rewritten.
    public static class DialogueReflow
    {
        private const BindingFlags Members = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
        private sealed class Access
        {
            public FieldInfo Cmd, Strings, Integers, Truth, NameId, StartLine, Text, Colors, Lengths, Position, TextColor, Names, Flags, Paint, Scene;
            public MethodInfo Script, ExeText;
        }
        private sealed class State
        {
            public bool PendingBreak, HasDialogue, WaitSatisfied, NewInteraction;
            public int InteractionRows;
            public string SourceTail, ReadSource;
            // Track ORIGINAL rows, not the shorter translated fragments. A whole
            // colored row followed by default-color quoted speech is an inline
            // speaker header. No names, palette indices or script offsets needed.
            public string SourceLine;
            public int SourceLineColor;
            public bool SourceLineColored, PendingSpeakerBreak;
            public void AddSource(string source, int color, int defaultColor)
            {
                if (string.IsNullOrWhiteSpace(source)) return;
                if (SourceLine == null) { SourceLineColor = color; SourceLineColored = color != defaultColor; }
                else SourceLineColored &= color == SourceLineColor && color != defaultColor;
                SourceLine = (SourceLine ?? "") + source;
            }
            public void EndSourceLine()
            {
                if (SourceLine != null)
                    PendingSpeakerBreak = SourceLineColored && !StartsSpeech(SourceLine) && !DialogueLayout.HasBreakPunctuation(SourceLine);
                SourceLine = null;
                SourceLineColored = false;
            }
            public int ReadOpcode = -1;
            public bool ReadStartsChat;
            public bool ReadFixedCard;
            public void Clear()
            {
                PendingBreak = HasDialogue = WaitSatisfied = NewInteraction = false;
                InteractionRows = 0;
                SourceTail = SourceLine = null;
                SourceLineColored = PendingSpeakerBreak = false;
            }
        }
        private struct Glyph
        {
            public char Character;
            public sbyte Color;
            public Glyph(char character, sbyte color) { Character = character; Color = color; }
        }
        private static readonly Dictionary<Type, Access> accesses = new Dictionary<Type, Access>();
        private static readonly Dictionary<object, State> states = new Dictionary<object, State>();
        private static int bypass;
        public static bool IsBypassed { get { return bypass != 0; } }

        private static FieldInfo Field(Type type, string name)
        {
            FieldInfo value = type.GetField(name, Members);
            if (value == null) throw new MissingFieldException(type.FullName, name);
            return value;
        }
        private static Access GetAccess(Type type)
        {
            Access value;
            if (accesses.TryGetValue(type, out value)) return value;
            value = new Access {
                Cmd = Field(type, "Cmd"), Strings = Field(type, "ScStr"), Integers = Field(type, "ScInt"),
                Truth = Field(type, "Truth"), NameId = Field(type, "NameID"), StartLine = Field(type, "TextLine"),
                Text = Field(type, "Text"), Colors = Field(type, "TextC"), Lengths = Field(type, "TextLen"),
                Position = Field(type, "TextPos"), TextColor = Field(type, "TextColor"), Names = Field(type, "Name"),
                Flags = Field(type, "Flag"), Paint = Field(type, "PaintValue"), Scene = type.GetField("Scene", Members),
                Script = type.GetMethod("Script", Members, null, Type.EmptyTypes, null),
                ExeText = type.GetMethod("ExeText", Members, null, new [] { typeof(string), typeof(int) }, null)
            };
            if (value.Script == null || value.Script.ReturnType != typeof(IEnumerator) || value.ExeText == null)
                throw new MissingMethodException(type.FullName, "Script / ExeText");
            accesses.Add(type, value);
            return value;
        }
        private static State GetState(object canvas)
        {
            State state;
            if (!states.TryGetValue(canvas, out state)) { state = new State(); states.Add(canvas, state); }
            return state;
        }
        public static void Initialize(Type canvasType) { GetAccess(canvasType); }
        public static void Reset() { states.Clear(); bypass = 0; }
        public static void RecordSource(object canvas, int opcode, string sourceText, bool startsChat = false, bool fixedCard = false)
        {
            State state = GetState(canvas);
            state.ReadOpcode = opcode;
            state.ReadSource = sourceText;
            state.ReadStartsChat = startsChat;
            state.ReadFixedCard = fixedCard;
        }
        public static void AfterExeText(object canvas, string text, int type)
        {
            if (text != null || (type != 1 && type != 2)) return;
            State state = GetState(canvas);
            state.Clear();
        }
        public static IEnumerator Wrap(object canvas, IEnumerator original)
        {
            return Execute(canvas, GetAccess(canvas.GetType()), GetState(canvas), original);
        }
        private static bool StartsSpeech(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return false;
            char first = text.TrimStart()[0];
            return first == '｢' || first == '「' || first == '“' || first == '\"';
        }
        private static IEnumerator Execute(object canvas, Access access, State state, IEnumerator original)
        {
            int command = (int)access.Cmd.GetValue(canvas);
            if (state.ReadFixedCard)
            {
                state.Clear();
                yield return original;
                state.Clear();
                yield break;
            }
            if (!(bool)access.Truth.GetValue(canvas) || (access.Scene != null && Convert.ToInt32(access.Scene.GetValue(canvas)) != 2))
            {
                yield return original;
                yield break;
            }
            if (command == 72 || command == 82 || command == 83)
            {
                string value;
                int[] args = (int[])access.Integers.GetValue(canvas);
                if (command == 82) value = ((sbyte[])access.Flags.GetValue(canvas))[args[0]].ToString();
                else if (command == 83) value = ((string[])access.Names.GetValue(canvas))[args[0]];
                else value = ((string[])access.Strings.GetValue(canvas))[0];
                string source = (command == 72 && state.ReadOpcode == command) ? state.ReadSource : value;
                if (!string.IsNullOrEmpty(value))
                {
                    // Chat headers are structural boundaries, even when the
                    // previous message ends in a name, emoticon or laughter w.
                    if (command==72 && state.ReadStartsChat && state.HasDialogue)
                        state.PendingBreak=true;
                    sbyte[] palette = (sbyte[])access.TextColor.GetValue(canvas);
                    sbyte color = palette[1];
                    if (state.PendingSpeakerBreak && color == palette[0] && StartsSpeech(source))
                        state.PendingBreak = true;
                    state.PendingSpeakerBreak = false;
                    state.AddSource(source, color, palette[0]);
                    yield return Write(canvas, access, state, value, color);
                }
                else yield return original;
                if (!string.IsNullOrEmpty(source)) state.SourceTail = source;
                yield break;
            }
            if ((command == 77 || command == 78) && state.HasDialogue)
            {
                if (command == 78)
                {
                    yield return OriginalCommand(canvas, access, 79, null, null);
                    state.WaitSatisfied = true;
                    state.NewInteraction = true;
                }
                else
                {
                    // Even a suppressed 77 must execute Script's common epilogue
                    // (Else=false). Command 0 is an interpreter no-op with that
                    // same epilogue, so branch state remains exactly as before.
                    yield return OriginalCommand(canvas, access, 0, null, null);
                }
                // A punctuation break in Japanese is only useful when the
                // translated clause ends there too. A shorter Chinese fragment
                // without punctuation should still join the following fragment.
                state.PendingBreak |= DialogueLayout.HasBreakPunctuation(state.SourceTail) && DialogueLayout.HasBreakPunctuation(Row(canvas, access));
                state.SourceTail = null;
                state.EndSourceLine();
                yield break;
            }
            if (command == 79)
            {
                yield return original;
                state.WaitSatisfied = true;
                state.NewInteraction = state.HasDialogue;
                yield break;
            }
            // The menu interpreter owns its row/column indices. Never wrap its
            // ExeText calls. Changes of speaker and explicit clears also reset us.
            bool clears = command == 71 || command == 73 || command == 75 || command == 76 || (command >= 105 && command < 130);
            if (clears) state.Clear();
            yield return original;
            if (clears) state.Clear();
        }
        private static string Row(object canvas, Access access)
        {
            int row = ((sbyte[])access.Position.GetValue(canvas))[0];
            return new string(((char[][])access.Text.GetValue(canvas))[row], 0, ((sbyte[])access.Lengths.GetValue(canvas))[row]);
        }
        private static string Characters(List<Glyph> glyphs)
        {
            var text = new StringBuilder(glyphs.Count);
            foreach (Glyph glyph in glyphs) text.Append(glyph.Character);
            return text.ToString();
        }
        private static IEnumerator Write(object canvas, Access access, State state, string value, sbyte color)
        {
            // Confirmation resets the unread-row budget, NOT the screen.
            // History stays visible until the original buffer scrolls it away.
            if (state.NewInteraction)
            {
                state.NewInteraction = false;
                state.InteractionRows = 0;
            }
            var pending = new List<Glyph>();
            foreach (char character in value) pending.Add(new Glyph(character, color));
            if (state.PendingBreak)
            {
                state.PendingBreak = false;
                // A translated punctuation-only command belongs to the preceding
                // sentence even if its original Japanese row ended in punctuation.
                if (Row(canvas, access).Length > 0 && !DialogueLayout.IsClosingPunctuation(pending[0].Character))
                    yield return Advance(canvas, access, state);
            }
            while (pending.Count > 0)
            {
                string line = Row(canvas, access);
                string remaining = Characters(pending);
                int take = DialogueLayout.FitPrefix(remaining, DialogueLayout.MaximumHalfCells - DialogueLayout.Width(line), DialogueLayout.MaximumCharacters - line.Length);
                if (take == 0)
                {
                    yield return Advance(canvas, access, state);
                    continue;
                }
                int consumed = 0;
                while (consumed < take)
                {
                    sbyte runColor = pending[consumed].Color;
                    int end = consumed + 1;
                    while (end < take && pending[end].Color == runColor) end++;
                    var text = new StringBuilder(end - consumed);
                    for (int i = consumed; i < end; i++) text.Append(pending[i].Character);
                    yield return OriginalCommand(canvas, access, 72, text.ToString(), runColor);
                    if (state.InteractionRows == 0) state.InteractionRows = 1;
                    state.HasDialogue = true;
                    state.WaitSatisfied = false;
                    consumed = end;
                }
                pending.RemoveRange(0, take);
                if (pending.Count > 0) yield return Advance(canvas, access, state);
            }
        }
        private static IEnumerator Advance(object canvas, Access access, State state)
        {
            // TextLine is the actual body origin: ordinary dialogue has five
            // rows (four with a speaker), while full-screen text can use nine.
            int capacity = Math.Max(1, 9 - Convert.ToInt32(access.StartLine.GetValue(canvas)));
            if (state.InteractionRows >= capacity)
            {
                if (!state.WaitSatisfied) yield return OriginalCommand(canvas, access, 79, null, null);
                state.InteractionRows = 0;
                state.WaitSatisfied = true;
            }
            // Original newline scrolls only when its physical buffer is full.
            // At this point every row pushed out belongs to acknowledged history.
            access.ExeText.Invoke(canvas, new object[] { null, 0 });
            if (state.InteractionRows > 0) state.InteractionRows++;
            access.Paint.SetValue(canvas, (int)access.Paint.GetValue(canvas) | 127);
        }
        private static IEnumerator OriginalCommand(object canvas, Access access, int command, string value, sbyte? color)
        {
            int previousCommand = (int)access.Cmd.GetValue(canvas);
            string[] strings = (string[])access.Strings.GetValue(canvas);
            sbyte[] colors = (sbyte[])access.TextColor.GetValue(canvas);
            string previousText = strings[0];
            sbyte previousColor = colors[1];
            IEnumerator routine = null;
            try
            {
                access.Cmd.SetValue(canvas, command);
                if (command == 72) strings[0] = value;
                if (color.HasValue) colors[1] = color.Value;
                bypass++;
                try { routine = (IEnumerator)access.Script.Invoke(canvas, null); }
                finally { bypass--; }
                yield return routine;
            }
            finally
            {
                IDisposable disposable = routine as IDisposable;
                if (disposable != null) disposable.Dispose();
                access.Cmd.SetValue(canvas, previousCommand);
                strings[0] = previousText;
                colors[1] = previousColor;
            }
        }
    }
}
