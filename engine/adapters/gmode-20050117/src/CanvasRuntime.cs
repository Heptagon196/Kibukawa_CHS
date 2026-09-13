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
    /// Because Bun_iro is filled per character, BUNSYOU_IRO recolours the rest of a
    /// line: that is how the script emphasises the clue word or the name a line turns
    /// on. Those lines are stocked one colour run at a time, so the emphasis stays on
    /// the characters it falls on in Japanese.
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
        protected static readonly List<string> literals = new List<string>();
        protected Harmony harmony;

        private static readonly Dictionary<string, FieldInfo> instanceFields = new Dictionary<string, FieldInfo>();
        private static readonly Dictionary<string, FieldInfo> staticFields = new Dictionary<string, FieldInfo>();
        private static readonly ConditionalWeakTable<object, LineState> states = new ConditionalWeakTable<object, LineState>();

        /// <summary>Per-canvas state for the display line currently being stocked.</summary>
        private sealed class LineState
        {
            public bool NewLine = true;
            public bool Translated;
            public int Total;
            public int Slots;
            // A recoloured line arrives as one string per colour run. ColourRun counts the
            // BUNSYOU_IRO commands run since this line started — the run the next fragment
            // belongs to — and StockedRun is the last run already stocked.
            public string[] Runs;
            public int ColourRun;
            public int StockedRun;
        }

        /// <summary>Members the runtime resolves before it patches anything.</summary>
        protected static readonly string[] RequiredFields = {
            "Bun_moji", "Bun_iro", "Bun_speed", "Bun_alpha", "Bun_jikan", "Bun_nagasa",
            "BunsyouNagasaMax", "DanNoKazu", "NowStockMojiDan", "NowStockMojiKeta",
            "NowPrintingDan", "NowPrintingKeta", "SyoriMojiCount", "RubiCreateCounter"
        };

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
            drawOrigin = AccessTools.Field(graphicsType, "drawOrigin");
            if (drawOrigin == null) throw new MissingFieldException("StGraphics.drawOrigin");
            pack = loaded;
            font = new BitmapFontAtlas(Path.Combine(pluginFolder, "fonts"));
            harmony = new Harmony(GetType().FullName);
            InstallHooks();
            InstallChoiceMemory();
            ready = true;
            Log("Kibu9 Chinese runtime ready: " + pack.LineCount + " lines, " + font.GlyphCount + " glyphs.");
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
            // Nameplates and menu labels are StringRead operands stored straight into
            // the native arrays, so they are replaced where they are read.
            Patch(AccessTools.Method(canvasType, "NAMAE_SETTEI"), "BeforeName", null);
            Patch(AccessTools.Method(canvasType, "SENTAKUSI"), "BeforeChoice", null);
            Patch(AccessTools.Method(canvasType, "StringRead"), null, "AfterStringRead");
            // These are exactly the handlers that advance NowStockMojiDan, so their
            // postfix marks the moment the next BUNSYOU starts a new display line.
            foreach (string name in LineTerminators)
            {
                MethodInfo method = AccessTools.Method(canvasType, name);
                if (method == null) throw new MissingMethodException(canvasType.FullName, name);
                Patch(method, null, "AfterLine");
            }
            // The single glyph choke point: DrawString and DrawChars both funnel here.
            Patch(AccessTools.Method(graphicsType, "DrawCharImpl", new[] { typeof(char[]), typeof(int), typeof(int) }), "BeforeDraw", null);
            // Japanese ruby is a reading of the original base text; over a translated
            // line it would overlay kana on the wrong characters.
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
            LineState state = states.GetOrCreateValue(__instance);
            if (state.NewLine)
            {
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
        /// Suppress the Japanese ruby of a translated line.
        ///
        /// CanvasEx::BUNSYOU_RUBI records rubi_info_start[i] = RubiCreateCounter and then
        /// rubi_info_kazu[i] = CreateRubiTexture(...) - start, so returning the counter
        /// unchanged makes the ruby cell count zero and the native ruby draw loop has
        /// nothing to draw. No texture is allocated and the script's ruby metadata stays
        /// exactly as shipped; untranslated lines keep their ruby.
        ///
        /// The ruby command precedes its base BUNSYOU, and by the time the texture is
        /// built the operands are consumed, so Pos is exactly the base command's offset.
        /// </summary>
        protected static bool BeforeCreateRubi(object __instance, ref int __result)
        {
            if (!ready) return true;
            string target;
            int fragments;
            if (!pack.TryLine(currentScript, Number(__instance, "Pos"), out target, out fragments)
                || string.IsNullOrEmpty(target)) return true;
            __result = Number(__instance, "RubiCreateCounter");
            rubySuppressed++;
            return false;
        }

        /// <summary>True keeps the original DrawCharImpl for this draw.</summary>
        protected static bool BeforeDraw(object __instance, char[] __0, int __1, int __2)        {
            if (!ready || __0 == null || __0.Length == 0) return true;
            Vector2 origin = (Vector2)drawOrigin.GetValue(__instance);
            return LegacyFontRenderer.Draw(__instance, __0, __1 + (int)origin.x, __2 + (int)origin.y, null, font);
        }

        protected virtual void OnDestroy()
        {
            ready = false;
            if (font != null) { font.Dispose(); font = null; }
            if (harmony != null) { harmony.UnpatchSelf(); harmony = null; }
        }
    }
}
