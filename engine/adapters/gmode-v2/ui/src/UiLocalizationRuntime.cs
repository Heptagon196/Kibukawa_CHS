using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using UnityEngine;
using UnityEngine.UI;

namespace Kibukawa.Engine.UnityUI
{
    /// <summary>
    /// Display-only UI translation. Call Initialize from Awake, Update each frame,
    /// and Dispose from OnDestroy, all on Unity's main thread.
    /// No CanvasEx model fields, save strings, keyboard keys or IL literals change.
    /// </summary>
    public class UiLocalizationRuntime
    {
        protected static string Owner;
        protected static IDictionary<string,string> Exact, Keys;
        protected static Func<string,bool> IsExcluded;
        protected static Func<string,string> TranslateSpecial;
        protected static string[] FontNames;
        private static readonly Dictionary<string, string> extraDisplay =
            new Dictionary<string, string>(StringComparer.Ordinal);
        private static readonly Dictionary<Text, TextState> states = new Dictionary<Text, TextState>();
        private static readonly HashSet<string> warnings = new HashSet<string>();
        private static Harmony harmony;
        private static Action<string> log;
        private static Font chineseFont;
        private static bool active, fontAttempted;
        private static float nextRefresh;

        private sealed class TextState
        {
            internal Font Font;
            internal int Size, Min, Max;
            internal float Spacing;
            internal bool BestFit;
            internal FontStyle Style;
            internal string Source, Translation;
        }

        public static void Initialize(Action<string> logger = null)
        {
            if (active) return;
            log = logger;
            warnings.Clear();
            fontAttempted = false;
            harmony = new Harmony(Owner);
            active = true;
            try
            {
                Patch(AccessTools.PropertySetter(typeof(Text), "text"), "BeforeTextSet", "AfterTextSet");
                Patch(AccessTools.Method(typeof(Text), "OnEnable"), null, "AfterTextEnabled");
                Type localization = AccessTools.TypeByName("Steezy.Localize.Localization");
                Patch(localization == null ? null : AccessTools.Method(localization, "Get", new[] { typeof(string) }),
                    null, "AfterLocalized");
                Type graphics = AccessTools.TypeByName("Socotra.UI.StGraphics");
                if (graphics == null) Warn("Socotra.UI.StGraphics is unavailable; legacy UI translation is disabled.");
                else
                {
                    // Evidence: DrawString converts its argument to char[] and calls
                    // DrawCharImpl; DrawChars copies [offset,length] then calls it.
                    // Patching here runs before the main plugin's glyph renderer.
                    Patch(AccessTools.Method(graphics, "DrawString", new[] { typeof(string), typeof(int), typeof(int) }),
                        "BeforeDrawString", null);
                    Patch(AccessTools.Method(graphics, "DrawChars", new[] { typeof(char[]), typeof(int), typeof(int), typeof(int), typeof(int) }),
                        "BeforeDrawChars", null);
                }
                nextRefresh = 0;
                Update();
                Write("UI localization initialized: " + Exact.Count +
                    " exact display strings, " + Keys.Count + " localization keys.");
            }
            catch
            {
                Dispose();
                throw;
            }
        }

        /// <summary>Registers a whole display string, never a substring or model mutation.</summary>
        public static void RegisterDisplayTranslation(string source, string target)
        {
            if (string.IsNullOrEmpty(source) || target == null)
                throw new ArgumentException("A nonempty source and nonnull target are required.");
            if (IsSentinel(source)) throw new ArgumentException("Technical sentinel is not a display translation: " + source);
            string existing;
            if ((Exact.TryGetValue(source, out existing) || extraDisplay.TryGetValue(source, out existing))
                && !string.Equals(existing, target, StringComparison.Ordinal))
                throw new InvalidOperationException("Conflicting display translation: " + source);
            extraDisplay[source] = target;
            nextRefresh = 0;
        }

        private static bool IsSentinel(string value)
        {
            return IsExcluded != null && IsExcluded(value);
        }

        public static string TranslateDisplay(string source)
        {
            if (source == null || IsSentinel(source)) return source;
            string result;
            if (extraDisplay.TryGetValue(source, out result) || Exact.TryGetValue(source, out result))
                return result;
            return TranslateSpecial == null ? source : TranslateSpecial(source);
        }

        public static Font GetChineseFont()
        {
            if (chineseFont != null || fontAttempted) return chineseFont;
            fontAttempted = true;
            try
            {
                chineseFont = Font.CreateDynamicFontFromOSFont(
                    FontNames, 16);
                if (chineseFont != null)
                {
                    UnityEngine.Object.DontDestroyOnLoad(chineseFont);
                    Write("Chinese UI font created from system font fallback list.");
                }
                else Warn("System Chinese UI font was unavailable; original fonts are preserved.");
            }
            catch (Exception exception) { Warn("Cannot create Chinese UI font: " + exception.Message); }
            return chineseFont;
        }

        public static void Update()
        {
            if (!active || Time.realtimeSinceStartup < nextRefresh) return;
            nextRefresh = Time.realtimeSinceStartup + 2f;
            // Serialized Text may exist before installation or on inactive prefabs.
            // Setters/OnEnable handle updates immediately between these sweeps.
            foreach (Text text in Resources.FindObjectsOfTypeAll<Text>()) Refresh(text);
            List<Text> dead = new List<Text>();
            foreach (Text text in states.Keys) if (text == null) dead.Add(text);
            foreach (Text text in dead) states.Remove(text);
        }

        private static void Patch(MethodBase method, string prefix, string postfix)
        {
            if (method == null) { Warn("Missing optional UI hook: " + (prefix ?? postfix)); return; }
            HarmonyMethod before = prefix == null ? null : new HarmonyMethod(typeof(UiLocalizationRuntime), prefix);
            if (before != null) before.priority = Priority.First;
            harmony.Patch(method, before, postfix == null ? null : new HarmonyMethod(typeof(UiLocalizationRuntime), postfix));
        }

        private static void BeforeDrawString(ref string __0)
        {
            if (active) __0 = TranslateDisplay(__0);
        }

        private static void BeforeDrawChars(ref char[] __0, ref int __3, ref int __4)
        {
            if (!active || __0 == null || __3 < 0 || __4 < 0 || __3 > __0.Length - __4) return;
            string source = new string(__0, __3, __4);
            string translated = TranslateDisplay(source);
            if (string.Equals(source, translated, StringComparison.Ordinal)) return;
            // Never overwrite the shared script buffer, including bookmark/name data.
            __0 = translated.ToCharArray();
            __3 = 0;
            __4 = __0.Length;
        }

        private static void AfterLocalized(string __0, ref string __result)
        {
            string translated;
            if (active && __0 != null && Keys.TryGetValue(__0, out translated))
                __result = translated;
        }

        private static void BeforeTextSet(Text __instance, ref string __0)
        {
            if (!active || __instance == null) return;
            TextState state = Capture(__instance);
            if (IsInputValue(__instance)) return;
            string translated = TranslateDisplay(__0);
            if (!string.Equals(__0, translated, StringComparison.Ordinal))
            {
                state.Source = __0;
                state.Translation = translated;
                __0 = translated;
            }
            else if (!string.Equals(__0, state.Translation, StringComparison.Ordinal))
            {
                state.Source = null;
                state.Translation = null;
            }
        }

        private static void AfterTextSet(Text __instance)
        {
            if (active) ApplyFont(__instance);
        }

        private static void AfterTextEnabled(Text __instance)
        {
            if (active) Refresh(__instance);
        }

        private static bool IsInputValue(Text text)
        {
            InputField input = text.GetComponentInParent<InputField>();
            return input != null && input.textComponent == text;
        }

        private static TextState Capture(Text text)
        {
            TextState state;
            if (!states.TryGetValue(text, out state))
            {
                state = new TextState { Font = text.font, Size = text.fontSize, Spacing = text.lineSpacing,
                    BestFit = text.resizeTextForBestFit, Min = text.resizeTextMinSize,
                    Max = text.resizeTextMaxSize, Style = text.fontStyle };
                states.Add(text, state);
            }
            return state;
        }

        private static void Refresh(Text text)
        {
            if (text == null) return;
            Capture(text);
            if (!IsInputValue(text))
            {
                string source = text.text;
                string translated = TranslateDisplay(source);
                if (!string.Equals(source, translated, StringComparison.Ordinal))
                {
                    // Use original value so the setter records its restoration pair.
                    text.text = source;
                }
            }
            ApplyFont(text);
        }

        private static bool HasHan(string value)
        {
            if (value == null) return false;
            foreach (char ch in value) if (ch >= '\u3400' && ch <= '\u9fff') return true;
            return false;
        }

        private static void ApplyFont(Text text)
        {
            if (text == null) return;
            TextState state = Capture(text);
            Font font = HasHan(text.text) ? GetChineseFont() : null;
            if (font == null) { RestoreFont(text, state); return; }
            if (text.font != font) text.font = font;
            text.lineSpacing = Mathf.Max(state.Spacing, 1.2f);
            // Input text keeps its original layout; only its glyph font changes.
            if (!IsInputValue(text) && state.Size > 0)
            {
                text.resizeTextMinSize = Mathf.Min(state.Size, Mathf.Max(10, state.Size * 3 / 5));
                text.resizeTextMaxSize = state.Size;
                text.resizeTextForBestFit = true;
            }
        }

        private static void RestoreFont(Text text, TextState state)
        {
            if (text.font != state.Font) text.font = state.Font;
            text.fontSize = state.Size;
            text.lineSpacing = state.Spacing;
            text.resizeTextMinSize = state.Min;
            text.resizeTextMaxSize = state.Max;
            text.resizeTextForBestFit = state.BestFit;
            text.fontStyle = state.Style;
        }

        public static void Dispose()
        {
            active = false;
            if (harmony != null) { harmony.UnpatchSelf(); harmony = null; }
            foreach (KeyValuePair<Text, TextState> item in states)
            {
                Text text = item.Key;
                if (text == null) continue;
                if (item.Value.Source != null && string.Equals(text.text, item.Value.Translation, StringComparison.Ordinal))
                    text.text = item.Value.Source;
                RestoreFont(text, item.Value);
            }
            states.Clear();
            extraDisplay.Clear();
            if (chineseFont != null) UnityEngine.Object.Destroy(chineseFont);
            chineseFont = null;
            fontAttempted = false;
            log = null;
        }

        private static void Write(string message) { if (log != null) log(message); }
        private static void Warn(string message) { if (warnings.Add(message)) Write("UI warning: " + message); }
    }
}
