using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Reflection.Emit;
using System.Security.Cryptography;
using BepInEx;
using BepInEx.Configuration;
using HarmonyLib;
using UnityEngine;
using UnityEngine.UI;

namespace Kibu1ZhCN
{
    [BepInPlugin(Id, "Kibu6 Simplified Chinese", "1.0.4")]
    [BepInProcess("kibu6.exe")]
    public sealed class Plugin : BaseUnityPlugin
    {
        public const string Id = "local.kibu6.zhcn";
        private static Plugin instance;
        private static TranslationCatalog catalog;
        private Harmony harmony;
        private static FieldInfo cursor, scenario, selected, strings, opcode, guideImage, helpPage;
        private ConfigEntry<bool> enabledSetting, replaceFonts;
        private ConfigEntry<string> fontNames;
        private static Font chineseFont;
        private static BitmapFontAtlas dialogueFont;
        private static bool ready;
        private int reportedMismatches;
        private int reportedMissingGlyphs;

        private void Awake()
        {
            instance = this;
            enabledSetting = Config.Bind("General", "Enabled", true, "Enable this translation. Restart the game after changing.");
            replaceFonts = Config.Bind("Font", "ReplaceFont", true, "Use standard GNU Unifont for all dialogue characters including Latin, digits and punctuation; fit Chinese UI separately.");
            fontNames = Config.Bind("Font", "FontNames", "Microsoft YaHei,SimSun,Noto Sans CJK SC,Source Han Sans SC,Yu Gothic", "OS fonts for Chinese UI and uncovered dynamic input; bundled pixel dialogue glyphs do not use this setting.");
            if (!enabledSetting.Value) return;
            try
            {
                string dataPath = Path.Combine(Path.GetDirectoryName(Info.Location), "translations.bin");
                TranslationPack pack = TranslationPackReader.Load(dataPath);
                if (replaceFonts.Value) dialogueFont = new BitmapFontAtlas(Path.Combine(Path.GetDirectoryName(Info.Location),"fonts"));
                string managed = Path.Combine(Paths.GameRootPath, "kibu6_Data", "Managed", "Assembly-CSharp.dll");
                string archive = Path.Combine(Paths.GameRootPath, "kibu6_Data", "StreamingAssets", "scratchpad");
                if (!MatchesHash(managed, pack.gameAssemblySha256) || !MatchesHash(archive, pack.scratchpadSha256))
                    throw new InvalidOperationException("Original game version mismatch. Restore unmodified game files before using the BepInEx edition.");
                catalog = new TranslationCatalog(pack);
                RuntimeImages.Initialize(Path.Combine(Path.GetDirectoryName(Info.Location), "images"));
                Type canvas = AccessTools.TypeByName("appli1.CanvasEx");
                if (canvas == null) throw new MissingMemberException("appli1.CanvasEx is missing");
                cursor = RequireField(canvas, "ScCur"); scenario = RequireField(canvas, "Scenario");
                selected = RequireField(canvas, "ScSelect"); strings = RequireField(canvas, "ScStr"); opcode = RequireField(canvas, "Cmd");
                DialogueReflow.Initialize(canvas);
                MenuSelectionMemory.Initialize(canvas);
                harmony = new Harmony(Id);
                Patch(AccessTools.Method(canvas, "InitCanvasEx"), "BeforeCanvasInit", null);
                Patch(AccessTools.Method(canvas, "Read"), "BeforeRead", "AfterRead");
                Patch(AccessTools.Method(canvas, "Script"), null, "AfterScript");
                harmony.Patch(AccessTools.EnumeratorMoveNext(AccessTools.Method(canvas, "Script")), transpiler: new HarmonyMethod(typeof(Plugin), "RememberMenuInitialSelection"));
                Patch(AccessTools.Method(canvas, "Jump", new[] { typeof(bool), typeof(int) }), "BeforeJump", null);
                Patch(AccessTools.Method(canvas, "ExeText", new[] { typeof(string), typeof(int) }), null, "AfterExeText");
                Patch(AccessTools.PropertySetter(typeof(Text), "text"), "BeforeText", "AfterTextEnabled");
                Patch(AccessTools.Method(typeof(Text), "OnEnable"), null, "AfterTextEnabled");
                Type localize = AccessTools.TypeByName("Steezy.Localize.Localization");
                Patch(AccessTools.Method(localize, "Get", new[] { typeof(string) }), null, "AfterLocalized");
                Type graphics = AccessTools.TypeByName("Socotra.UI.StGraphics");
                Patch(AccessTools.Method(graphics, "DrawCharImpl"), "BeforeDraw", null);
                Type help = AccessTools.TypeByName("HowToPlayDialog");
                guideImage = RequireField(help, "guideImage");
                helpPage = RequireField(help, "nowPage");
                Patch(AccessTools.Method(help, "ChangePage", new[] { typeof(int) }), null, "AfterHelpPage");
                // Non-scenario game literals are replaced in JIT code only. The assembly file stays intact.
                foreach (int token in catalog.Literals.Keys)
                {
                    MethodBase method = canvas.Module.ResolveMethod(token);
                    harmony.Patch(method, transpiler: new HarmonyMethod(typeof(Plugin), "TranslateLiterals"));
                }
                ready = true;
                Logger.LogInfo("Loaded " + pack.scripts.Length + " contextual script translations; original resources remain untouched.");
                if (dialogueFont != null) Logger.LogInfo("GNU Unifont dialogue: " + dialogueFont.GlyphCount + " glyphs; Chinese, Latin, digits and punctuation share native 16px height.");
                Logger.LogInfo("Chinese help pages: " + RuntimeImages.HelpPageCount + "; original dialog navigation retained.");
                Logger.LogInfo("Chinese dialogue reflow: 20 half-cells (10 full-width glyphs, native horizontal bounds) / 20-character buffer; at most 5 unread rows, or 4 with a speaker; acknowledged history scrolls normally, only original commands clear the screen.");
                StartCoroutine(RefreshText());
            }
            catch (Exception error)
            {
                ready = false;
                if (harmony != null) harmony.UnpatchSelf();
                DialogueReflow.Reset();
                MenuSelectionMemory.Reset();
                UiFontPolicy.Reset();
                RuntimeImages.Dispose();
                if (dialogueFont != null) { dialogueFont.Dispose(); dialogueFont = null; }
                if (chineseFont != null) { UnityEngine.Object.Destroy(chineseFont); chineseFont = null; }
                Logger.LogError("Chinese plugin disabled: " + error);
            }
        }
        private static bool MatchesHash(string path, string expected)
        {
            using (SHA256 hash = SHA256.Create())
            using (FileStream stream = File.OpenRead(path))
                return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").Equals(expected, StringComparison.OrdinalIgnoreCase);
        }
        private static FieldInfo RequireField(Type type, string name)
        {
            FieldInfo field = type == null ? null : AccessTools.Field(type, name);
            if (field == null) throw new MissingFieldException(type == null ? "missing type" : type.FullName, name);
            return field;
        }
        private void Patch(MethodBase target, string prefix, string postfix)
        {
            if (target == null) throw new MissingMethodException("Required hook: " + prefix + "/" + postfix);
            harmony.Patch(target, prefix == null ? null : new HarmonyMethod(typeof(Plugin), prefix), postfix == null ? null : new HarmonyMethod(typeof(Plugin), postfix));
        }
        private static void BeforeCanvasInit()
        {
            if (!ready) return;
            DialogueReflow.Reset();
            MenuSelectionMemory.Reset();
        }
        private static void BeforeRead(object __instance, out int __state)
        {
            __state = (int)cursor.GetValue(__instance);
        }
        private static void AfterRead(object __instance, int __state)
        {
            if (!ready) return;
            string script = TranslationCatalog.ScriptName(Convert.ToInt32(scenario.GetValue(__instance)), Convert.ToInt32(selected.GetValue(__instance)));
            string[] values = (string[])strings.GetValue(__instance);
            DialogueReflow.RecordSource(__instance, (int)opcode.GetValue(__instance), values.Length == 0 ? null : values[0], false, FixedCardLayout.IsActive(script,__state));
            catalog.ApplyScript(script, __state, (int)opcode.GetValue(__instance), values);
            MenuSelectionMemory.RecordMenu(__instance, __state);
            // No writes to ScData, ScCur, jump arguments, or saved offsets.
        }
        private static void AfterScript(object __instance, ref IEnumerator __result)
        {
            if (ready && !DialogueReflow.IsBypassed) __result = DialogueReflow.Wrap(__instance, __result);
        }
        private static void BeforeJump(object __instance)
        {
            if (ready) MenuSelectionMemory.Remember(__instance);
        }
        private static IEnumerable<CodeInstruction> RememberMenuInitialSelection(IEnumerable<CodeInstruction> instructions)
        {
            // At Select[1] = 0, the stack is [selectionArray, 1]. Load the
            // iterator's CanvasEx instead of zero, before input/highlight handling.
            var code = new List<CodeInstruction>(instructions);
            int patched = 0;
            for (int i=3; i+1<code.Count; i++)
            {
                FieldInfo selection = code[i-2].operand as FieldInfo;
                if (code[i].opcode != OpCodes.Ldc_I4_0 || code[i-1].opcode != OpCodes.Ldc_I4_1 ||
                    code[i-2].opcode != OpCodes.Ldfld || selection == null || selection.Name != "Select" ||
                    code[i+1].opcode != OpCodes.Stelem_I1) continue;
                // Mono's iterator uses a cached local CanvasEx, rather than
                // necessarily loading <>4__this directly. Reuse its exact load.
                CodeInstruction load = code[i-3];
                if (load.opcode != OpCodes.Ldloc_0 && load.opcode != OpCodes.Ldloc_1 &&
                    load.opcode != OpCodes.Ldloc_2 && load.opcode != OpCodes.Ldloc_3 &&
                    load.opcode != OpCodes.Ldloc && load.opcode != OpCodes.Ldloc_S)
                    throw new InvalidOperationException("Unexpected menu owner load; refusing to patch.");
                code[i].opcode = load.opcode; code[i].operand = load.operand;
                code.Insert(i+1,new CodeInstruction(OpCodes.Call,AccessTools.Method(typeof(MenuSelectionMemory),"Restore")));
                patched++; i++;
            }
            if (patched != 2) throw new InvalidOperationException("Expected both menu selection initializers, found " + patched);
            return code;
        }
        private static void AfterExeText(object __instance, string Str, int Type)
        {
            if (ready) DialogueReflow.AfterExeText(__instance, Str, Type);
        }
        private static void BeforeText(Text __instance, ref string value)
        {
            if (ready) { UiFontPolicy.Capture(__instance); value = catalog.TranslateUI(value); }
        }
        private static void AfterTextEnabled(Text __instance)
        {
            if (ready) RefreshOne(__instance);
        }
        private static void AfterLocalized(string key, ref string __result)
        {
            string translated;
            if (ready && catalog.TryLocalize(key, out translated)) __result = translated;
        }
        private static Font GetFont(bool force = false)
        {
            if (!instance.replaceFonts.Value && !force) return null;
            if (chineseFont == null)
            {
                string[] names = instance.fontNames.Value.Split(',');
                for (int i = 0; i < names.Length; i++) names[i] = names[i].Trim();
                chineseFont = Font.CreateDynamicFontFromOSFont(names, 16);
                if (chineseFont != null)
                {
                    UnityEngine.Object.DontDestroyOnLoad(chineseFont);
                    instance.Logger.LogInfo("Dynamic Chinese font: " + string.Join(", ", names));
                }
            }
            return chineseFont;
        }
        private static bool BeforeDraw(object __instance, char[] cText, int offsetX, int offsetY)
        {
            if (!ready || !instance.replaceFonts.Value) return true;
            return LegacyFontRenderer.Draw(__instance, cText, offsetX, offsetY, GetFont(), dialogueFont);
        }
        private static void AfterHelpPage(object __instance)
        {
            if (!ready) return;
            Image guide = (Image)guideImage.GetValue(__instance);
            if (guide == null || guide.sprite == null) return;
            int page = (int)helpPage.GetValue(__instance);
            RuntimeImages.ShowHelp(guide, page);
        }
        private static void RefreshOne(Text text)
        {
            if (text == null) return;
            UiFontPolicy.Capture(text);
            string translated = catalog.TranslateUI(text.text);
            if (translated != text.text) text.text = translated;
            Font font = GetFont();
            UiFontPolicy.Apply(text, font);
        }
        private IEnumerator RefreshText()
        {
            // Serialized labels may predate hook installation; refresh only Text components.
            while (ready)
            {
                foreach (Text text in Resources.FindObjectsOfTypeAll<Text>()) RefreshOne(text);
                if (dialogueFont != null && dialogueFont.MissingGlyphCount != reportedMissingGlyphs)
                {
                    reportedMissingGlyphs = dialogueFont.MissingGlyphCount;
                    Logger.LogWarning("Unifont encountered " + reportedMissingGlyphs + " unbundled dynamic characters; using its replacement glyph.");
                }
                if (catalog.SourceMismatches != reportedMismatches)
                {
                    reportedMismatches = catalog.SourceMismatches;
                    Logger.LogWarning("Translation source mismatches: " + reportedMismatches + "; original text preserved for those slots.");
                }
                yield return new WaitForSecondsRealtime(2f);
            }
        }
        private static IEnumerable<CodeInstruction> TranslateLiterals(IEnumerable<CodeInstruction> instructions, MethodBase __originalMethod)
        {
            Dictionary<int, LiteralEntry> replacements = catalog.Literals[__originalMethod.MetadataToken];
            int ordinal = 0, applied = 0;
            foreach (CodeInstruction instruction in instructions)
            {
                LiteralEntry entry;
                if (replacements.TryGetValue(ordinal, out entry))
                {
                    if (instruction.opcode != OpCodes.Ldstr || (string)instruction.operand != entry.source)
                        throw new InvalidOperationException("Literal hook mismatch at " + __originalMethod + " instruction " + ordinal);
                    instruction.operand = entry.target;
                    applied++;
                }
                ordinal++;
                yield return instruction;
            }
            if (applied != replacements.Count) throw new InvalidOperationException("Not all literal translations were applied: " + __originalMethod);
        }
        private void OnDestroy()
        {
            ready = false;
            if (harmony != null) harmony.UnpatchSelf();
            DialogueReflow.Reset();
            MenuSelectionMemory.Reset();
            UiFontPolicy.Reset();
            RuntimeImages.Dispose();
            if (dialogueFont != null) { dialogueFont.Dispose(); dialogueFont=null; }
            if (chineseFont != null) { UnityEngine.Object.Destroy(chineseFont); chineseFont = null; }
            catalog = null;
            instance = null;
        }
    }
}
