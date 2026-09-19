using System;
using System.IO;
using BepInEx;
using HarmonyLib;
using Kibukawa.Engine.Gmode20050117;

namespace Kibu9ZhCN
{
    [BepInPlugin("local.kibu9.zhcn", "Kibu9 Simplified Chinese", "0.1.22")]
    [BepInProcess("kibu9.exe")]
    public sealed class Plugin : CanvasRuntime
    {
        private void Awake()
        {
            if (!Config.Bind("General", "Enabled", true, "Enable Chinese text; restart after changing.").Value) return;
            try
            {
                Type canvas = AccessTools.TypeByName("CanvasEx");
                if (canvas == null) throw new TypeLoadException("CanvasEx");
                Type graphics = AccessTools.TypeByName("Socotra.UI.StGraphics");
                if (graphics == null) throw new TypeLoadException("Socotra.UI.StGraphics");
                Initialise(Path.GetDirectoryName(Info.Location), canvas, graphics);
                UiLocalization.Initialize(message => Logger.LogInfo(message));
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

        private void Update()
        {
            if (ready) UiLocalization.Update();
        }

        protected override void OnDestroy()
        {
            UiLocalization.Dispose();
            base.OnDestroy();
        }
    }
}
