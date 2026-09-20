using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using BepInEx;
using HarmonyLib;
using Kibukawa.Engine.Gmode20050817;
using Kibukawa.ImageReplacements;

namespace Kibu10ZhCN.Images
{
    [BepInPlugin("heptagon.kibukawa.imagereplacements.zhcn", "Kibukawa Image Replacements", "1.0.4")]
    [BepInProcess("kibu10.exe")]
    public sealed class ImageReplacementPlugin : NamedImageRuntime
    {
        protected override string GameId { get { return "kibu10"; } }
        protected override int ChapterCount { get { return 1; } }
        private static readonly Dictionary<string,TextureReplacement> brightness=new Dictionary<string,TextureReplacement>();
        private void Awake() { InitializeImages(); }
        private void OnDestroy() { Cleanup(); }
        private void Update() { TickImages(); }
        protected override void InitializeArtwork(string folder,Type canvas,Harmony hooks)
        {
            foreach(string name in new[]{"t_start","t_help","t_append"})
                foreach(int level in new[]{900,700,500,400})
                {
                    string key="resource:///"+name+".gif.bytes#"+level;
                    var item=new TextureReplacement();
                    item.Initialize(Path.Combine(folder,"images",name+"-"+level+".rgba"),message=>Logger.LogWarning(message),0,0,true);
                    brightness.Add(key,item);
                }
            var loader=AccessTools.Method(canvas,"LoadGraphic2",new[]{typeof(string),typeof(int)});
            if(loader==null || loader.ReturnType.FullName!="Socotra.UI.Image") throw new MissingMethodException("CanvasEx.LoadGraphic2");
            hooks.Patch(loader,postfix:new HarmonyMethod(typeof(ImageReplacementPlugin),nameof(AfterBrightness)));
            NativeArtwork.Initialize(folder,canvas,hooks);
            TitleMenuOverlay.Initialize(folder,canvas,hooks);
            ShellCover.Initialize(folder);
            ShellLogos.Initialize(folder,hooks);
            HowToPlayPages.Initialize(folder,hooks);
        }
        private static void AfterBrightness(string __0,int __1,ref object __result)
        {
            TextureReplacement item;
            if(brightness.TryGetValue(__0+"#"+__1,out item)) __result=item.Replace(__result);
        }
        protected override void DisposeArtwork()
        {
            HowToPlayPages.Dispose();ShellLogos.Dispose();ShellCover.Dispose();TitleMenuOverlay.Dispose();NativeArtwork.Dispose();
            foreach(var item in brightness.Values)item.Reset();brightness.Clear();
        }
        protected override void UpdateArtwork() { ShellCover.Update();ShellLogos.Update(); }
    }
}
