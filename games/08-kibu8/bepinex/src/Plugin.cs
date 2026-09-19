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

namespace Kibu8ZhCN
{
    [BepInPlugin("local.kibu8.zhcn", "Kibu8 Simplified Chinese", "0.5.70")]
    [BepInProcess("kibu8.exe")]
    public sealed class Plugin : CanvasRuntime
    {
        public Plugin()
        {
            layout = new RuntimeLayout(12, 5, 18, 32, 17, 11, 13, 6,
                new[] { "PaintMenu", "PaintDocomo", "PaintList", "DrawAdvCommand", "DrawAdvCommandCenter" });
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
                if (pack.Data.gameAssemblySha256 != Hash(File.ReadAllBytes(Path.Combine(Paths.GameRootPath,"kibu8_Data/Managed/Assembly-CSharp.dll"))) ||
                    pack.Data.scratchpadSha256 != Hash(File.ReadAllBytes(Path.Combine(Paths.GameRootPath,"kibu8_Data/StreamingAssets/scratchpad"))))
                    throw new InvalidDataException("Translation pack game identity mismatch");
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
                    "FWidth", "MojiHani_yoko", "info_struct_moji", "info_struct_zenkaku_suu", "info_struct_mojiretu", "info_struct_iro" }) F(name);
                UiLocalization.Initialize(message => Logger.LogInfo(message));
                foreach (ScriptTranslation script in pack.Scripts.Values)
                {
                    foreach (StringTranslation text in script.Strings.Values)
                        if (text.Opcode == 17 || text.Opcode == 80) UiLocalization.RegisterDisplayTranslation(text.Source, text.Target);
                }
                InstallHooks("local.kibu8.zhcn");
                NotebookReading.Install(harmony,canvasType,smallFont,folder);
                PuzzleNotebook.Install(harmony,canvasType);
                ready = true;
                Logger.LogInfo("Chinese runtime ready: " + pack.Scripts.Count + " distinct original scripts; immutable script bytes and save offsets; " + font.GlyphCount + " pixel glyphs.");
                Logger.LogInfo("Original Japanese ruby is disabled on translated rows. Translator notes are parenthesized native dialogue text. Runtime appearance awaits user verification.");
            }
            catch (Exception error)
            {
                ready = false;
                if (harmony != null) harmony.UnpatchSelf();
                UiLocalization.Dispose();
            NotebookReading.Dispose();
                if (font != null) { font.Dispose(); font = null; }
                if (smallFont != null) { smallFont.Dispose(); smallFont = null; }
                Logger.LogError("Chinese plugin disabled: " + error);
            }
        }
        private void Update() { if (ready) UiLocalization.Update(); }
        private void OnDestroy()
        {
            ready = false;
            if (harmony != null) harmony.UnpatchSelf();
            UiLocalization.Dispose();
            NotebookReading.Dispose();
            if (font != null) font.Dispose();
            if (smallFont != null) smallFont.Dispose();
        }
    }
}
