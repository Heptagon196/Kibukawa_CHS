using System;
using System.IO;
using System.Collections.Generic;
using System.Reflection;
using BepInEx;
using HarmonyLib;

namespace Kibukawa.ImageReplacements
{
    [BepInPlugin("heptagon.kibukawa.imagereplacements.zhcn", "Kibukawa Image Replacements", "1.1.0")]
    public sealed class ImageReplacementPlugin : BaseUnityPlugin
    {
        private static readonly Dictionary<string,TextureReplacement> routes=new Dictionary<string,TextureReplacement>();
        private static readonly HashSet<string> logged=new HashSet<string>();
        private static ImageReplacementPlugin instance;
        private static bool ready;
        private Harmony harmony;
        private void Awake()
        {
            try
            {
                string directory=Path.GetDirectoryName(Info.Location);
                var manifest=ReplacementManifest.Read(Path.Combine(directory,"image-replacements.tsv"));
                if(Path.GetFileNameWithoutExtension(Paths.ExecutablePath)!=manifest.Game)
                    throw new InvalidDataException("Image pack belongs to another game");
                if(ReplacementManifest.Hash(File.ReadAllBytes(Path.Combine(Paths.ManagedPath,"Assembly-CSharp.dll")))!=manifest.AssemblyHash)
                    throw new InvalidDataException("Unverified game assembly");
                string scratchpad=Path.Combine(Path.GetDirectoryName(Paths.ManagedPath),"StreamingAssets","scratchpad");
                if(ReplacementManifest.Hash(File.ReadAllBytes(scratchpad))!=manifest.ScratchpadHash)
                    throw new InvalidDataException("Unverified game image archive");
                instance=this;
                harmony=new Harmony("heptagon.kibukawa.imagereplacements.zhcn");
                var canvases=new HashSet<string>();
                foreach(var entry in manifest.Entries)
                {
                    var texture=new TextureReplacement();
                    string label=entry.Id+" ("+entry.Key+")";
                    texture.Initialize(entry.Payload,message=>Logger.LogWarning(label+": "+message));
                    routes.Add(entry.Key,texture);
                    canvases.Add(entry.Canvas);
                }
                foreach(string name in canvases)
                {
                    Type type=AccessTools.TypeByName(name);
                    MethodInfo method=AccessTools.Method(type,"ReadImg",new[]{typeof(int)});
                    if(method==null || method.ReturnType.FullName!="Socotra.UI.Image") throw new MissingMethodException(name+".ReadImg");
                    harmony.Patch(method,postfix:new HarmonyMethod(typeof(ImageReplacementPlugin),nameof(AfterReadImage)));
                }
                ready=true;
                Logger.LogInfo("Enabled "+routes.Count+" configured image routes via ReadImg; original image decoder unchanged");
            }
            catch(Exception error)
            {
                Cleanup();
                Logger.LogError("Image replacements disabled; keeping originals: "+error);
            }
        }
        private static void AfterReadImage(object __instance,int __0,ref object __result)
        {
            if(!ready || __instance==null) return;
            string key=__instance.GetType().FullName+":"+__0;
            TextureReplacement texture;
            if(!routes.TryGetValue(key,out texture)) return;
            object original=__result;
            __result=texture.Replace(original);
            if(!Object.ReferenceEquals(original,__result) && logged.Add(key))
                instance.Logger.LogInfo("Replaced image "+key+" with independently owned RGBA texture");
        }
        private void Cleanup()
        {
            ready=false;
            if(harmony!=null) harmony.UnpatchSelf();
            foreach(var replacement in routes.Values) replacement.Reset();
            routes.Clear();logged.Clear();
        }
        private void OnDestroy() { Cleanup(); }
    }
}
