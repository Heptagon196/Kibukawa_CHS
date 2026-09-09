using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.UI;

namespace Kibu1ZhCN
{
    // Replacement media is loaded only from the plugin's own directory.
    // Original resource objects/files and legacy image ownership are untouched.
    public static class RuntimeImages
    {
        public const int HelpPageCount = 5;
        private static readonly Sprite[] help = new Sprite[HelpPageCount];
        private static readonly List<Texture2D> textures = new List<Texture2D>();
        private static readonly Dictionary<Image, Sprite> originals = new Dictionary<Image, Sprite>();
        public static void Initialize(string root)
        {
            for (int i = 0; i < HelpPageCount; i++)
            {
                Texture2D texture = Load(Path.Combine(root, "help-" + i.ToString("00") + ".png"), 930, 632);
                help[i] = Sprite.Create(texture, new Rect(0, 0, texture.width, texture.height), new Vector2(.5f, .5f), 100f);
                help[i].name = "kibu6.zhcn.help." + i;
                UnityEngine.Object.DontDestroyOnLoad(help[i]);
            }
        }

        private static Texture2D Load(string path, int width, int height)
        {
            if (!File.Exists(path)) throw new FileNotFoundException("Missing Chinese image", path);
            Texture2D texture = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            textures.Add(texture);
            if (!ImageConversion.LoadImage(texture, File.ReadAllBytes(path), false))
                throw new InvalidDataException("Invalid PNG: " + path);
            if (texture.width != width || texture.height != height)
                throw new InvalidDataException("Unexpected Chinese image dimensions: " + path);
            texture.filterMode = FilterMode.Point;
            texture.wrapMode = TextureWrapMode.Clamp;
            texture.name = "kibu6.zhcn." + Path.GetFileNameWithoutExtension(path);
            UnityEngine.Object.DontDestroyOnLoad(texture);
            return texture;
        }

        public static void ShowHelp(Image image, int page)
        {
            if (image == null || page < 1 || page > HelpPageCount) return;
            // ChangePage has just assigned the original page sprite. Remember
            // the latest page so shutdown restores the page actually displayed.
            if (image.sprite != help[page - 1]) originals[image] = image.sprite;
            image.sprite = help[page - 1];
        }

        public static void Dispose()
        {
            foreach (KeyValuePair<Image, Sprite> pair in originals)
                if (pair.Key != null) pair.Key.sprite = pair.Value;
            originals.Clear();
            foreach (Sprite sprite in help) if (sprite != null) UnityEngine.Object.Destroy(sprite);
            Array.Clear(help, 0, help.Length);
            foreach (Texture2D texture in textures) if (texture != null) UnityEngine.Object.Destroy(texture);
            textures.Clear();
        }
    }
}
