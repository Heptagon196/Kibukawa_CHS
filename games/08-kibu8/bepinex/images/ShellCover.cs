using System;
using System.Collections.Generic;
using System.IO;
using HarmonyLib;
using UnityEngine;
using UnityEngine.UI;

namespace Kibu8ZhCN.Images
{
    // TitleView.Init assigns TitleDataModel.gameScreeShot to GameScreenShot.
    // Replace only that UI binding, leaving the model and original assets intact.
    public static class ShellCover
    {
        private const string Owner = "heptagon.kibu8.shellcover";
        private static Texture2D replacement;
        private static Texture rawSource;
        private static Harmony harmony;
        private static float nextSweep;
        private static readonly Dictionary<Sprite, Sprite> sprites = new Dictionary<Sprite, Sprite>();
        private static readonly Dictionary<Image, Sprite> originals = new Dictionary<Image, Sprite>();
        private static readonly Dictionary<Image, Sprite> overrides = new Dictionary<Image, Sprite>();
        private static readonly Dictionary<RawImage, Texture> rawOriginals = new Dictionary<RawImage, Texture>();

        public static void Initialize(string folder)
        {
            if (replacement != null) return;
            try
            {
                byte[] bytes = File.ReadAllBytes(Path.Combine(folder, "titleimage-zh.png"));
                replacement = new Texture2D(2, 2, TextureFormat.RGBA32, false);
                if (!ImageConversion.LoadImage(replacement, bytes, false) || replacement.width != 354 || replacement.height != 354)
                    throw new InvalidDataException("Shell cover must be a valid 354x354 PNG.");
                replacement.name = "kibu8_titleimage_zh";
                replacement.filterMode = FilterMode.Bilinear;
                replacement.wrapMode = TextureWrapMode.Clamp;
                UnityEngine.Object.DontDestroyOnLoad(replacement);
                harmony = new Harmony(Owner);
                harmony.Patch(AccessTools.PropertySetter(typeof(Image), "sprite"),
                    new HarmonyMethod(typeof(ShellCover), "BeforeSprite"));
                harmony.Patch(AccessTools.PropertySetter(typeof(Image), "overrideSprite"),
                    new HarmonyMethod(typeof(ShellCover), "BeforeOverride"));
                harmony.Patch(AccessTools.PropertySetter(typeof(RawImage), "texture"),
                    new HarmonyMethod(typeof(ShellCover), "BeforeTexture"));
                harmony.Patch(AccessTools.Method(typeof(Image), "OnEnable"),
                    postfix: new HarmonyMethod(typeof(ShellCover), "ImageEnabled"));
                nextSweep = 0;
                Update();
            }
            catch { Dispose(); throw; }
        }

        private static bool IsBinding(Component component)
        {
            return replacement != null && component != null && component.gameObject.name == "GameScreenShot";
        }

        private static bool IsOriginal(Texture texture)
        {
            return texture != null && texture != replacement && texture.name == "titleimage"
                && texture.width == 354 && texture.height == 354;
        }

        private static bool IsOriginal(Sprite sprite)
        {
            return sprite != null && sprite.name == "titleimage" && IsOriginal(sprite.texture)
                && sprite.rect == new Rect(0, 0, 354, 354);
        }

        private static Sprite Translate(Sprite original)
        {
            Sprite translated;
            if (sprites.TryGetValue(original, out translated)) return translated;
            Rect rect = original.rect;
            Vector2 pivot = new Vector2(original.pivot.x / rect.width, original.pivot.y / rect.height);
            translated = Sprite.Create(replacement, rect, pivot, original.pixelsPerUnit, 1,
                SpriteMeshType.FullRect, original.border);
            translated.name = "kibu8_titleimage_zh_sprite";
            UnityEngine.Object.DontDestroyOnLoad(translated);
            sprites.Add(original, translated);
            return translated;
        }

        private static void BeforeSprite(Image __instance, ref Sprite __0)
        {
            if (!IsBinding(__instance) || !IsOriginal(__0)) return;
            originals[__instance] = __0;
            __0 = Translate(__0);
        }

        private static void BeforeOverride(Image __instance, ref Sprite __0)
        {
            if (!IsBinding(__instance) || !IsOriginal(__0)) return;
            overrides[__instance] = __0;
            __0 = Translate(__0);
        }

        private static void BeforeTexture(RawImage __instance, ref Texture __0)
        {
            if (!IsBinding(__instance) || !IsOriginal(__0)) return;
            rawOriginals[__instance] = __0;
            rawSource = __0;
            __0 = replacement;
        }

        private static void ImageEnabled(Image __instance) { Refresh(__instance); }

        private static void Refresh(Image image)
        {
            if (!IsBinding(image)) return;
            // overrideSprite getter returns sprite when no override is present.
            // Capture a distinct override first so the base setter cannot hide it.
            Sprite originalOverride = image.overrideSprite;
            Sprite originalSprite = image.sprite;
            // Instantiation can clone an already translated inactive prefab.
            // Record inherited replacement references for disposal as well.
            foreach (var pair in sprites)
            {
                if (originalSprite == pair.Value) originals[image] = pair.Key;
                if (originalOverride != originalSprite && originalOverride == pair.Value)
                    overrides[image] = pair.Key;
            }
            if (originalOverride != originalSprite && IsOriginal(originalOverride))
                image.overrideSprite = originalOverride;
            if (IsOriginal(originalSprite)) image.sprite = originalSprite;
        }

        private static void Refresh(RawImage image)
        {
            if (!IsBinding(image)) return;
            if (image.texture == replacement && rawSource != null) rawOriginals[image] = rawSource;
            else if (IsOriginal(image.texture)) image.texture = image.texture;
        }

        public static void Update()
        {
            if (replacement == null || Time.realtimeSinceStartup < nextSweep) return;
            nextSweep = Time.realtimeSinceStartup + 2f;
            foreach (Image image in Resources.FindObjectsOfTypeAll<Image>()) Refresh(image);
            foreach (RawImage image in Resources.FindObjectsOfTypeAll<RawImage>()) Refresh(image);
            Prune(originals);
            Prune(overrides);
            Prune(rawOriginals);
        }

        private static void Prune<T, TValue>(Dictionary<T, TValue> table) where T : UnityEngine.Object
        {
            var dead = new List<T>();
            foreach (T key in table.Keys) if (key == null) dead.Add(key);
            foreach (T key in dead) table.Remove(key);
        }

        private static bool IsReplacement(Sprite sprite)
        {
            return sprite != null && sprite.texture == replacement;
        }

        public static void Dispose()
        {
            // Include newly cloned inactive bindings before destroying owned data.
            if (replacement != null && harmony != null)
            {
                foreach (Image image in Resources.FindObjectsOfTypeAll<Image>()) Refresh(image);
                foreach (RawImage image in Resources.FindObjectsOfTypeAll<RawImage>()) Refresh(image);
            }
            if (harmony != null) { harmony.UnpatchSelf(); harmony = null; }
            foreach (var item in overrides)
                if (item.Key != null && IsReplacement(item.Key.overrideSprite)) item.Key.overrideSprite = item.Value;
            foreach (var item in originals)
                if (item.Key != null && IsReplacement(item.Key.sprite)) item.Key.sprite = item.Value;
            // An explicit override identical to the base sprite is indistinguishable
            // via the getter until the base has been restored (notably on clones).
            foreach (Image image in Resources.FindObjectsOfTypeAll<Image>())
                if (IsBinding(image) && IsReplacement(image.overrideSprite))
                    foreach (var pair in sprites)
                        if (image.overrideSprite == pair.Value) { image.overrideSprite = pair.Key; break; }
            foreach (var item in rawOriginals)
                if (item.Key != null && item.Key.texture == replacement) item.Key.texture = item.Value;
            overrides.Clear();
            originals.Clear();
            rawOriginals.Clear();
            foreach (Sprite sprite in sprites.Values) if (sprite != null) UnityEngine.Object.Destroy(sprite);
            sprites.Clear();
            if (replacement != null) UnityEngine.Object.Destroy(replacement);
            replacement = null;
            rawSource = null;
        }
    }
}
