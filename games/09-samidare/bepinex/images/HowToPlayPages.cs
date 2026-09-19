using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using HarmonyLib;
using UnityEngine;
using UnityEngine.UI;

namespace Kibu9ZhCN.Images
{
    // HowToPlayDialog owns navigation and assigns one native Sprite per page.
    // Replace only the displayed sprite and restore the latest native page on shutdown.
    internal static class HowToPlayPages
    {
        private const int PageCount = 4;
        private static readonly Sprite[] pages = new Sprite[PageCount];
        private static readonly List<Texture2D> textures = new List<Texture2D>();
        private static readonly Dictionary<Image, Sprite> originals = new Dictionary<Image, Sprite>();
        private static FieldInfo guideImage, nowPage;
        private static bool active;

        internal static void Initialize(string folder, Harmony harmony)
        {
            if (active) return;
            for (int index = 0; index < PageCount; index++)
            {
                Texture2D texture = Load(Path.Combine(folder, "images", "help-" + index.ToString("00") + ".png"));
                Sprite sprite = Sprite.Create(texture, new Rect(0, 0, 930, 632), new Vector2(.5f, .5f), 100f);
                sprite.name = "kibu9.zhcn.help." + index;
                UnityEngine.Object.DontDestroyOnLoad(sprite);
                pages[index] = sprite;
            }
            Type type = AccessTools.TypeByName("HowToPlayDialog");
            guideImage = type == null ? null : AccessTools.Field(type, "guideImage");
            nowPage = type == null ? null : AccessTools.Field(type, "nowPage");
            MethodInfo changePage = type == null ? null : AccessTools.Method(type, "ChangePage", new[] { typeof(int) });
            if (guideImage == null || guideImage.FieldType != typeof(Image)
                || nowPage == null || nowPage.FieldType != typeof(int) || changePage == null)
                throw new MissingMemberException("HowToPlayDialog guideImage/nowPage/ChangePage");
            harmony.Patch(changePage, postfix: new HarmonyMethod(typeof(HowToPlayPages), nameof(AfterChangePage)));
            active = true;
        }

        private static Texture2D Load(string path)
        {
            if (!File.Exists(path)) throw new FileNotFoundException("Missing Chinese help page", path);
            Texture2D texture = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            if (!ImageConversion.LoadImage(texture, File.ReadAllBytes(path), false)
                || texture.width != 930 || texture.height != 632)
            {
                UnityEngine.Object.Destroy(texture);
                throw new InvalidDataException("Chinese help page must be a 930x632 PNG: " + path);
            }
            texture.filterMode = FilterMode.Bilinear;
            texture.wrapMode = TextureWrapMode.Clamp;
            texture.name = "kibu9.zhcn." + Path.GetFileNameWithoutExtension(path);
            UnityEngine.Object.DontDestroyOnLoad(texture);
            textures.Add(texture);
            return texture;
        }

        private static void AfterChangePage(object __instance)
        {
            if (!active || __instance == null) return;
            Image image = guideImage.GetValue(__instance) as Image;
            int page = Convert.ToInt32(nowPage.GetValue(__instance));
            if (image == null || page < 1 || page > PageCount) return;
            if (image.sprite != pages[page - 1]) originals[image] = image.sprite;
            image.sprite = pages[page - 1];
        }

        internal static void Dispose()
        {
            active = false;
            foreach (KeyValuePair<Image, Sprite> item in originals)
                if (item.Key != null && Array.IndexOf(pages, item.Key.sprite) >= 0) item.Key.sprite = item.Value;
            originals.Clear();
            foreach (Sprite sprite in pages) if (sprite != null) UnityEngine.Object.Destroy(sprite);
            Array.Clear(pages, 0, pages.Length);
            foreach (Texture2D texture in textures) if (texture != null) UnityEngine.Object.Destroy(texture);
            textures.Clear();
            guideImage = null;
            nowPage = null;
        }
    }
}
