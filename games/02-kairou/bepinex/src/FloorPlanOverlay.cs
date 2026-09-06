using System;
using System.IO;
using System.Reflection;
using UnityEngine;

namespace Kibu1ZhCN
{
    // The bundled complete image is top-down RGBA; Unity arrays are bottom-up.
    // Only a separately owned Socotra image is edited, never the archive image.
    public static class FloorPlanOverlay
    {
        private const int Width = 220, Height = 128;
        private static byte[] overlay;
        private static object source, replacement;
        private static Action<string> warning;
        private static bool failed;

        public static void Initialize(string folder, Action<string> warningLogger)
        {
            Reset();
            warning = warningLogger;
            try
            {
                using (var reader = new BinaryReader(File.OpenRead(Path.Combine(folder, "floorplan.bin"))))
                {
                    if (reader.ReadUInt32() != 0x50414D4B || reader.ReadInt32() != Width || reader.ReadInt32() != Height)
                        throw new InvalidDataException("Invalid KMAP floor plan header");
                    overlay = reader.ReadBytes(Width * Height * 4);
                    if (overlay.Length != Width * Height * 4 || reader.BaseStream.Position != reader.BaseStream.Length)
                        throw new InvalidDataException("Invalid KMAP floor plan payload length");
                    for (int i = 3; i < overlay.Length; i += 4)
                        if (overlay[i] != 255) throw new InvalidDataException("KMAP requires a complete opaque image");
                }
            }
            catch (Exception error) { Fail(error); }
        }

        public static object Replace(int index, object original)
        {
            if (index != 10 || original == null || failed || overlay == null) return original;
            try
            {
                if (System.Object.ReferenceEquals(original, source) && Alive(replacement)) return replacement;
                Type type = original.GetType();
                PropertyInfo textureProperty = type.GetProperty("Texture");
                PropertyInfo disposableProperty = type.GetProperty("IsDisposable");
                if (textureProperty == null || !textureProperty.CanWrite || disposableProperty == null || !disposableProperty.CanWrite)
                    throw new MissingMemberException(type.FullName, "Writable Texture / IsDisposable");
                Texture2D texture = textureProperty == null ? null : textureProperty.GetValue(original, null) as Texture2D;
                if (texture == null || texture.width != Width || texture.height != Height) return original;
                // UniGif makes the original texture unreadable after uploading it.
                // The build includes all pixels, so no original GPU texture readback is needed.
                Color32[] pixels = Compose(new Color32[Width * Height], overlay, Width, Height);
                MethodInfo create = type.GetMethod("CreateImage", BindingFlags.Public | BindingFlags.Static,
                    null, new[] { typeof(int), typeof(int) }, null);
                if (create == null) throw new MissingMethodException(type.FullName, "CreateImage");
                Release();
                replacement = create.Invoke(null, new object[] { Width, Height });
                // CreateImage's default Texture2D(w,h) allocates a mip chain.
                // Apply(false,...) leaves those smaller levels unwritten (gray map).
                // Match UniGif's explicit format and no-mipmap constructor instead.
                // Texture setter destroys only the independently owned factory texture.
                Texture2D target = new Texture2D(Width, Height, TextureFormat.ARGB32, false);
                textureProperty.SetValue(replacement, target, null);
                // The game's setter clears ownership when replacing its old texture.
                disposableProperty.SetValue(replacement, true, null);
                target.SetPixels32(pixels);
                target.filterMode = FilterMode.Point;
                target.Apply(false, false);
                source = original;
                return replacement;
            }
            catch (Exception error)
            {
                Release();
                Fail(error);
                return original;
            }
        }

        private static bool Alive(object value)
        {
            if (value == null) return false;
            var unity = value as UnityEngine.Object;
            return System.Object.ReferenceEquals(unity, null) || unity != null;
        }

        public static Color32[] Compose(Color32[] bottomUp, byte[] topDownRgba, int width, int height)
        {
            if (width <= 0 || height <= 0 || bottomUp == null || topDownRgba == null ||
                bottomUp.Length != checked(width * height) || topDownRgba.Length != checked(width * height * 4))
                throw new ArgumentException("Floor plan dimensions do not match pixel data");
            Color32[] output = (Color32[])bottomUp.Clone();
            for (int y = 0; y < height; y++)
                for (int x = 0; x < width; x++)
                {
                    int i = (y * width + x) * 4, dest = (height - 1 - y) * width + x;
                    int alpha = topDownRgba[i + 3];
                    if (alpha == 0) continue;
                    Color32 back = output[dest];
                    int backAlpha = back.a * (255 - alpha);
                    int combined = alpha * 255 + backAlpha;
                    output[dest] = new Color32(
                        (byte)((topDownRgba[i] * alpha * 255 + back.r * backAlpha + combined / 2) / combined),
                        (byte)((topDownRgba[i + 1] * alpha * 255 + back.g * backAlpha + combined / 2) / combined),
                        (byte)((topDownRgba[i + 2] * alpha * 255 + back.b * backAlpha + combined / 2) / combined),
                        (byte)((combined + 127) / 255));
                }
            return output;
        }

        private static void Fail(Exception error)
        {
            failed = true;
            overlay = null;
            // Logging must not turn an optional image replacement into a game error.
            try { if (warning != null) warning("Chinese floor plan unavailable; keeping original: " + error.Message); }
            catch { }
        }

        private static void Release()
        {
            object owned = replacement;
            replacement = null;
            source = null;
            if (!Alive(owned)) return;
            try
            {
                // Socotra.Image.Dispose releases its disposable factory texture and GameObject.
                MethodInfo dispose = owned.GetType().GetMethod("Dispose", Type.EmptyTypes);
                if (dispose != null) dispose.Invoke(owned, null);
            }
            catch { }
        }

        public static void Reset()
        {
            Release();
            overlay = null;
            warning = null;
            failed = false;
        }
    }
}

