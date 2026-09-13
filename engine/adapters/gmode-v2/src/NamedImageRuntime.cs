using System;
using System.IO;
using System.Collections.Generic;
using System.Reflection;
using BepInEx;
using HarmonyLib;
using Kibukawa.ImageReplacements;

namespace Kibukawa.Engine.Gmode20050817
{
    public abstract class NamedImageRuntime : BaseUnityPlugin
    {
        protected abstract string GameId { get; }
        protected abstract int ChapterCount { get; }
        protected virtual int[] ExpectedSourceSize(string id) { return null; }
        protected virtual void InitializeArtwork(string folder,Type canvas,Harmony hooks) { }
        protected virtual void RegisterArtwork(string name,object image) { }
        protected virtual void DisposeArtwork() { }
        protected virtual void UpdateArtwork() { }
        protected virtual void DisableArtworkRegistration() { }
        protected bool ImagesReady { get { return ready; } }
        private static readonly Dictionary<string,TextureReplacement> routes = new Dictionary<string,TextureReplacement>(StringComparer.Ordinal);
        private static readonly HashSet<string> logged = new HashSet<string>(StringComparer.Ordinal);
        private static NamedImageRuntime instance;
        private static bool ready;
        private Harmony harmony;
        private static Type archiveType;
        private static PropertyInfo appliIndex;
        private static UnityEngine.Object archive;
        protected void InitializeImages()
        {
            try
            {
                instance=this;
                string folder=Path.GetDirectoryName(Info.Location);
                string gameRoot=Path.GetFullPath(Paths.GameRootPath).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
                foreach(string line in File.ReadAllLines(Path.Combine(folder,"image-sources.sha256")))
                {
                    if(String.IsNullOrWhiteSpace(line)) continue;
                    if(line.Length<67 || line.Substring(64,2)!="  ") throw new InvalidDataException("Invalid image source manifest");
                    string path=Path.GetFullPath(Path.Combine(gameRoot,line.Substring(66)));
                    if(!path.StartsWith(gameRoot,StringComparison.OrdinalIgnoreCase) || ReplacementManifest.Hash(File.ReadAllBytes(path))!=line.Substring(0,64))
                        throw new InvalidDataException("Original image resources changed");
                }
                var manifest=ReplacementManifest.Read(Path.Combine(Path.GetDirectoryName(Info.Location),"image-replacements.tsv"));
                if(manifest.Game!=GameId || Path.GetFileNameWithoutExtension(Paths.ExecutablePath)!=manifest.Game)
                    throw new InvalidDataException("Image pack belongs to another game");
                if(ReplacementManifest.Hash(File.ReadAllBytes(Path.Combine(Paths.ManagedPath,"Assembly-CSharp.dll")))!=manifest.AssemblyHash)
                    throw new InvalidDataException("Unverified game assembly");
                string scratchpad=Path.Combine(Path.GetDirectoryName(Paths.ManagedPath),"StreamingAssets","scratchpad");
                if(ReplacementManifest.Hash(File.ReadAllBytes(scratchpad))!=manifest.ScratchpadHash)
                    throw new InvalidDataException("Unverified game image archive");
                var loaders=new HashSet<string>(StringComparer.Ordinal);
                bool needsChapterSelector=false;
                foreach(var entry in manifest.Entries)
                {
                    int split=entry.Canvas.IndexOf('@');
                    if(split<1 || entry.Index!=0) throw new InvalidDataException("Invalid named image route");
                    string selector=entry.Canvas.Substring(0,split), name=entry.Canvas.Substring(split+1);
                    int hash=selector.IndexOf('#');
                    if(hash<0) throw new InvalidDataException("Missing chapter selector");
                    string loader=selector.Substring(0,hash), chapter=selector.Substring(hash+1);
                    int chapterNumber;
                    if(chapter!="*" && (!Int32.TryParse(chapter,out chapterNumber) || chapterNumber<0 || chapterNumber>=ChapterCount)) throw new InvalidDataException("Invalid chapter selector");
                    if(chapter!="*") needsChapterSelector=true;
                    if(loader!="CanvasEx.LoadGraphic" && loader!="CanvasEx.Image_createImage") throw new InvalidDataException("Unsupported image loader");
                    string key=loader+"#"+chapter+"@"+Normalize(loader,name);
                    if(routes.ContainsKey(key)) throw new InvalidDataException("Duplicate normalized image route");
                    var texture=new TextureReplacement();
                    int[] expected=ExpectedSourceSize(entry.Id);
                    texture.Initialize(entry.Payload,message=>Logger.LogWarning(entry.Id+": "+message),expected==null?0:expected[0],expected==null?0:expected[1],true);
                    routes.Add(key,texture); loaders.Add(loader);
                }
                archiveType=AccessTools.TypeByName("AppliArchive");
                appliIndex=archiveType==null ? null : AccessTools.Property(archiveType,"AppliIndex");
                if(needsChapterSelector && appliIndex==null) throw new MissingMemberException("AppliArchive.AppliIndex");
                harmony=new Harmony(Info.Metadata.GUID);
                Type canvas=AccessTools.TypeByName("CanvasEx");
                foreach(string loader in loaders)
                {
                    MethodInfo method=AccessTools.Method(canvas,loader.Substring("CanvasEx.".Length),new[]{typeof(string)});
                    if(method==null || method.ReturnType.FullName!="Socotra.UI.Image") throw new MissingMethodException(loader);
                    harmony.Patch(method,postfix:new HarmonyMethod(typeof(NamedImageRuntime),nameof(AfterImage)));
                }
                InitializeArtwork(folder,canvas,harmony);
                ready=true;
                Logger.LogInfo("Enabled "+routes.Count+" named image routes; original resource decoder retained.");
            }
            catch(Exception error) { Cleanup(); Logger.LogError("Image replacements disabled; keeping originals: "+error); }
        }
        private static string Normalize(string loader,string name)
        {
            if(String.IsNullOrEmpty(name) || name.IndexOfAny(new[]{'\t','\r','\n','@'})>=0) throw new InvalidDataException("Invalid image resource name");
            // Follow LoadGraphic's exact extension rule; preserve resource paths/case.
            return loader=="CanvasEx.LoadGraphic" && name.IndexOf('.')<0 ? name+".gif" : name;
        }
        private static void AfterImage(MethodBase __originalMethod,string __0,ref object __result)
        {
            if(!ready || __result==null || String.IsNullOrEmpty(__0)) return;
            string loader="CanvasEx."+__originalMethod.Name;
            if(archive==null && archiveType!=null) archive=UnityEngine.Object.FindObjectOfType(archiveType);
            string chapter=archive==null || appliIndex==null ? "?" : Convert.ToInt32(appliIndex.GetValue(archive,null)).ToString();
            string tail="@"+Normalize(loader,__0), key=loader+"#"+chapter+tail;
            TextureReplacement replacement;
            if(!routes.TryGetValue(key,out replacement))
            {
                key=loader+"#*"+tail;
                if(!routes.TryGetValue(key,out replacement)) return;
            }
            object original=__result;
            __result=replacement.Replace(original);
            if(!Object.ReferenceEquals(original,__result))
            {
                try { instance.RegisterArtwork(Normalize(loader,__0),__result); }
                catch(Exception error) { instance.DisableArtworkRegistration(); instance.Logger.LogWarning("Artwork registration disabled: "+error.Message); }
            }
            if(!Object.ReferenceEquals(original,__result) && logged.Add(key)) instance.Logger.LogInfo("Replaced "+key);
        }
        protected void Cleanup()
        {
            ready=false;
            if(harmony!=null) harmony.UnpatchSelf();
            DisposeArtwork();
            foreach(var replacement in routes.Values) replacement.Reset();
            routes.Clear(); logged.Clear(); archive=null; archiveType=null; appliIndex=null;
        }
        protected void TickImages() { if(ready) UpdateArtwork(); }
    }
}
