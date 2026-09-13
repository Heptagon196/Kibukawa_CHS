using System;
using System.IO;
using System.Reflection;
using BepInEx;
using HarmonyLib;
using Kibukawa.Engine.Gmode20050817;

namespace Kibu8ZhCN.Images
{
    [BepInPlugin("heptagon.kibukawa.imagereplacements.zhcn", "Kibukawa Image Replacements", "1.2.3")]
    [BepInProcess("kibu8.exe")]
    public sealed class ImageReplacementPlugin : NamedImageRuntime
    {
        protected override string GameId { get { return "kibu8"; } }
        protected override int ChapterCount { get { return 3; } }
        protected override int[] ExpectedSourceSize(string id) { return id=="memo-tab"?new[]{18,32}:null; }
        private static ImageReplacementPlugin instance;
        private void Awake() { instance=this; InitializeImages(); }
        private void OnDestroy() { Cleanup(); }
        private void Update() { TickImages(); }
        protected override void InitializeArtwork(string folder,Type canvas,Harmony hooks)
        {
            ShellCover.Initialize(folder);
            TitleMenu.Initialize(canvas);
            hooks.Patch(AccessTools.Method(canvas,"PaintTitle"),prefix:new HarmonyMethod(typeof(ImageReplacementPlugin),nameof(BeforeTitle)));
        }
        protected override void RegisterArtwork(string name,object image) { TitleMenu.Register(name,image); }
        protected override void DisposeArtwork() { ShellCover.Dispose(); TitleMenu.Dispose(); }
        protected override void DisableArtworkRegistration() { TitleMenu.Dispose(); }
        protected override void UpdateArtwork() { ShellCover.Update(); }
        private static bool BeforeTitle(object __instance,object __0)
        {
            if(!instance.ImagesReady) return true;
            try { return !TitleMenu.Draw(__instance,__0); }
            catch(Exception error) { TitleMenu.Dispose(); instance.Logger.LogWarning("Title menu alignment disabled: "+error.Message); return true; }
        }
    }

    // PaintTitle draws the title at (0,0), then one highlight at (62,151/171/192).
    // The translated title and highlight were generated separately and have different
    // lettering. Repaint the complete menu using the same sprites in both states.
    internal static class TitleMenu
    {
        private static FieldInfo task,cursor,background,characters;
        private static MethodInfo draw;
        private static object title;
        private static readonly object[] selected=new object[3],normal=new object[3];
        private static bool enabled;

        internal static void Initialize(Type canvas)
        {
            task=AccessTools.Field(canvas,"MainTask"); cursor=AccessTools.Field(canvas,"CommandCursorPos");
            background=AccessTools.Field(canvas,"Image_Haikei"); characters=AccessTools.Field(canvas,"Image_Kyara");
            Type graphics=AccessTools.TypeByName("Socotra.UI.StGraphics"),image=AccessTools.TypeByName("Socotra.UI.Image");
            draw=AccessTools.Method(graphics,"DrawImage",new[]{image,typeof(int),typeof(int)});
            if(task==null || cursor==null || background==null || characters==null || draw==null)
                throw new MissingMemberException("Title menu rendering bindings");
            enabled=true;
        }

        internal static void Register(string name,object image)
        {
            if(!enabled) return;
            if(name=="/title.jpg")
            {
                // This is our independently owned replacement, never the archive texture.
                var tex=(UnityEngine.Texture2D)image.GetType().GetProperty("Texture").GetValue(image,null);
                if(tex.width!=240 || tex.height!=240) throw new InvalidDataException("Title dimensions");
                var pixels=tex.GetPixels32();
                for(int y=0;y<240;y++) for(int x=0;x<240;x++)
                    if(TitleMenuLayout.ClearBackgroundPixel(x,y)) pixels[(239-y)*240+x]=new UnityEngine.Color32(0,0,0,255);
                tex.SetPixels32(pixels); tex.Apply(false,false);
                title=image; return;
            }
            for(int i=0;i<3;i++)
                if(name=="/title_menu0"+i+".gif" && !Object.ReferenceEquals(selected[i],image))
                {
                    Release(normal[i]); normal[i]=null; selected[i]=null;
                    var texture=(UnityEngine.Texture2D)image.GetType().GetProperty("Texture").GetValue(image,null);
                    if(texture.width!=109 || texture.height!=17) throw new InvalidDataException("Title menu sprite dimensions");
                    var pixels=texture.GetPixels32();
                    for(int p=0;p<pixels.Length;p++)
                    {
                        var c=pixels[p];
                        byte gray=TitleMenuLayout.NormalChannel(c.r,c.g,c.b);
                        pixels[p]=new UnityEngine.Color32(gray,gray,gray,c.a);
                    }
                    object owned=image.GetType().GetMethod("CreateImage",new[]{typeof(int),typeof(int)}).Invoke(null,new object[]{109,17});
                    normal[i]=owned;
                    var target=new UnityEngine.Texture2D(109,17,UnityEngine.TextureFormat.ARGB32,false);
                    image.GetType().GetProperty("Texture").SetValue(owned,target,null);
                    image.GetType().GetProperty("IsDisposable").SetValue(owned,true,null);
                    target.SetPixels32(pixels); target.filterMode=UnityEngine.FilterMode.Point; target.Apply(false,false);
                    selected[i]=image;
                }
        }

        internal static bool Draw(object canvas,object graphics)
        {
            if(!enabled || title==null || !Object.ReferenceEquals(title,background.GetValue(null))) return false;
            int state=(int)task.GetValue(canvas),selection=(int)cursor.GetValue(canvas);
            if(!TitleMenuLayout.CanDraw(state,selection)) return false;
            var sprites=(Array)characters.GetValue(null);
            for(int i=0;i<3;i++)
                if(normal[i]==null || selected[i]==null || !Object.ReferenceEquals(selected[i],sprites.GetValue(i))) return false;
            draw.Invoke(graphics,new object[]{title,0,0});
            for(int i=0;i<3;i++) draw.Invoke(graphics,new object[]{i==selection?selected[i]:normal[i],TitleMenuLayout.Left,TitleMenuLayout.Row(i)});
            return true;
        }

        private static void Release(object value)
        {
            var unity=value as UnityEngine.Object;
            if(value==null || (!Object.ReferenceEquals(unity,null) && unity==null)) return;
            try { value.GetType().GetMethod("Dispose",Type.EmptyTypes).Invoke(value,null); } catch { }
        }
        internal static void Dispose()
        {
            enabled=false; title=null;
            for(int i=0;i<3;i++) { Release(normal[i]); normal[i]=null; selected[i]=null; }
        }
    }
}
