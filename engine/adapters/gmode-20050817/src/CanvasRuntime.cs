using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text.RegularExpressions;
using BepInEx;
using HarmonyLib;
using UnityEngine;
using Kibukawa8.Runtime;
using Kibu1ZhCN;

namespace Kibukawa.Engine.Gmode20050817
{
    public abstract class CanvasRuntime : BaseUnityPlugin
    {
        protected static IDictionary<string, string> exactUi;
        protected static RuntimeLayout layout;
        protected Harmony harmony;
        protected static RuntimePack pack;
        protected static BitmapFontAtlas font;
        protected static BitmapFontAtlas smallFont;
        protected static Type canvasType;
        protected static FieldInfo drawOrigin, infoOwner;
        protected static bool ready;
        protected static CanvasRuntime instance;
        protected static readonly Dictionary<string, FieldInfo> fields = new Dictionary<string, FieldInfo>();
        protected static readonly ConditionalWeakTable<object, CanvasState> states = new ConditionalWeakTable<object, CanvasState>();
        protected static readonly Dictionary<string, RuntimeRow> infoRows = new Dictionary<string, RuntimeRow>(StringComparer.Ordinal);
        [ThreadStatic] protected static float drawScale;
        [ThreadStatic] protected static bool smallFontScope;
        [ThreadStatic] protected static string menuTitle;
        [ThreadStatic] protected static InfoState activeInfo;
        protected sealed class CanvasState
        {
            public sbyte[] Script;
            public ScriptTranslation Translation;
            public bool Dialogue;
            public bool Reflowed;
            public int SpeakerX = 10;
            public readonly HashSet<int> RollRows = new HashSet<int>();
        }
        public sealed class ReadState
        {
            public DisplayTranslation Display;
            public int Row;
        }
        public sealed class InfoState
        {
            public object Owner;
            public string Text;
            public int Count;
            public sbyte[] Raw, Colors;
            public int[] Positions;
            public int Width;
            public object ClipGraphics;
            public int TranslatedCount;
            public InfoState Previous;
        }
        protected static FieldInfo F(string name)
        {
            FieldInfo field;
            if (!fields.TryGetValue(name, out field))
            {
                field = AccessTools.Field(canvasType, name);
                if (field == null) throw new MissingFieldException(canvasType.FullName, name);
                fields.Add(name, field);
            }
            return field;
        }
        protected static int Number(object canvas, string name) { return Convert.ToInt32(F(name).GetValue(canvas)); }
        protected static string Hash(byte[] bytes)
        {
            using (SHA256 sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", "").ToLowerInvariant();
        }
        protected static CanvasState State(object canvas)
        {
            CanvasState state = states.GetValue(canvas, key => new CanvasState());
            sbyte[] script = (sbyte[])F("Script").GetValue(canvas);
            if (!ReferenceEquals(script, state.Script))
            {
                state.Script = script;
                state.Translation = null;
                state.Dialogue = false;
                state.RollRows.Clear();
                if (script != null)
                {
                    byte[] bytes = new byte[script.Length];
                    Buffer.BlockCopy(script, 0, bytes, 0, bytes.Length);
                    state.Translation = pack.Bind(bytes);
                    if (state.Translation != null) RegisterInfo(state.Translation);
                    if (state.Translation == null) instance.Logger.LogWarning("Unrecognized scenario; original display retained.");
                }
            }
            return state;
        }
        protected static void RegisterInfo(ScriptTranslation script)
        {
            foreach (DisplayTranslation display in script.Displays.Values)
                if (display.Opcode == 72 && display.Rows.Length == 1)
                {
                    RuntimeRow row = display.Rows[0], existing;
                    if (infoRows.TryGetValue(row.SourceText, out existing) && (existing.Text != row.Text || !Equal(existing.Colors, row.Colors)))
                        throw new InvalidDataException("Ambiguous INFO translations");
                    infoRows[row.SourceText] = row;
                }
        }
        protected static bool BeforeChoiceCenter(object __instance, object __0, int __1, int __2, int __3)
        {
            return DrawChoice(__instance, __0, __1, 0, __2, __3, true);
        }
        protected static bool BeforeChoiceLeft(object __instance, object __0, int __1, int __2, int __3, int __4)
        {
            return DrawChoice(__instance, __0, __1, __2, __3, __4, false);
        }
        protected static bool DrawChoice(object canvas, object graphics, int index, int x, int y, int color, bool centered)
        {
            if (!ready) return true;
            string text = ((string[])F("Sentaku_nafuda").GetValue(canvas))[index];
            if (String.IsNullOrEmpty(text)) return true;
            bool latin = false;
            foreach (char c in text) latin |= LatinMetrics.Narrow(c);
            if (!latin) return true;
            text = NativeDialogueLayout.PrepareChoiceText(text);
            int width = 0;
            foreach (char c in text) width += LatinMetrics.NotebookWidth(c, 13);
            if (centered) x = (Number(null, "Width") - width) / 2;
            y += Number(null, "FAscent") - Number(null, "FDocomo") / 2;
            MethodInfo draw = AccessTools.Method(graphics.GetType(), "DrawString", new[] { typeof(string), typeof(int), typeof(int) });
            MethodInfo setColor = AccessTools.Method(canvasType, "SetColor");
            // Preserve native outline and baseline; use the same advances for all passes.
            bool previousSmallFont = smallFontScope;
            smallFontScope = true;
            try
            {
            for (int pass = 0; pass < 5; pass++)
            {
                setColor.Invoke(canvas, new object[] { graphics, pass == 4 ? color : 0 });
                int pen = x, dx = pass == 1 ? -1 : pass == 3 ? 1 : 0;
                int dy = pass == 0 ? 1 : pass == 2 ? -1 : 0;
                foreach (char c in text)
                {
                    if (c != ' ' && c != '　')
                        draw.Invoke(graphics, new object[] { c.ToString(), pen + dx, y + dy });
                    pen += LatinMetrics.NotebookWidth(c, 13);
                }
            }
            }
            finally { smallFontScope = previousSmallFont; }
            return false;
        }
        protected static void BeforeShadowString(ref string __1)
        {
            // Ds_sub measures the whole string, then draws each glyph twice.
            // Translate before measurement; changing this argument leaves save data intact.
            string translated;
            if (ready && __1 != null && exactUi.TryGetValue(__1, out translated))
                __1 = translated;
        }
        protected static bool Equal(byte[] a, byte[] b)
        {
            if (a.Length != b.Length) return false;
            for (int i = 0; i < a.Length; i++) if (a[i] != b[i]) return false;
            return true;
        }
        protected void Patch(MethodBase method, string prefix, string postfix, string finalizer = null)
        {
            if (method == null) throw new MissingMethodException(prefix ?? postfix ?? finalizer);
            harmony.Patch(method, prefix == null ? null : new HarmonyMethod(typeof(CanvasRuntime), prefix),
                postfix == null ? null : new HarmonyMethod(typeof(CanvasRuntime), postfix), null,
                finalizer == null ? null : new HarmonyMethod(typeof(CanvasRuntime), finalizer), null);
        }
        protected static void AfterLoad(object __instance)
        {
            if (!ready) return;
            State(__instance);
        }
        protected static void BeforeString(object __instance, out int __state) { __state = Number(__instance, "Pos"); }
        protected static void AfterString(object __instance, int __state, ref string __result)
        {
            if (!ready) return;
            ScriptTranslation script = State(__instance).Translation;
            StringTranslation text;
            if (script != null && script.Strings.TryGetValue(__state, out text) && (text.Opcode == 5 || text.Opcode == 8))
            {
                if (__result == text.Source) __result = text.Target;
                else instance.Logger.LogWarning("String source mismatch at " + __state);
            }
        }
        protected static ReadState Read(object canvas, byte opcode)
        {
            if (!ready) return null;
            CanvasState state = State(canvas);
            DisplayTranslation display;
            if (state.Translation == null || !state.Translation.Displays.TryGetValue(Number(canvas, "Pos") - 1, out display) || display.Opcode != opcode) return null;
            return new ReadState { Display = display, Row = opcode == 255 ? 0 : Number(canvas, "NowStockingGyou") };
        }
        protected static void BeforeDialogue(object __instance, out ReadState __state) { __state = Read(__instance, 255); }
        protected static void BeforeRoll(object __instance, out ReadState __state) { __state = Read(__instance, 75); }
        protected static void BeforeScroll(object __instance, out ReadState __state) { __state = Read(__instance, 120); }
        protected static T[] Grow<T>(T[] old, int needed)
        {
            if (old != null && old.Length >= needed) return old;
            T[] result = new T[needed];
            if (old != null) Array.Copy(old, result, old.Length);
            return result;
        }
        protected static void SetAt<T>(object canvas, string field, int index, T value)
        {
            T[] array = Grow((T[])F(field).GetValue(canvas), index + 1);
            array[index] = value; F(field).SetValue(canvas, array);
        }
        protected static sbyte[] Signed(byte[] values, int minimum)
        {
            sbyte[] result = new sbyte[Math.Max(values.Length, minimum)];
            Buffer.BlockCopy(values, 0, result, 0, values.Length);
            return result;
        }
        protected static void ApplyRow(object canvas, RuntimeRow source, int index, bool roll, bool scroll)
        {
            RuntimeRow row = source;
            string prefix = roll ? "rollitigyougun_" : "bg_itigyougun_";
            if (row.Text.Length > 127 || row.Text.Length != row.Colors.Length || row.Text.Length != row.Controls.Length)
                throw new InvalidDataException("Invalid translated row");
            SetAt(canvas, prefix + "mojiretu", index, row.Text);
            SetAt(canvas, prefix + "zenkakusuu", index, checked((sbyte)row.Text.Length));
            sbyte[][] oldColors = (sbyte[][])F(prefix + "color").GetValue(canvas);
            int capacity = oldColors != null && index < oldColors.Length && oldColors[index] != null ? oldColors[index].Length : 23;
            capacity = Math.Max(capacity, row.Text.Length);
            SetAt(canvas, prefix + "color", index, Signed(row.Colors, capacity));
            if (!roll || scroll) SetAt(canvas, "bg_itigyougun_control", index, Signed(row.Controls, Math.Max(23, capacity)));
            int[] ruby = new int[capacity];
            for (int i = 0; i < ruby.Length; i++) ruby[i] = -1;
            SetAt(canvas, prefix + "rubi_index", index, ruby);
            SetAt(canvas, prefix + "rubisuu", index, (sbyte)0);
        }
        protected static RuntimeRow[] PrepareDialogueRows(object canvas, RuntimeRow[] source)
        {
            // PaintList consumes rows 0/1/2 as name/age/occupation, then the
            // description at its own 16-column grid. These are not dialogue wraps.
            if (Number(canvas,"MainTask")==17) return NativeDialogueLayout.PrepareNotebookRows(source);
            int capacity = layout.DialogueRows - (Number(canvas,"NowNamae")==-1 ? 0 : 1);
            return NativeDialogueLayout.WrapWithAnnotations(source, layout.DialogueColumns, capacity);
        }
        protected static bool UsesDialogueLayout(object canvas)
        {
            int task = Number(canvas, "MainTask");
            return task == 0 || task == 6 || task == 10;
        }
        protected static void BeforeDialogueViewport(object __instance)
        {
            if (!ready || !UsesDialogueLayout(__instance)) return;
            // MOJI_HANI vertical modes 1/2 use the full-screen origin/layout.
            // Only the normal bottom dialogue region has the five-row budget.
            if (Number(__instance, "MojiHani_tate") != 0 || Number(__instance, "Moji_y") != 168) return;
            CanvasState state = State(__instance);
            if (!state.Dialogue) return;
            int current = Math.Min(Number(__instance, "PrintDanYoyaku"), Number(__instance, "BunsyouGun_gyousuu") - 1);
            int visible = layout.DialogueRows;
            if (Number(__instance, "MojiHani_tate") == 0 && Number(__instance, "NowNamae") != -1) visible--;
            int top = Math.Max(0, current - Math.Max(1, visible) + 1);
            if (top > Number(__instance, "ScrollDan"))
            {
                F("ScrollDan").SetValue(__instance, top);
                F("Resumed").SetValue(__instance, true);
            }
        }
        protected static void AfterDialogue(object __instance, ReadState __state)
        {
            CanvasState state = State(__instance); state.Dialogue = false;
            if (__state == null) return;
            RuntimeRow[] layout = PrepareDialogueRows(__instance, __state.Display.Rows);
            int maximum = 0;
            for (int i = 0; i < layout.Length; i++)
            {
                ApplyRow(__instance, layout[i], i, false, false);
                maximum = Math.Max(maximum, ((string[])F("bg_itigyougun_mojiretu").GetValue(__instance))[i].Length);
            }
            // Native fade painting uses row <= count, so the first unused row
            // must be an empty sentinel. Clear all retired native rows as well.
            int end = Math.Max(layout.Length + 1, ((string[])F("bg_itigyougun_mojiretu").GetValue(__instance)).Length);
            var empty = new RuntimeRow { SourceText=String.Empty, Text=String.Empty, Colors=new byte[0], Controls=new byte[0], RubyJson="{}" };
            for (int i=layout.Length;i<end;i++) ApplyRow(__instance,empty,i,false,false);
            F("BunsyouGun_gyousuu").SetValue(__instance, checked((sbyte)layout.Length));
            F("BunsyouGun_max_mojisuu").SetValue(__instance, checked((sbyte)maximum));
            state.Dialogue = true;
            state.Reflowed = layout.Length != __state.Display.Rows.Length;
        }
        protected static void AfterRoll(object __instance, ReadState __state)
        {
            if (__state == null) return;
            ApplyRow(__instance, __state.Display.Rows[0], __state.Row, true, __state.Display.Opcode == 120);
            State(__instance).RollRows.Add(__state.Row);
        }
        protected static float SpaceAdvance(string text, float step, float width)
        { return Kibukawa.Engine.GmodeV2.TextGeometry.SpaceAdvance(text,step,width,9,LatinMetrics.Narrow); }
        protected static float RowAdvance(string text, int end, float step, float width)
        { return Kibukawa.Engine.GmodeV2.TextGeometry.RowAdvance(text,end,step,width,9,LatinMetrics.Narrow,layout.DialogueColumns / 2 * step); }
        protected static bool IsTopBulletList(object canvas)
        {
            if(Number(canvas,"MojiHani_tate")!=1 || !State(canvas).Dialogue) return false;
            var rows=(string[])F("bg_itigyougun_mojiretu").GetValue(canvas);
            return rows!=null && rows.Length>0 && rows[0]!=null && rows[0].TrimStart().StartsWith("・",StringComparison.Ordinal);
        }
        protected static void FitDraw(object canvas, int slot, int row, bool roll, ref int x)
        {
            CanvasState state = State(canvas);
            if (roll ? !state.RollRows.Contains(row) : !state.Dialogue) return;
            string[] lines = (string[])F(roll ? "rollitigyougun_mojiretu" : "bg_itigyougun_mojiretu").GetValue(canvas);
            string text = lines[row];
            // The original 12px font advances 13px; Unifont uses 16px ink.
            float step = Math.Max(layout.BodyAdvance, Number(null, "FWidth") * 2 + 1);
            int align = roll ? 1 : Number(canvas, "MojiHani_yoko");
            float width = align == 0 ? 204 : 220;
            float rowWidth = RowAdvance(text, text.Length, step, width), measure = rowWidth;
            if (!roll && align == 0)
                for (int i = 0; i < Number(canvas, "BunsyouGun_gyousuu"); i++)
                    if (lines[i] != null) measure = Math.Max(measure, RowAdvance(lines[i], lines[i].Length, step, width));
            float scale = 1f;
            float start = align == 0 ? 10 + (204 - measure * scale) / 2 :
                align == 3 ? 10 : align == 2 ? 230 - rowWidth * scale : (240 - rowWidth * scale) / 2;
            // Cumulative fade lists retain the previous frame. Their origin must
            // not move when another, wider item is appended.
            if(!roll && IsTopBulletList(canvas)) start=10;
            // Round midpoint coordinates consistently; ties-to-even alternates
            // 16/18px advances when a centered 17px grid starts on a half pixel.
            x = (int)Math.Round(start + RowAdvance(text, slot, step, width) * scale, MidpointRounding.AwayFromZero);
            drawScale = scale;
        }
        protected static void BeforeAdvDraw(object __instance, int __2, int __3, ref int __4, ref int __5, out float __state)
        {
            __state = drawScale;
            if (ready && smallFontScope && Number(__instance, "MainTask") == 17)
            {
                var lines = (string[])F("bg_itigyougun_mojiretu").GetValue(__instance);
                string text = lines[__3] ?? String.Empty;
                int nativeStep = Number(null, "FWidth") * 2 + 1;
                for (int i = 0; i < Math.Min(__2, text.Length); i++)
                    __4 -= nativeStep - LatinMetrics.NotebookWidth(text[i], nativeStep);
            }
            // PaintList profile rows are name/age/occupation. Center the 12px
            // name vertically in its cell; lift age without moving other rows.
            if (ready && smallFontScope && Number(__instance, "MainTask") == 17
                && Number(__instance, "ListPos") == 0)
            {
                if (__3 == 0) __5 -= 6;
                else if (__3 == 1) __5 -= 2;
            }
            if (ready && UsesDialogueLayout(__instance))
            {
                FitDraw(__instance, __2, __3, false, ref __4);
                CanvasState state = State(__instance);
                if (IsTopBulletList(__instance))
                    __5 = 24 + __3 * layout.RowAdvance;
                else if (state.Dialogue && Number(__instance, "MojiHani_tate") == 0)
                    __5 = Number(__instance, "Moji_y") - layout.TopOffset
                        + (Number(__instance, "NowNamae") == -1 ? 0 : layout.RowAdvance)
                        + (__3 - Number(__instance, "ScrollDan")) * layout.RowAdvance;
            }
        }
        protected static void BeforeSpeaker(object __instance, int __1, ref int __2)
        {
            if (!ready || !UsesDialogueLayout(__instance)) return;
            CanvasState state = State(__instance);
            if (!state.Dialogue || Number(__instance, "MojiHani_tate") != 0) return;
            state.SpeakerX = __1;
            __2 = Number(__instance, "Moji_y") - layout.TopOffset;
        }
        protected static void AfterDialoguePaint(object __instance, object __0)
        {
            if (!ready || !UsesDialogueLayout(__instance) || Number(__instance, "NowNamae") == -1 || Number(__instance, "MojiHani_tate") != 0) return;
            CanvasState state = State(__instance);
            if (!state.Dialogue || Number(__instance, "ScrollDan") == 0) return;
            // Native redraw only paints the speaker when absolute row zero is visible.
            // Keep the name fixed even after the body has scrolled past that row.
            AccessTools.Method(canvasType, "DrawAdvNafuda").Invoke(__instance,
                new object[] { __0, state.SpeakerX, Number(__instance, "Moji_y") - layout.TopOffset });
        }
        protected static void BeforeRollDraw(object __instance, int __2, int __3, ref int __4, out float __state)
        {
            __state = drawScale;
            if (ready) FitDraw(__instance, __2, __3, true, ref __4);
        }
        protected static void RestoreScale(float __state) { drawScale = __state; }
        protected static void BeforeSmallFontPage(out bool __state)
        {
            __state = smallFontScope;
            smallFontScope = true;
        }
        protected static void RestoreSmallFontPage(bool __state) { smallFontScope = __state; }
        protected static BitmapFontAtlas ScopedSmallFont() { return smallFontScope || activeInfo != null ? smallFont : null; }
        protected static void BeforeMenuTitle(object __instance, out string __state)
        {
            __state = menuTitle;
            menuTitle = (string)F("Command_taisyoumei").GetValue(__instance);
        }
        protected static void RestoreMenuTitle(string __state) { menuTitle = __state; }
        protected static BitmapFontAtlas FontForDraw(char[] text)
        {
            return !String.IsNullOrEmpty(menuTitle) && text != null && new string(text) == menuTitle ? smallFont : ScopedSmallFont();
        }
        protected static bool BeforeDraw(object __instance, char[] __0, int __1, int __2)
        {
            if (!ready) return true;
            float scale = drawScale > 0 ? drawScale : 1;
            if (activeInfo != null)
            {
                float originalStart = 238 - activeInfo.TranslatedCount * 12;
                int slot = (int)Math.Round((__1 - originalStart) / 12f);
                if (slot >= 0 && slot < activeInfo.Positions.Length)
                    __1 = 238 - activeInfo.Width + activeInfo.Positions[slot];
                scale = 1f;
                __2 = layout.InfoBaseline; // INFO baseline lifted one native pixel; preserve native small-font bearings.
            }
            Vector2 origin = (Vector2)drawOrigin.GetValue(__instance);
            return LegacyFontRenderer.Draw(__instance, __0, __1 + (int)origin.x, __2 + (int)origin.y, null, font, scale, FontForDraw(__0));
        }
        protected static void BeforeInfo(object __instance, out InfoState __state)
        {
            __state = null;
            if (!ready) return;
            object owner = infoOwner.GetValue(__instance);
            string source = (string)F("info_struct_moji").GetValue(owner);
            RuntimeRow row;
            if (source == null || !infoRows.TryGetValue(source, out row)) return;
            __state = new InfoState { Owner = owner, Text = source, Count = Number(owner, "info_struct_zenkaku_suu"),
                Raw = (sbyte[])F("info_struct_mojiretu").GetValue(owner), Colors = (sbyte[])F("info_struct_iro").GetValue(owner),
                TranslatedCount = row.Text.Length, Positions = new int[row.Text.Length], Previous = activeInfo };
            // INFO is individually drawn at 12px intervals by the original coroutine.
            // Use native native small-font 12px ink with a 1px gap and 6px separators.
            int next = 0;
            for (int i = 0; i < row.Text.Length; i++)
            {
                if (i > 0 && NativeDialogueLayout.DigitHanBoundary(row.Text[i-1], row.Text[i]))
                    next += layout.InfoSpaceAdvance;
                __state.Positions[i] = next;
                next += row.Text[i] == '\u3000' ? layout.InfoSpaceAdvance : LatinMetrics.Narrow(row.Text[i]) ? 7 : layout.InfoAdvance;
            }
            __state.Width = Math.Max(0, next - 1);
            activeInfo = __state;
            F("info_struct_moji").SetValue(owner, row.Text);
            F("info_struct_zenkaku_suu").SetValue(owner, row.Text.Length);
            F("info_struct_mojiretu").SetValue(owner, Grow(__state.Raw, row.Text.Length * 2));
            F("info_struct_iro").SetValue(owner, Signed(row.Colors, Math.Max(50, row.Text.Length)));
        }
        protected static void BeforeInfoClip(object __instance, int __0, int __1, int __2, ref int __3)
        {
            // PaintMain_info uses this short clip only during transition pattern 14.
            if (activeInfo == null || __0 != 0 || __1 != 0 || __2 != 240 || __3 != 14) return;
            activeInfo.ClipGraphics = __instance;
            __3 = 16;
        }
        protected static void RestoreInfo(InfoState __state)
        {
            if (__state == null) return;
            F("info_struct_moji").SetValue(__state.Owner, __state.Text);
            F("info_struct_zenkaku_suu").SetValue(__state.Owner, __state.Count);
            F("info_struct_mojiretu").SetValue(__state.Owner, __state.Raw);
            F("info_struct_iro").SetValue(__state.Owner, __state.Colors);
            activeInfo = __state.Previous;
            if (__state.ClipGraphics != null)
                AccessTools.Method(__state.ClipGraphics.GetType(), "SetClip", new[] { typeof(int), typeof(int), typeof(int), typeof(int) })
                    .Invoke(__state.ClipGraphics, new object[] { 0, 0, 240, 14 });
        }
        protected void InstallHooks(string owner)
        {
                harmony = new Harmony(owner);
                NativeChoiceMemory.Install(harmony, canvasType);
                Patch(AccessTools.Method(canvasType, "DrawAdvCommandCenter"), "BeforeChoiceCenter", null);
                Patch(AccessTools.Method(canvasType, "DrawAdvCommand"), "BeforeChoiceLeft", null);
                NativeMenuPosition.Install(harmony, canvasType, 168 - layout.TopOffset + 14);
                Patch(AccessTools.Method(canvasType, "Ds_sub", new[] { AccessTools.TypeByName("Socotra.UI.StGraphics"), typeof(string), typeof(int), typeof(int) }), "BeforeShadowString", null);
                Patch(AccessTools.Method(canvasType, "LoadScenario"), null, "AfterLoad");
                Patch(AccessTools.Method(canvasType, "LoadResScenario"), null, "AfterLoad");
                Patch(AccessTools.Method(canvasType, "StringRead"), "BeforeString", "AfterString");
                Patch(AccessTools.Method(canvasType, "BUNSYOU"), "BeforeDialogue", "AfterDialogue");
                Patch(AccessTools.Method(canvasType, "BUNSYOU_ROLL"), "BeforeRoll", "AfterRoll");
                Patch(AccessTools.Method(canvasType, "BUNSYOU_SCROLL"), "BeforeScroll", "AfterRoll");
                Patch(AccessTools.Method(canvasType, "DrawAdvString"), "BeforeAdvDraw", null, "RestoreScale");
                Patch(AccessTools.Method(canvasType, "PaintADV"), "BeforeDialogueViewport", null);
                Patch(AccessTools.Method(canvasType, "DrawAdvNafuda"), "BeforeSpeaker", null);
                Patch(AccessTools.Method(canvasType, "PaintADV_text"), null, "AfterDialoguePaint");
                Patch(AccessTools.Method(canvasType, "DrawAdvStringRoll"), "BeforeRollDraw", null, "RestoreScale");
                Type graphics = AccessTools.TypeByName("Socotra.UI.StGraphics");
                drawOrigin = AccessTools.Field(graphics, "drawOrigin");
                if (drawOrigin == null) throw new MissingFieldException("StGraphics.drawOrigin");
                Patch(AccessTools.Method(graphics, "DrawCharImpl", new[] { typeof(char[]), typeof(int), typeof(int) }), "BeforeDraw", null);
                Patch(AccessTools.Method(graphics, "SetClip", new[] { typeof(int), typeof(int), typeof(int), typeof(int) }), "BeforeInfoClip", null);
                foreach (string method in layout.SmallFontMethods)
                    Patch(AccessTools.Method(canvasType, method), "BeforeSmallFontPage", null, "RestoreSmallFontPage");
                Patch(AccessTools.Method(canvasType, "PaintCommand"), "BeforeMenuTitle", null, "RestoreMenuTitle");
                Patch(AccessTools.Method(canvasType, "PaintLongCommand"), "BeforeMenuTitle", null, "RestoreMenuTitle");
                MethodInfo infoMove = AccessTools.EnumeratorMoveNext(AccessTools.Method(canvasType, "PaintMain_info"));
                infoOwner = AccessTools.Field(infoMove.DeclaringType, "<>4__this");
                if (infoOwner == null) throw new MissingFieldException("INFO coroutine owner");
                Patch(infoMove, "BeforeInfo", null, "RestoreInfo");
        }
    }
}
