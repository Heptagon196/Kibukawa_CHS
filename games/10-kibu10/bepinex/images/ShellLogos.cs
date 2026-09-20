using System;
using System.Collections.Generic;
using System.IO;
using HarmonyLib;
using UnityEngine;
using UnityEngine.UI;

namespace Kibu10ZhCN.Images
{
    // Exact English pixels supplied with this game, independently loaded so the
    // result does not depend on Unity loading the unused English title model.
    internal static class ShellLogos
    {
        private static readonly Dictionary<Image,Sprite> originals=new Dictionary<Image,Sprite>();
        private static readonly Dictionary<Sprite,Sprite> replacements=new Dictionary<Sprite,Sprite>();
        private static readonly Dictionary<string,Texture2D> textures=new Dictionary<string,Texture2D>();
        private static float next;
        private static bool active;
        internal static void Initialize(string folder,Harmony harmony)
        {
            foreach(string name in new[]{"title_logo_archives_00","title_logo_archives_plus_00"})
            {
                var texture=new Texture2D(2,2,TextureFormat.RGBA32,false);
                try
                {
                    if(!ImageConversion.LoadImage(texture,File.ReadAllBytes(Path.Combine(folder,"images",name+"_en.png")),false)
                        || texture.height!=44 || texture.width!=(name.Contains("plus")?378:352))
                        throw new InvalidDataException("Unexpected English logo: "+name);
                    texture.filterMode=FilterMode.Bilinear;texture.wrapMode=TextureWrapMode.Clamp;
                    UnityEngine.Object.DontDestroyOnLoad(texture);textures.Add(name,texture);
                }
                catch { UnityEngine.Object.Destroy(texture);throw; }
            }
            harmony.Patch(AccessTools.PropertySetter(typeof(Image),"sprite"),new HarmonyMethod(typeof(ShellLogos),nameof(BeforeSprite)));
            next=0;active=true;
        }
        private static void BeforeSprite(Image __instance,ref Sprite __0)
        {
            if(!active || __0==null)return;
            Texture2D texture;if(!textures.TryGetValue(__0.name,out texture))return;
            Sprite replacement;
            if(!replacements.TryGetValue(__0,out replacement) || replacement==null)
            {
                var rect=__0.rect;
                replacement=Sprite.Create(texture,new Rect(0,0,texture.width,texture.height),
                    new Vector2(__0.pivot.x/rect.width,__0.pivot.y/rect.height),__0.pixelsPerUnit);
                replacement.name=__0.name+"_en";
                UnityEngine.Object.DontDestroyOnLoad(replacement);replacements[__0]=replacement;
            }
            originals[__instance]=__0;__0=replacement;
        }
        internal static void Update()
        {
            if(!active || Time.realtimeSinceStartup<next)return;next=Time.realtimeSinceStartup+2;
            foreach(var image in Resources.FindObjectsOfTypeAll<Image>())
            {
                var sprite=image.sprite;BeforeSprite(image,ref sprite);if(sprite!=image.sprite)image.sprite=sprite;
            }
            var dead=new List<Image>();foreach(var image in originals.Keys)if(image==null)dead.Add(image);
            foreach(var image in dead)originals.Remove(image);
        }
        internal static void Dispose()
        {
            active=false;
            foreach(var pair in originals)if(pair.Key!=null && replacements.ContainsValue(pair.Key.sprite))pair.Key.sprite=pair.Value;
            originals.Clear();
            foreach(var sprite in replacements.Values)if(sprite!=null)UnityEngine.Object.Destroy(sprite);
            replacements.Clear();
            foreach(var texture in textures.Values)if(texture!=null)UnityEngine.Object.Destroy(texture);
            textures.Clear();
        }
    }
}
