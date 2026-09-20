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

using Kibukawa.Engine.Gmode20050817;
using Kibukawa.Engine.Gmode20050817Direct;

namespace Kibu10ZhCN
{
    [BepInPlugin("local.kibu10.zhcn", "Kibu10 Simplified Chinese", "0.1.19")]
    [BepInProcess("kibu10.exe")]
    public sealed class Plugin : DirectCanvasRuntime
    {
        public Plugin()
        {
            // append.bin:9454 is the destructive save-reset confirmation. Its
            // native state machine expects the authored four-row buffer.
            preserveDirectDialogueRows.Add("9454\nこれまでのデータを全て\n初期化して、ゲームを\n最初から始めます。\nよろしいですか？");
            layout = new RuntimeLayout(12, 5, 18, 32, 17, 11, 12, 6,
                new[] { "PaintMenu", "PaintDocomo", "DrawAdvCommand", "DrawAdvCommandCenter" });
        }
        private void Awake()
        {
            instance = this;
            exactUi = UiLocalizationData.Exact;
            if (!Config.Bind("General", "Enabled", true, "Enable Chinese text; restart after changing.").Value) return;
            try
            {
                string folder = Path.GetDirectoryName(Info.Location);
                foreach (string line in File.ReadAllLines(Path.Combine(folder, "sources.sha256")))
                {
                    if (String.IsNullOrWhiteSpace(line)) continue;
                    int separator = line.IndexOf("  ", StringComparison.Ordinal);
                    if (separator != 64) throw new InvalidDataException("Invalid source manifest");
                    string relative = line.Substring(66);
                    string path = Path.GetFullPath(Path.Combine(Paths.GameRootPath, relative));
                    string root = Path.GetFullPath(Paths.GameRootPath).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
                    if (!path.StartsWith(root, StringComparison.OrdinalIgnoreCase) || Hash(File.ReadAllBytes(path)) != line.Substring(0, 64))
                        throw new InvalidDataException("Original game source mismatch: " + relative);
                }
                // Unity Mono CP932 substitutes some valid SJIS characters with '?'.
                // Use the game's immutable decoder table for exact source binding.
                var decoderMethod=AccessTools.Method(AccessTools.TypeByName("USEncoder.ToEncoding"), "ToUnicode", new[]{typeof(byte[])});
                if (decoderMethod==null) throw new MissingMethodException("Original SJIS decoder");
                var decoder=(Func<byte[],string>)Delegate.CreateDelegate(typeof(Func<byte[],string>),decoderMethod);
                pack = RuntimePack.Load(Path.Combine(folder, "translations.bin"), ScriptIdentityData.Names, decoder);

                UiLocalizationData.Exact.Clear(); UiLocalizationData.Keys.Clear();
                foreach (var entry in pack.Data.ui) UiLocalizationData.Exact.Add(entry.source,entry.target);
                foreach (var entry in pack.Data.localization) UiLocalizationData.Keys.Add(entry.key,entry.target);
                font = new BitmapFontAtlas(Path.Combine(folder, "fonts"));
                smallFont = new BitmapFontAtlas(Path.Combine(folder, "fonts", "ui-12"));
                canvasType = AccessTools.TypeByName("CanvasEx");
                if (canvasType == null) throw new TypeLoadException("CanvasEx");
                // Resolve required members before applying any patches.
                foreach (string name in new[] { "Script", "Pos", "NowStockingGyou", "BunsyouGun_gyousuu", "BunsyouGun_max_mojisuu",
                    "bg_itigyougun_mojiretu", "bg_itigyougun_zenkakusuu", "bg_itigyougun_color", "bg_itigyougun_control", "bg_itigyougun_rubi_index", "bg_itigyougun_rubisuu",
                    "rollitigyougun_mojiretu", "rollitigyougun_zenkakusuu", "rollitigyougun_color", "rollitigyougun_rubi_index", "rollitigyougun_rubisuu",
                    "FWidth", "MojiHani_yoko", "PrintDanYoyaku", "PrintDanKanryo", "PrintMojiKetaKanryo",
                    "info_struct_moji", "info_struct_zenkaku_suu", "info_struct_mojiretu", "info_struct_iro" }) F(name);
                UiLocalization.Initialize(message => Logger.LogInfo(message));
                foreach (ScriptTranslation script in pack.Scripts.Values)
                {
                    foreach (StringTranslation text in script.Strings.Values)
                        if (text.Opcode == 17 || text.Opcode == 73 || text.Opcode == 80) UiLocalization.RegisterDisplayTranslation(text.Source, text.Target);
                }
                InstallDirectHooks("local.kibu10.zhcn");
                // Kibu10's native INFO painter advances one full-width cell by
                // 12 pixels and one CP932 half-width character by 6 pixels.
                // The shared direct adapter uses the eighth game's 7-pixel
                // Latin advance, so replace only this game's INFO prefix.
                MethodInfo infoPainter = AccessTools.Method(canvasType, "PaintMain_info");
                harmony.Unpatch(infoPainter, AccessTools.Method(typeof(DirectCanvasRuntime), "DrawDirectInfo"));
                harmony.Patch(infoPainter, prefix: new HarmonyMethod(typeof(Plugin), nameof(DrawKibu10Info)));
                ready = true;
                Logger.LogInfo("Chinese runtime ready: " + pack.Scripts.Count + " distinct original scripts; immutable script bytes and save offsets; " + font.GlyphCount + " pixel glyphs.");
                Logger.LogInfo("Original Japanese ruby is disabled on translated rows. Translator notes are parenthesized native dialogue text. Runtime appearance awaits user verification.");
            }
            catch (Exception error)
            {
                ready = false;
                if (harmony != null) harmony.UnpatchSelf();
                UiLocalization.Dispose();
                if (font != null) { font.Dispose(); font = null; }
                if (smallFont != null) { smallFont.Dispose(); smallFont = null; }
                Logger.LogError("Chinese plugin disabled: " + error);
            }
        }
        private void Update() { if (ready) UiLocalization.Update(); }
        internal static int NativeInfoWidth(char value)
        {
            // Match PaintMain_info exactly: ASCII and half-width katakana use
            // half cells; every other character, including U+3000, uses 12 px.
            return value <= '\u007f' || value >= '\uff61' && value <= '\uff9f' ? 6 : 12;
        }
        internal static bool DrawKibu10Info(object __instance, object __0)
        {
            if (!ready) return true;
            RuntimeRow row;
            string source = (string)F("info_struct_moji").GetValue(__instance);
            if (source == null || !infoRows.TryGetValue(source, out row)) return true;
            if (Number(__instance, "FrameTask") != 2 || Number(__instance, "MainTask") == 11
                || (bool)F("NowRoll").GetValue(__instance)) return false;

            int width = DirectTextLayout.MeasureNative(row.Text, 0, row.Text.Length);
            int x = 238 - width;
            int[] palette = (int[])F("ColorTable").GetValue(__instance);
            MethodInfo color = AccessTools.Method(canvasType, "SetColor");
            MethodInfo draw = AccessTools.Method(__0.GetType(), "DrawString", new[] { typeof(string), typeof(int), typeof(int) });
            Type stFont = AccessTools.TypeByName("Socotra.UI.StFont");
            MethodInfo setFont = AccessTools.Method(__0.GetType(), "SetFont", new[] { stFont });
            MethodInfo getFont = AccessTools.Method(stFont, "GetFont", new[] { typeof(int) });
            object previousFont = F("font").GetValue(null);
            bool previous = smallFontScope;
            smallFontScope = true;
            try
            {
                // PaintMain_info selects GetFont(32) before drawing and restores
                // CanvasEx.font afterwards.  Our replacement skips that original
                // method, so reproduce both calls or the top bar inherits the
                // 16px dialogue font that happened to be active beforehand.
                setFont.Invoke(__0, new[] { getFont.Invoke(null, new object[] { 32 }) });
                for (int i = 0; i < row.Text.Length; i++)
                {
                    color.Invoke(__instance, new object[] { __0, palette[row.Colors[i]] });
                    draw.Invoke(__0, new object[] { row.Text[i].ToString(), x + DirectTextLayout.PositionNative(row.Text, i), layout.InfoBaseline });
                }
            }
            finally
            {
                try { setFont.Invoke(__0, new[] { previousFont }); }
                finally { smallFontScope = previous; }
            }
            return false;
        }
        private void OnDestroy()
        {
            ready = false;
            if (harmony != null) harmony.UnpatchSelf();
            UiLocalization.Dispose();
            if (font != null) font.Dispose();
            if (smallFont != null) smallFont.Dispose();
        }
    }
}
