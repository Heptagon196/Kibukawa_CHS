using System;
using System.IO;
using System.Reflection;
using HarmonyLib;
using Kibukawa.ImageReplacements;

namespace Kibu9ZhCN.Images
{
    internal static class TitleBackground
    {
        private static FieldInfo background, name;
        private static TextureReplacement replacement;
        private static object source, current;

        internal static void Initialize(string folder, Type canvas, Harmony harmony, Action<string> warning)
        {
            background = AccessTools.Field(canvas, "Image_Haikei");
            name = AccessTools.Field(canvas, "HaikeiFileNameBackup");
            MethodInfo title = AccessTools.Method(canvas, "Game_title", Type.EmptyTypes);
            if (background == null || !background.IsStatic || name == null || name.IsStatic || title == null)
                throw new MissingMemberException("Ninth-game title background bindings");
            replacement = new TextureReplacement();
            replacement.Initialize(Path.Combine(folder, "title-background.rgba"), warning, 240, 240, true);
            harmony.Patch(title, postfix: new HarmonyMethod(typeof(TitleBackground), nameof(AfterTitle)));
        }

        private static void AfterTitle(object __instance)
        {
            if (replacement == null || (string)name.GetValue(__instance) != "title") return;
            object original = background.GetValue(null);
            if (original == null || Object.ReferenceEquals(original, current)) return;
            object translated = replacement.Replace(original);
            if (Object.ReferenceEquals(original, translated)) return;
            source = original;
            current = translated;
            background.SetValue(null, translated);
        }

        internal static void Dispose()
        {
            if (background != null && Object.ReferenceEquals(background.GetValue(null), current))
                background.SetValue(null, source);
            if (replacement != null) replacement.Reset();
            replacement = null;
            background = null;
            name = null;
            source = null;
            current = null;
        }
    }
}
