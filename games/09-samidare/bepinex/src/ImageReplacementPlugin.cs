using System;
using BepInEx;
using HarmonyLib;
using Kibukawa.Engine.Gmode20050817;

namespace Kibu9ZhCN.Images
{
    [BepInPlugin("heptagon.kibukawa9.imagereplacements.zhcn", "Kibukawa 9 Image Replacements", "1.0.1")]
    [BepInProcess("kibu9.exe")]
    public sealed class ImageReplacementPlugin : NamedImageRuntime
    {
        protected override string GameId { get { return "kibu9"; } }
        protected override int ChapterCount { get { return 1; } }
        private void Awake() { InitializeImages(); }
        private void OnDestroy() { Cleanup(); }
        private void Update() { TickImages(); }

        protected override void InitializeArtwork(string folder, Type canvas, Harmony hooks)
        {
            TitleBackground.Initialize(folder, canvas, hooks, message => Logger.LogWarning(message));
            ShellCover.Initialize(folder);
            HowToPlayPages.Initialize(folder, hooks);
        }

        protected override void DisposeArtwork()
        {
            TitleBackground.Dispose();
            ShellCover.Dispose();
            HowToPlayPages.Dispose();
        }

        protected override void UpdateArtwork() { ShellCover.Update(); }
    }
}
