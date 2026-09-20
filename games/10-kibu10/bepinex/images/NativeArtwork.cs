using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using HarmonyLib;
using UnityEngine;

namespace Kibu10ZhCN.Images
{
    // AI-edited artwork is retained at its original output resolution in the package.
    // The renderer samples it into the native game's fixed viewport, without touching
    // either original resources or the stored artwork files.
    internal static class NativeArtwork
    {
        private sealed class Route
        {
            internal Texture2D Texture;
            internal readonly Dictionary<object,object> Instances=new Dictionary<object,object>();
        }
        private static readonly Dictionary<string,Route> routes=new Dictionary<string,Route>();
        internal static Texture2D LoadNative(string path,int width,int height)
        {
            var full=new Texture2D(2,2,TextureFormat.RGBA32,false);
            try
            {
                if(!ImageConversion.LoadImage(full,File.ReadAllBytes(path),false) || full.width>4096 || full.height>4096 || full.width<width || full.height<height)
                    throw new InvalidDataException("Artwork dimensions: "+path);
                if(Math.Abs((double)full.width/full.height-(double)width/height)>.02)
                    throw new InvalidDataException("Artwork aspect ratio: "+path);
                var pixels=new Color[width*height];
                for(int y=0;y<height;y++)for(int x=0;x<width;x++)pixels[y*width+x]=full.GetPixelBilinear((x+.5f)/width,(y+.5f)/height);
                var result=new Texture2D(width,height,TextureFormat.RGBA32,false);
                result.SetPixels(pixels);result.Apply(false,false);result.filterMode=FilterMode.Point;result.wrapMode=TextureWrapMode.Clamp;
                return result;
            }
            finally { UnityEngine.Object.Destroy(full); }
        }
        internal static void Initialize(string folder,Type canvas,Harmony harmony)
        {
            Add("/title1.gif","title1-zh.png",240,240,folder);
            Add("/title2.gif","title2-zh.png",240,240,folder);
            Add("title.gif","title-scratch-zh.png",240,240,folder);
            foreach(string method in new[]{"Image_createImage","LoadGraphic"})
                harmony.Patch(AccessTools.Method(canvas,method,new[]{typeof(string)}),postfix:new HarmonyMethod(typeof(NativeArtwork),nameof(AfterLoad)));
        }
        private static void Add(string name,string file,int width,int height,string folder)
        {
            routes.Add(name,new Route{Texture=LoadNative(Path.Combine(folder,"artwork",file),width,height)});
        }
        private static void AfterLoad(MethodBase __originalMethod,string __0,ref object __result)
        {
            try { Replace(__originalMethod,__0,ref __result); }
            catch(Exception error) { Debug.LogWarning("Kibu10 artwork kept original: "+error.Message); }
        }
        private static void Replace(MethodBase __originalMethod,string __0,ref object __result)
        {
            if(__result==null || String.IsNullOrEmpty(__0))return;
            if(__originalMethod.Name=="LoadGraphic" && __0.IndexOf('.')<0)__0+=".gif";
            Route route;if(!routes.TryGetValue(__0,out route))return;
            object translated;
            if(route.Instances.TryGetValue(__result,out translated))
            {
                var unity=translated as UnityEngine.Object;
                if(ReferenceEquals(unity,null)||unity!=null){__result=translated;return;}
                route.Instances.Remove(__result);
            }
            Type t=__result.GetType();var property=t.GetProperty("Texture");var original=property.GetValue(__result,null) as Texture2D;
            if(original==null || original.width!=route.Texture.width || original.height!=route.Texture.height)return;
            translated=t.GetMethod("CreateImage",new[]{typeof(int),typeof(int)}).Invoke(null,new object[]{original.width,original.height});
            var texture=new Texture2D(original.width,original.height,TextureFormat.RGBA32,false);
            texture.SetPixels32(route.Texture.GetPixels32());texture.Apply(false,false);texture.filterMode=FilterMode.Point;
            property.SetValue(translated,texture,null);t.GetProperty("IsDisposable").SetValue(translated,true,null);
            route.Instances.Add(__result,translated);__result=translated;
        }
        internal static void Dispose()
        {
            foreach(var route in routes.Values)
            {
                foreach(var item in route.Instances.Values)
                {
                    var unity=item as UnityEngine.Object;
                    if(!ReferenceEquals(unity,null)&&unity==null)continue;
                    try{item.GetType().GetMethod("Dispose",Type.EmptyTypes).Invoke(item,null);}catch{}
                }
                UnityEngine.Object.Destroy(route.Texture);
            }
            routes.Clear();
        }
    }
}
