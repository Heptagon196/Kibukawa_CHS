using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using BepInEx;
using HarmonyLib;
using UnityEngine;
using Kibu1ZhCN;

namespace Kibukawa.Engine.Gmode20050117
{
    /// <summary>
    /// Runtime base for the 20050117 scenario VM (ninth title).
    ///
    /// Where 20050817 keeps per-row colour/control/ruby planes in the script, this
    /// version stocks one line at a time: BUNSYOU reads three setup bytes plus one
    /// NUL-terminated string, then CanvasEx::BunsyouStock appends that string to
    /// Bun_moji[dan] while filling the parallel Bun_iro / Bun_speed / Bun_alpha /
    /// Bun_jikan entries per character. The runtime therefore substitutes the
    /// stocked string and its Bun_nagasa length, and leaves the native reveal
    /// animation, colours, script bytes and save offsets untouched.
    ///
    /// Because Bun_iro is filled per character, BUNSYOU_IRO starts an override and
    /// BUNSYOU_F7 restores the base colour after any ruby span has closed. Those lines
    /// are stocked one effective colour run at a time, so emphasis stays on the words
    /// it marks in Japanese even when the colour ends in the middle of a line.
    ///
    /// Glyph drawing is shared with the eighth title: StGraphics::DrawCharImpl has
    /// identical IL in both versions, so gmode-v2's BitmapFontAtlas and
    /// LegacyFontRenderer are reused verbatim. RenderStart/RenderEnd differ
    /// between the versions and LegacyFontRenderer binds those from the live
    /// graphics type, so it always calls this game's own methods.
    /// </summary>
    public abstract class CanvasRuntime : BaseUnityPlugin
    {
        protected static RuntimePack pack;
        protected static BitmapFontAtlas font;
        protected static BitmapFontAtlas smallFont;
        protected static CanvasRuntime instance;
        protected static Type canvasType;
        protected static Type graphicsType;
        protected static string currentScript;
        protected static int lineOffset = -1;
        // 0 none, 1 nameplate, 2 menu label. Set by the command's prefix and consumed
        // by the StringRead postfix, so only the intended operand is replaced.
        protected static int textKind;
        protected static int textIndex;
        protected static int textOffset = -1;
        protected static FieldInfo drawOrigin;
        protected static bool ready;
        protected static int substituted;
        protected static int skippedTooLong;
        protected static int localizationHits;
        protected static int rubySuppressed;
        protected static int runsIncomplete;
        [ThreadStatic] protected static bool dialogueDraw;
        [ThreadStatic] protected static bool nameplateDraw;
        protected static readonly List<string> literals = new List<string>();
        protected Harmony harmony;

        private static readonly Dictionary<string, FieldInfo> instanceFields = new Dictionary<string, FieldInfo>();
        private static readonly Dictionary<string, FieldInfo> staticFields = new Dictionary<string, FieldInfo>();
        private static readonly ConditionalWeakTable<object, LineState> states = new ConditionalWeakTable<object, LineState>();

        /// <summary>Per-canvas state for the display line currently being stocked.</summary>
        private sealed class LineState
        {
            public readonly Dictionary<int, RuntimePack.LayoutLine> Layouts = new Dictionary<int, RuntimePack.LayoutLine>();
            public bool NewLine = true;
            public bool Translated;
            public int Total;
            public int Slots;
            // A recoloured line arrives as one string per effective colour run. ColourRun
            // advances when BUNSYOU_IRO changes colour or BUNSYOU_F7 restores the base
            // colour; StockedRun is the last translated run already stocked.
            public string[] Runs;
            public int ColourRun;
            public int StockedRun;
        }

        /// <summary>The Chinese names temporarily replaced while SaveData runs.</summary>
        protected sealed class NameSaveState
        {
            public string[] Values;
            public bool Restored;
        }

        /// <summary>Members the runtime resolves before it patches anything.</summary>
        protected static readonly string[] RequiredFields = {
            "Bun_moji", "Bun_iro", "Bun_speed", "Bun_alpha", "Bun_jikan", "Bun_nagasa",
            "BunsyouNagasaMax", "DanNoKazu", "NowStockMojiDan", "NowStockMojiKeta",
            "NowPrintingDan", "NowPrintingKeta", "SyoriMojiCount", "RubiCreateCounter",
            "MojiHani_tate", "MojiHani_yoko", "MainTask", "SubTask", "NowFadeChu",
            "SysCursor_enable", "OsippanasiKinsi",
            "Sentaku_nafuda", "Namae_nafuda", "model", "NowRubiChu", "NowMojiColorChangeChu"
        };

        protected static readonly string[] RequiredStaticFields = { "Width", "FAscent", "FDocomo", "FHeight" };

        /// <summary>Handlers whose postfix ends the current display line.</summary>
        protected static readonly string[] LineTerminators = {
            "BUNSYOU_SLASH", "BUNSYOU_SEMI_COLON", "BUNSYOU_PERIOD", "BUNSYOU_ASTARISK"
        };

        protected static FieldInfo F(string name)
        {
            FieldInfo field;
            if (instanceFields.TryGetValue(name, out field)) return field;
            field = AccessTools.Field(canvasType, name);
            if (field == null) throw new MissingFieldException(canvasType.FullName, name);
            instanceFields.Add(name, field);
            return field;
        }

        protected static FieldInfo S(string name)
        {
            FieldInfo field;
            if (staticFields.TryGetValue(name, out field)) return field;
            field = canvasType.GetField(name, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
            if (field == null) throw new MissingFieldException(canvasType.FullName, name);
            staticFields.Add(name, field);
            return field;
        }

        protected static int Number(object canvas, string name) { return Convert.ToInt32(F(name).GetValue(canvas)); }
        protected static int StaticNumber(string name) { return Convert.ToInt32(S(name).GetValue(null)); }

        protected void Patch(MethodBase method, string prefix, string postfix, string finalizer = null)
        {
            if (method == null) throw new MissingMethodException(prefix ?? postfix ?? finalizer);
            harmony.Patch(method, prefix == null ? null : new HarmonyMethod(typeof(CanvasRuntime), prefix),
                          postfix == null ? null : new HarmonyMethod(typeof(CanvasRuntime), postfix), null,
                          finalizer == null ? null : new HarmonyMethod(typeof(CanvasRuntime), finalizer), null);
        }

        protected static void Log(string message)
        {
            if (instance != null) instance.Logger.LogInfo(message);
        }

        protected static void Warn(string message)
        {
            if (instance != null) instance.Logger.LogWarning(message);
        }

        private static string Hash(string path)
        {
            using (SHA256 sha = SHA256.Create())
            using (FileStream stream = File.OpenRead(path))
            {
                byte[] digest = sha.ComputeHash(stream);
                var text = new System.Text.StringBuilder(digest.Length * 2);
                foreach (byte value in digest) text.Append(value.ToString("x2"));
                return text.ToString();
            }
        }

        /// <summary>Load the pack and atlas, verify identity and install every hook. Writes nothing.</summary>
        protected void Initialise(string pluginFolder, Type canvas, Type graphics)
        {
            instance = this;
            canvasType = canvas ?? throw new ArgumentNullException("canvas");
            graphicsType = graphics ?? throw new ArgumentNullException("graphics");
            string packPath = Path.Combine(pluginFolder, "translations.bin");
            if (!File.Exists(packPath)) throw new FileNotFoundException("Missing translation pack", packPath);
            RuntimePack loaded = RuntimePack.Load(packPath);
            if (loaded.GameAssemblySha256 != Hash(Path.Combine(Paths.GameRootPath, "kibu9_Data/Managed/Assembly-CSharp.dll")) ||
                loaded.ScratchpadSha256 != Hash(Path.Combine(Paths.GameRootPath, "kibu9_Data/StreamingAssets/scratchpad")))
                throw new InvalidDataException("Translation pack game identity mismatch");
            // Resolve every required member before applying any patch.
            foreach (string name in RequiredFields) F(name);
            foreach (string name in RequiredStaticFields) S(name);
            drawOrigin = AccessTools.Field(graphicsType, "drawOrigin");
            if (drawOrigin == null) throw new MissingFieldException("StGraphics.drawOrigin");
            pack = loaded;
            font = new BitmapFontAtlas(Path.Combine(pluginFolder, "fonts"));
            smallFont = new BitmapFontAtlas(Path.Combine(pluginFolder, "fonts/ui-12"));
            harmony = new Harmony(GetType().FullName);
            InstallHooks();
            InstallChoiceMemory();
            ready = true;
            Log("Kibu9 Chinese runtime ready: " + pack.LineCount + " lines, " + font.GlyphCount
                + " dialogue glyphs, " + smallFont.GlyphCount + " small UI glyphs.");
        }

        /// <summary>
        /// Choice memory is an enhancement, not a prerequisite: if its transpiler no
        /// longer matches the shipped IL, disable only that and keep text translation
        /// working. The transpiler asserts its guard counts, so a mismatch is loud.
        /// </summary>
        private void InstallChoiceMemory()
        {
            try
            {
                NativeChoiceMemory.Install(harmony, canvasType);
                Log("Native choice memory extended to cancellable text menus.");
            }
            catch (Exception error)
            {
                Log("Choice memory not installed, text translation continues: " + error.Message);
            }
        }

        protected virtual void InstallHooks()
        {
            // Capture which scenario is loading, so a line can be keyed on
            // (script, command offset) exactly like the rest of the series.
            Patch(AccessTools.Method(canvasType, "LoadScenario", new[] { typeof(string) }), "BeforeLoad", "AfterLoad");
            Patch(AccessTools.Method(canvasType, "LoadScenarioEx", new[] { typeof(string) }), "BeforeLoad", null);
            // BUNSYOU runs after the dispatcher consumed the opcode byte, so Pos - 1 is
            // the script-relative offset of the command that opens the line.
            Patch(AccessTools.Method(canvasType, "BUNSYOU"), "BeforeBunsyou", null);
            // Each BUNSYOU fragment then arrives here.
            Patch(AccessTools.Method(canvasType, "BunsyouStock", new[] { typeof(string) }), "BeforeStock", null);
            // BUNSYOU_IRO recolours the characters stocked after it, which is how the
            // script emphasises a clue word or a name part-way through a line.
            Patch(AccessTools.Method(canvasType, "BUNSYOU_IRO"), "BeforeColour", null);
            // F7 closes ruby first; only a later F7 with no active ruby restores the
            // base text colour. Count that restoration as another effective colour run.
            Patch(AccessTools.Method(canvasType, "BUNSYOU_F7"), "BeforeF7", null);
            // COLON is the stock click gate used to paginate the normal bottom
            // dialogue region.  Full-screen vertical modes have their own viewport
            // and must flow through it without inheriting that row threshold.
            Patch(AccessTools.Method(canvasType, "BUNSYOU_COLON"), "BeforeColon", null);
            // Nameplates and menu labels are StringRead operands stored straight into
            // the native arrays, so they are replaced where they are read.
            Patch(AccessTools.Method(canvasType, "NAMAE_SETTEI"), "BeforeName", null);
            Patch(AccessTools.Method(canvasType, "SENTAKUSI"), "BeforeChoice", null);
            Patch(AccessTools.Method(canvasType, "StringRead"), null, "AfterStringRead");
            // Namae_nafuda is part of the native CP932 save block. Let the serializer
            // see the original Japanese strings, then restore the live Chinese array.
            Patch(AccessTools.Method(canvasType, "SaveData", Type.EmptyTypes),
                  "BeforeSaveNames", "AfterSaveNames", "AfterSaveNamesError");
            Patch(AccessTools.Method(canvasType, "LoadData", Type.EmptyTypes),
                  null, "AfterLoadNames");
            // These are exactly the handlers that advance NowStockMojiDan, so their
            // postfix marks the moment the next BUNSYOU starts a new display line.
            foreach (string name in LineTerminators)
            {
                MethodInfo method = AccessTools.Method(canvasType, name);
                if (method == null) throw new MissingMethodException(canvasType.FullName, name);
                Patch(method, null, "AfterLine");
            }
            // The single glyph choke point: DrawString and DrawChars both funnel here.
            Patch(AccessTools.Method(canvasType, "DrawAdvString", new[] {
                graphicsType, typeof(int), typeof(int), typeof(int), typeof(int) }),
                "BeforeAdvDraw", null, "RestoreAdvDraw");
            Patch(AccessTools.Method(canvasType, "DrawAdvNafuda"),
                "BeforeNameplatePosition", null, "RestoreNameplateDraw");
            Patch(AccessTools.Method(canvasType, "ClearBunBuffer"), null, "AfterClearText");
            Patch(AccessTools.Method(canvasType, "DrawAdvCommandCenter", new[] {
                graphicsType, typeof(int), typeof(int), typeof(int) }), "BeforeChoiceCenter", null);
            Patch(AccessTools.Method(canvasType, "DrawAdvCommand", new[] {
                graphicsType, typeof(int), typeof(int), typeof(int), typeof(int) }), "BeforeChoiceLeft", null);
            Patch(AccessTools.Method(graphicsType, "DrawCharImpl", new[] { typeof(char[]), typeof(int), typeof(int) }), "BeforeDraw", null);
            // Japanese ruby is a reading of the original base text. The Chinese edition
            // never displays it, including on lines that are not present in the pack.
            Patch(AccessTools.Method(canvasType, "CreateRubiTexture", new[] { typeof(string), typeof(int) }),
                  "BeforeCreateRubi", null);
            // Unity UI text goes through the game's own localization table; replacing the
            // lookup keeps every prefab, language switch and re-localize path intact.
            Type localize = AccessTools.TypeByName("Steezy.Localize.Localization");
            if (localize != null)
            {
                MethodInfo get = AccessTools.Method(localize, "Get", new[] { typeof(string) });
                if (get == null) throw new MissingMethodException(localize.FullName, "Get");
                Patch(get, null, "AfterGet");
            }
            // CanvasEx draws its loading and legacy-service messages through these
            // helpers. Each helper measures the complete string first, then slices it
            // into one-character DrawString calls. Replace the argument at entry so
            // the native centering calculation and every later glyph see the Chinese
            // line rather than trying to translate already-split characters.
            Type[] displayLine = { graphicsType, typeof(string), typeof(int), typeof(int) };
            Patch(AccessTools.Method(canvasType, "Ds_sub", displayLine), "BeforeCanvasUi", null);
            Patch(AccessTools.Method(canvasType, "Ds_sub2", displayLine), "BeforeCanvasUi", null);
            ApplyNativeLiterals();
        }

        /// <summary>
        /// Replace the soft-key labels the game hard-codes in its own static array.
        /// CanvasEx's field initialiser runs before the plugin, so this edits the live
        /// array in place; no game file is modified.
        /// </summary>
        protected static void ApplyNativeLiterals()
        {
            FieldInfo field = canvasType.GetField("command", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
            if (field == null) throw new MissingFieldException(canvasType.FullName, "command");
            string[] labels = (string[])field.GetValue(null);
            if (labels == null) return;
            for (int i = 0; i < labels.Length; i++)
            {
                string target;
                if (labels[i] != null && pack.TryUi(labels[i], out target) && !string.IsNullOrEmpty(target))
                {
                    literals.Add(labels[i]);
                    labels[i] = target;
                }
            }
        }

        /// <summary>Replace a Steezy.Localize lookup result with the pack's Chinese text.</summary>
        protected static void AfterGet(string __0, ref string __result)
        {
            if (!ready || __0 == null) return;
            string target;
            if (pack.TryLocalization(__0, out target) && !string.IsNullOrEmpty(target))
            {
                __result = target;
                localizationHits++;
            }
        }

        /// <summary>Translate a complete CanvasEx status line before native measurement.</summary>
        protected static void BeforeCanvasUi(ref string __1)
        {
            if (!ready || __1 == null) return;
            string target;
            if (pack.TryUi(__1, out target) && !string.IsNullOrEmpty(target)) __1 = target;
        }

        /// <summary>Canonical script name: the loader argument without directory or extension.</summary>
        protected static string Canonical(string value)
        {
            if (string.IsNullOrEmpty(value)) return value;
            string name = value.Replace('\\', '/');
            int slash = name.LastIndexOf('/');
            if (slash >= 0) name = name.Substring(slash + 1);
            if (name.EndsWith(".bin", StringComparison.OrdinalIgnoreCase)) name = name.Substring(0, name.Length - 4);
            return name.ToLowerInvariant();
        }

        protected static void BeforeLoad(object __instance, string __0)
        {
            currentScript = Canonical(__0);
            // A fresh script must not inherit the previous line's accumulator.
            if (__instance != null) states.Remove(__instance);
        }

        protected static void BeforeBunsyou(object __instance)
        {
            if (!ready) return;
            lineOffset = Number(__instance, "Pos") - 1;
            textKind = 0;
        }

        /// <summary>
        /// NAMAE_SETTEI reads the nameplate text, then a sound name and an image name.
        /// Only the first StringRead is drawn in the nameplate.
        /// </summary>
        protected static void BeforeName(object __instance)
        {
            if (!ready) return;
            textKind = 1;
            textIndex = 0;
            textOffset = Number(__instance, "Pos") - 1;
        }

        /// <summary>SENTAKUSI reads its label and then the jump target; only the label is drawn.</summary>
        protected static void BeforeChoice(object __instance)
        {
            if (!ready) return;
            textKind = 2;
            textIndex = 0;
            textOffset = Number(__instance, "Pos") - 1;
        }

        /// <summary>Replace a nameplate or menu label before the caller stores it.</summary>
        protected static void AfterStringRead(object __instance, ref string __result)
        {
            if (!ready || textKind == 0 || __result == null) return;
            int kind = textKind;
            int index = textIndex;
            textIndex = index + 1;
            // NAMAE_SETTEI performs three StringReads; SENTAKUSI only one.
            if (kind == 1 && textIndex >= 3) textKind = 0;
            if (kind == 2) textKind = 0;
            if (index != 0) return;
            string target;
            int fragments;
            if (!pack.TryLine(currentScript, textOffset, out target, out fragments)) return;
            if (string.IsNullOrEmpty(target)) return;
            __result = target;
            substituted++;
        }

        /// <summary>
        /// The original serializer converts every Namae_nafuda entry to CP932. Several
        /// Simplified-Chinese glyphs have no CP932 representation, so let it see the
        /// source Japanese names while retaining an exact snapshot for the live UI.
        /// </summary>
        protected static void BeforeSaveNames(object __instance, out NameSaveState __state)
        {
            __state = null;
            if (!ready || __instance == null) return;
            string[] names = (string[])F("Namae_nafuda").GetValue(__instance);
            if (names == null) return;
            __state = new NameSaveState { Values = (string[])names.Clone() };
            for (int i = 0; i < names.Length; i++) names[i] = pack.NameForSave(names[i]);
        }

        private static void RestoreSavedNames(object __instance, NameSaveState state)
        {
            if (state == null || state.Restored || state.Values == null || __instance == null) return;
            state.Restored = true;
            string[] names = (string[])F("Namae_nafuda").GetValue(__instance);
            if (names == null) return;
            Array.Copy(state.Values, names, Math.Min(state.Values.Length, names.Length));
        }

        protected static void AfterSaveNames(object __instance, NameSaveState __state)
        {
            RestoreSavedNames(__instance, __state);
        }

        protected static Exception AfterSaveNamesError(object __instance, NameSaveState __state,
                                                        Exception __exception)
        {
            RestoreSavedNames(__instance, __state);
            return __exception;
        }

        protected static void AfterLoadNames(object __instance)
        {
            if (!ready || __instance == null) return;
            string[] names = (string[])F("Namae_nafuda").GetValue(__instance);
            if (names == null) return;
            for (int i = 0; i < names.Length; i++) names[i] = pack.NameAfterLoad(names[i]);
        }

        protected static void AfterLoad(object __instance)
        {
            // Reserved for script identity work; substitution is keyed on the source
            // line, so nothing has to be captured here yet.
        }

        /// <summary>
        /// Replace the Japanese fragment with its Chinese translation before the original
        /// stocks it, so Bun_moji, Bun_iro, Bun_speed, Bun_alpha, Bun_jikan and
        /// NowStockMojiKeta all stay consistent by construction.
        ///
        /// A display line is a run of BUNSYOU fragments, and CanvasEx writes the line's
        /// total length into Bun_nagasa[dan] on the line's first fragment. The native
        /// value describes the Japanese line, so the runtime accumulates the length of
        /// whatever is actually stocked and keeps Bun_nagasa equal to it.
        ///
        /// A line the script recolours part-way through is stocked one colour run at a
        /// time instead: the whole translated line cannot go into the first fragment,
        /// because then BUNSYOU_IRO would recolour fragments that no longer carry any
        /// text and the emphasis would vanish. Each run is stocked in the first fragment
        /// that follows its colour change, and fragments that stay in the colour already
        /// stocked contribute nothing.
        /// </summary>
        protected static void BeforeStock(object __instance, ref string __0)
        {
            if (!ready || __0 == null) return;
            // CanvasEx::BUNSYOU has already added the Japanese argument length to
            // SyoriMojiCount before this prefix runs.  That counter gates every line
            // terminator and is decremented by the native character printer.  If the
            // replacement is shorter, leaving the source length here makes the VM wait
            // forever after the last Chinese glyph (and repeatedly play the text sound).
            int sourceLength = __0.Length;
            LineState state = states.GetOrCreateValue(__instance);
            if (state.NewLine)
            {
                int row = Number(__instance, "NowStockMojiDan");
                state.Layouts.Remove(row);
                state.NewLine = false;
                state.Total = 0;
                state.Translated = false;
                state.Runs = null;
                state.ColourRun = 0;
                state.StockedRun = 0;
                string target;
                int fragments;
                if (__0.Length > 0 && pack.TryLine(currentScript, lineOffset, out target, out fragments)
                    && !string.IsNullOrEmpty(target))
                {
                    state.Translated = true;
                    state.Slots = fragments;
                    state.Runs = target.IndexOf(RuntimePack.RunSeparator) < 0
                        ? null
                        : target.Split(RuntimePack.RunSeparator);
                    __0 = state.Runs == null ? target : state.Runs[0];
                    RuntimePack.LayoutLine layout;
                    if (pack.TryLayout(currentScript, lineOffset, out layout)) state.Layouts[row] = layout;
                    substituted++;
                }
            }
            else if (state.Translated)
            {
                if (state.Runs != null && state.ColourRun != state.StockedRun
                    && state.ColourRun < state.Runs.Length)
                {
                    __0 = state.Runs[state.ColourRun];
                    state.StockedRun = state.ColourRun;
                }
                else
                {
                    // The rest of the line lives in later BUNSYOU fragments; this fragment's
                    // run was already stocked, or the line is one colour throughout.
                    __0 = string.Empty;
                }
            }
            int countDelta = __0.Length - sourceLength;
            if (countDelta != 0)
            {
                F("SyoriMojiCount").SetValue(
                    __instance, Number(__instance, "SyoriMojiCount") + countDelta);
            }
            state.Total += __0.Length;
            int limit = Number(__instance, "BunsyouNagasaMax");
            if (limit > 0 && state.Total > limit)
            {
                // The pack builder refuses these, so reaching this means a hand-edited
                // pack; keep drawing rather than desync the line's character run.
                skippedTooLong++;
                Warn("Line exceeds the native budget (" + state.Total + " > " + limit + ")");
            }
            int[] lengths = (int[])F("Bun_nagasa").GetValue(__instance);
            int dan = Number(__instance, "NowStockMojiDan");
            if (lengths != null && dan >= 0 && dan < lengths.Length) lengths[dan] = state.Total;
        }

        /// <summary>Count the colour change a fragment is stocked under.</summary>
        protected static void BeforeColour(object __instance)
        {
            if (!ready) return;
            states.GetOrCreateValue(__instance).ColourRun++;
        }

        /// <summary>Advance the translated run when F7 restores BaseMojiColor.</summary>
        protected static void BeforeF7(object __instance)
        {
            if (!ready) return;
            bool ruby = Convert.ToBoolean(F("NowRubiChu").GetValue(__instance));
            bool colour = Convert.ToBoolean(F("NowMojiColorChangeChu").GetValue(__instance));
            if (!ruby && colour) states.GetOrCreateValue(__instance).ColourRun++;
        }

        /// <summary>
        /// Remove the ordinary dialogue pagination click from full-screen text.
        ///
        /// The native handler must still run while glyph reveal or fade is active.
        /// Once both have completed, returning false releases its MainTask/SubTask
        /// wait state without consuming input or displaying the click cursor.
        /// Vertical modes 1 and 2 are the engine's full-screen layouts; mode 0 is the
        /// ordinary bottom dialogue box and retains every authored COLON wait.
        /// </summary>
        protected static bool BeforeColon(object __instance)
        {
            if (!ready || __instance == null || Number(__instance, "MojiHani_tate") == 0
                || Number(__instance, "SyoriMojiCount") >= 0
                || Convert.ToBoolean(F("NowFadeChu").GetValue(__instance))) return true;
            F("MainTask").SetValue(__instance, 0);
            F("SubTask").SetValue(__instance, 0);
            F("SysCursor_enable").SetValue(__instance, false);
            F("OsippanasiKinsi").SetValue(__instance, false);
            return false;
        }

        /// <summary>Postfix on the handlers that advance NowStockMojiDan: a line just ended.</summary>
        protected static void AfterLine(object __instance)
        {
            if (!ready) return;
            LineState state = states.GetOrCreateValue(__instance);
            if (state.Translated && state.Runs != null && state.StockedRun != state.Runs.Length - 1)
            {
                // Every colour run of a recoloured line has text (the pack builder only
                // records a run when the script puts characters under it), so a run left
                // unstocked means the script offered fewer fragments than the pack expects.
                runsIncomplete++;
                Warn("Colour runs not fully stocked (" + (state.StockedRun + 1) + " of "
                     + state.Runs.Length + " over " + state.Slots + " fragments)");
            }
            state.NewLine = true;
        }

        /// <summary>
        /// Suppress all Japanese ruby while the Chinese runtime is active.
        ///
        /// CanvasEx::BUNSYOU_RUBI records rubi_info_start[i] = RubiCreateCounter and then
        /// rubi_info_kazu[i] = CreateRubiTexture(...) - start, so returning the counter
        /// unchanged makes the ruby cell count zero and the native ruby draw loop has
        /// nothing to draw. No texture is allocated and the script's ruby metadata stays
        /// exactly as shipped. This is deliberately independent of script offsets and
        /// translation lookup: furigana has no place in the Chinese edition.
        /// </summary>
        protected static bool BeforeCreateRubi(object __instance, ref int __result)
        {
            if (!ready) return true;
            __result = Number(__instance, "RubiCreateCounter");
            rubySuppressed++;
            return false;
        }

        /// <summary>
        /// Give Latin letters and digits the same geometry as the eighth game.  The
        /// script still owns character order, colour and timing; only the draw position
        /// changes.  Visual Han/Latin boundary gaps avoid adding buffer cells and keep
        /// every scenario/save offset immutable.
        ///
        /// The native last-row origin is y=222. Its lowest outline pass reaches y=236;
        /// a 16px KBF2 glyph extends four pixels below the game's 12px baseline and
        /// therefore reaches the screen edge. The DrawChar hook lifts only ADV atlas
        /// glyphs by three pixels, leaving rows 237-239 blank without moving shell UI.
        /// </summary>
        protected static void BeforeAdvDraw(object __instance, int __1, int __2, ref int __3, ref int __4,
                                            out bool __state)
        {
            __state = dialogueDraw;
            dialogueDraw = true;
            if (!ready) return;
            string[] lines = (string[])F("Bun_moji").GetValue(__instance);
            if (lines == null || __2 < 0 || __2 >= lines.Length || String.IsNullOrEmpty(lines[__2])
                || __1 < 0 || __1 >= lines[__2].Length) return;

            string text = lines[__2];
            int rowWidth = LatinMetrics.Advance(text, text.Length);
            int align = Number(__instance, "MojiHani_yoko");
            RuntimePack.LayoutLine layout;
            if (align == 0 && states.GetOrCreateValue(__instance).Layouts.TryGetValue(__2, out layout)
                && layout.Text.StartsWith(text, StringComparison.Ordinal) && __1 < layout.X.Length)
            {
                __3 = layout.X[__1];
                __4 += layout.RowDelta[__1] * (StaticNumber("FHeight") + 8);
                return;
            }
            int start;
            if (align == 0)
            {
                // Rows are stocked progressively in this VM. Measuring the rows that
                // happen to exist this frame would move earlier text when a wider row
                // appears. BunsyouNagasaMax is the authored fixed block width; all 7298
                // translated rows fit its 17px grid, including their boundary blanks.
                int blockWidth = Math.Max(rowWidth, Number(__instance, "BunsyouNagasaMax") * 17);
                start = (240 - blockWidth) / 2;
            }
            else if (align == 3) start = 0;
            else if (align == 2) start = 240 - rowWidth;
            else start = (240 - rowWidth) / 2;

            __3 = start + LatinMetrics.Advance(text, __1);
        }

        protected static void RestoreAdvDraw(bool __state) { dialogueDraw = __state; }

        protected static void AfterClearText(object __instance) { states.Remove(__instance); }

        protected static void BeforeNameplatePosition(object __instance, ref int __1, ref int __2, out bool __state)
        {
            BeforeNameplateDraw(out __state);
            if (!ready || Number(__instance, "MojiHani_yoko") != 0) return;
            RuntimePack.LayoutLine layout;
            if (states.GetOrCreateValue(__instance).Layouts.TryGetValue(0, out layout))
            {
                __1 = layout.X[0];
                __2 += layout.NameShift * (StaticNumber("FHeight") + 8);
            }
        }

        protected static void BeforeNameplateDraw(out bool __state)
        {
            __state = nameplateDraw;
            nameplateDraw = true;
        }

        protected static void RestoreNameplateDraw(bool __state) { nameplateDraw = __state; }

        protected static bool BeforeChoiceCenter(object __instance, object __0, int __1, int __2, int __3)
        { return DrawChoice(__instance, __0, __1, 0, __2, __3, true); }

        protected static bool BeforeChoiceLeft(object __instance, object __0, int __1, int __2, int __3, int __4)
        { return DrawChoice(__instance, __0, __1, __2, __3, __4, false); }

        /// <summary>
        /// Draw every choice label with the eighth game's 12px-font metrics.  The
        /// native code measures CP932 bytes, so a Simplified-Chinese character that
        /// cannot be encoded can otherwise truncate the measured width and move or
        /// clip even an all-CJK choice.
        /// </summary>
        protected static bool DrawChoice(object canvas, object graphics, int index, int x, int y,
                                         int color, bool centered)
        {
            if (!ready || graphics == null) return true;
            string[] choices = (string[])F("Sentaku_nafuda").GetValue(canvas);
            if (choices == null || index < 0 || index >= choices.Length || String.IsNullOrEmpty(choices[index]))
                return true;
            string text = choices[index];

            int width = SmallAdvance(text, text.Length);
            if (centered) x = (StaticNumber("Width") - width) / 2;
            y += StaticNumber("FAscent") - StaticNumber("FDocomo") / 2;

            MethodInfo draw = AccessTools.Method(graphics.GetType(), "DrawString",
                new[] { typeof(string), typeof(int), typeof(int) });
            MethodInfo setColor = AccessTools.Method(canvasType, "SetColor",
                new[] { graphicsType, typeof(int) });
            if (draw == null || setColor == null) return true;

            // These are the shipped ninth-game outline passes. Only the advances
            // change; outline shape, baseline and both colour layers stay native.
            int[,] outline = {
                { 0, 1 }, { -1, 0 }, { 0, -1 }, { 1, 0 }, { -1, -1 },
                { 1, -1 }, { 2, -1 }, { 2, 0 }, { -1, 1 }, { 2, 1 },
                { 0, 2 }, { 1, 2 }, { 2, 2 }
            };
            string model = (string)F("model").GetValue(canvas) ?? String.Empty;
            if (!model.StartsWith("N9", StringComparison.Ordinal) &&
                !model.StartsWith("P9", StringComparison.Ordinal) &&
                !model.StartsWith("X", StringComparison.Ordinal))
            {
                setColor.Invoke(canvas, new object[] { graphics, 0 });
                for (int pass = 0; pass < outline.GetLength(0); pass++)
                    DrawChoicePass(graphics, draw, text, x + outline[pass, 0], y + outline[pass, 1]);
            }

            int shadow = (color >> 1) & 0x777777;
            setColor.Invoke(canvas, new object[] { graphics, shadow });
            DrawChoicePass(graphics, draw, text, x + 1, y);
            DrawChoicePass(graphics, draw, text, x + 1, y + 1);
            setColor.Invoke(canvas, new object[] { graphics, color });
            DrawChoicePass(graphics, draw, text, x, y);
            return false;
        }

        private static void DrawChoicePass(object graphics, MethodInfo draw, string text, int x, int y)
        {
            for (int i = 0; i < text.Length; i++)
            {
                char c = text[i];
                if (c != ' ' && c != '　')
                    draw.Invoke(graphics, new object[] {
                        LatinMetrics.Display(c).ToString(), x + SmallAdvance(text, i), y });
            }
        }

        private static int SmallAdvance(string text, int end)
        {
            if (String.IsNullOrEmpty(text) || end <= 0) return 0;
            end = Math.Min(end, text.Length);
            int width = 0;
            for (int i = 0; i < end; i++)
            {
                if (i > 0 && SmallBoundary(text[i - 1], text[i])) width += 6;
                char c = text[i];
                width += c == ' ' || c == '　' ? 6 : LatinMetrics.Narrow(c) ? 7 : 13;
            }
            if (end < text.Length && SmallBoundary(text[end - 1], text[end])) width += 6;
            return width;
        }

        private static bool SmallBoundary(char left, char right)
        {
            return SmallHan(left) && LatinMetrics.Narrow(right)
                || LatinMetrics.Narrow(left) && SmallHan(right);
        }

        private static bool SmallHan(char c)
        {
            return c >= '\u3400' && c <= '\u9fff' || c >= '\uf900' && c <= '\ufaff' || c == '〇';
        }

        /// <summary>True keeps the original DrawCharImpl for this draw.</summary>
        protected static bool BeforeDraw(object __instance, char[] __0, int __1, int __2)        {
            if (!ready || __0 == null || __0.Length == 0) return true;
            Vector2 origin = (Vector2)drawOrigin.GetValue(__instance);
            int lift = dialogueDraw ? 3 : 0;
            BitmapFontAtlas uiFont = dialogueDraw || nameplateDraw ? null : smallFont;
            return LegacyFontRenderer.Draw(__instance, __0, __1 + (int)origin.x,
                                           __2 + (int)origin.y - lift, null, font, 1f, uiFont);
        }

        protected virtual void OnDestroy()
        {
            ready = false;
            if (font != null) { font.Dispose(); font = null; }
            if (smallFont != null) { smallFont.Dispose(); smallFont = null; }
            if (harmony != null) { harmony.UnpatchSelf(); harmony = null; }
        }
    }
}
