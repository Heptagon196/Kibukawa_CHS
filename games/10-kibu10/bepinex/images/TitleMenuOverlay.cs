using System;
using System.IO;
using System.Reflection;
using HarmonyLib;
using UnityEngine;

namespace Kibu10ZhCN.Images
{
    // Each state contains the complete master menu panel, including red branches.
    // One draw also clears native highlights left by the previous selection.
    internal static class TitleMenuOverlay
    {
        private static readonly object[,] images=new object[3,5];
        private static readonly int[] cycle={0,1,2,3,4,3,2,1};
        private static FieldInfo cursor,counter,drawFlag,task,background;
        private static object titleBackground;
        private static MethodInfo draw;
        private static bool active;
        private static string imageFolder;
        private static Type imageType;
        private static bool loaded;
        internal static void Initialize(string folder,Type canvas,Harmony harmony)
        {
            imageFolder=folder;
            imageType=AccessTools.TypeByName("Socotra.UI.Image");
            Type image=imageType;
            cursor=AccessTools.Field(canvas,"CommandCursorPos");counter=AccessTools.Field(canvas,"t_counter");drawFlag=AccessTools.Field(canvas,"draw_flag");task=AccessTools.Field(canvas,"MainTask");
            background=AccessTools.Field(canvas,"Image_Haikei");
            draw=AccessTools.Method(AccessTools.TypeByName("Socotra.UI.StGraphics"),"DrawImage",new[]{image,typeof(int),typeof(int)});
            if(cursor==null || counter==null || drawFlag==null || task==null || draw==null)throw new MissingMemberException("Title menu bindings");
            harmony.Patch(AccessTools.Method(canvas,"PaintTitle"),postfix:new HarmonyMethod(typeof(TitleMenuOverlay),nameof(AfterPaint)));
            active=true;
        }
        // Socotra's CreateImage delegates to StScreenManager.Instance. BepInEx
        // Awake runs before that singleton exists; the first title paint is safe.
        private static bool Alive(object value)
        {
            if(value==null)return false;
            var unity=value as UnityEngine.Object;
            return System.Object.ReferenceEquals(unity,null) || unity!=null;
        }
        private static void EnsureImages(object canvas)
        {
            object current=background==null?null:background.GetValue(canvas);
            bool valid=loaded && System.Object.ReferenceEquals(current,titleBackground);
            if(valid)foreach(var sprite in images)
                if(!Alive(sprite) || !Alive(imageType.GetProperty("Texture").GetValue(sprite,null))) { valid=false;break; }
            if(valid)return;
            ReleaseImages();
            titleBackground=current;
            Type image=imageType;
            var create=image.GetMethod("CreateImage",new[]{typeof(int),typeof(int)});
            for(int i=0;i<3;i++)for(int j=0;j<5;j++)
            {
                var texture=new Texture2D(2,2,TextureFormat.RGBA32,false);
                if(!ImageConversion.LoadImage(texture,File.ReadAllBytes(Path.Combine(imageFolder,"images","title-panel-"+i+"-"+j+".png")),false))throw new InvalidDataException("Menu panel PNG");
                texture.filterMode=FilterMode.Point;
                object sprite=create.Invoke(null,new object[]{texture.width,texture.height});
                image.GetProperty("Texture").SetValue(sprite,texture,null);image.GetProperty("IsDisposable").SetValue(sprite,true,null);images[i,j]=sprite;
            }
            loaded=true;
        }
        private static void AfterPaint(object __instance,object __0)
        {
            if(!active)return;
            try { Paint(__instance,__0); }
            catch(Exception error) { active=false; Debug.LogWarning("Kibu10 title overlay disabled: "+error.Message); }
        }
        private static void Paint(object __instance,object __0)
        {
            if((int)task.GetValue(__instance)==1 || !(bool)drawFlag.GetValue(__instance))return;
            int selected=(int)cursor.GetValue(__instance),phase=(int)counter.GetValue(__instance);
            if(selected<0 || selected>2 || phase<0 || phase>7)return;
            EnsureImages(__instance);
            draw.Invoke(__0,new object[]{images[selected,cycle[phase]],27,34});
        }
        internal static void Dispose()
        {
            active=false;
            ReleaseImages();
            titleBackground=null;
        }
        private static void ReleaseImages()
        {
            loaded=false;
            foreach(var image in images)if(Alive(image))try{image.GetType().GetMethod("Dispose",Type.EmptyTypes).Invoke(image,null);}catch{}
            Array.Clear(images,0,images.Length);
        }
    }
}
