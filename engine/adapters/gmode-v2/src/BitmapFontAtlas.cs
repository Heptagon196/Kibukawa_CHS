using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace Kibu1ZhCN
{
    // Prebuilt monochrome glyphs have identical rasterization and metrics on
    // every machine; no per-character outline scaling or OS font substitution.
    public sealed class BitmapFontAtlas : IDisposable
    {
        private readonly Dictionary<char, CharacterInfo> glyphs = new Dictionary<char, CharacterInfo>();
        private readonly HashSet<char> missing = new HashSet<char>();
        private readonly Dictionary<Shader, Material> materials = new Dictionary<Shader, Material>();
        private readonly Texture2D texture;
        public readonly int PixelSize;
        public readonly bool HasNativeBearings;
        public int GlyphCount { get { return glyphs.Count; } }
        public int MissingGlyphCount { get { return missing.Count; } }
        public BitmapFontAtlas(string folder)
        {
            int width, height;
            using (var reader = new BinaryReader(File.OpenRead(Path.Combine(folder,"dialogue-16.bin"))))
            {
                uint magic = reader.ReadUInt32();
                if (magic != 0x3246424B && magic != 0x3346424B) throw new InvalidDataException("Invalid pixel font signature");
                HasNativeBearings = magic == 0x3346424B;
                PixelSize=reader.ReadInt32(); width=reader.ReadInt32(); height=reader.ReadInt32();
                int count=reader.ReadInt32();
                if ((PixelSize != 12 && PixelSize != 16) || width<PixelSize || height<PixelSize || width>8192 || height>8192 || count<1 || count>65536)
                    throw new InvalidDataException("Invalid pixel font dimensions");
                for (int i=0; i<count; i++)
                {
                    int code=reader.ReadInt32(), x=reader.ReadInt32(), y=reader.ReadInt32(), nativeWidth=reader.ReadInt32();
                    int inkWidth=HasNativeBearings?reader.ReadInt32():nativeWidth;
                    int inkHeight=HasNativeBearings?reader.ReadInt32():PixelSize;
                    int bearingX=HasNativeBearings?reader.ReadInt32():0;
                    int bearingY=HasNativeBearings?reader.ReadInt32():0;
                    if (code<0 || code>65535 || x<0 || y<0 || inkWidth<0 || inkHeight<0 || inkWidth>32 || inkHeight>32 || x+inkWidth>width || y+inkHeight>height || (nativeWidth!=PixelSize/2 && nativeWidth!=PixelSize) || Math.Abs(bearingX)>32 || Math.Abs(bearingY)>32)
                        throw new InvalidDataException("Invalid pixel glyph coordinates");
                    // Crop the UVs to native width, so 8px Latin glyphs are not
                    // squeezed again when drawn into the game's half-width cells.
                    float left=(float)x/width, right=(float)(x+inkWidth)/width;
                    float top=1f-(float)y/height, bottom=1f-(float)(y+inkHeight)/height;
                    glyphs.Add((char)code,new CharacterInfo { advance=nativeWidth, minX=bearingX,maxX=bearingX+inkWidth,minY=bearingY,maxY=bearingY+inkHeight, uvTopLeft=new Vector2(left,top), uvTopRight=new Vector2(right,top),
                        uvBottomLeft=new Vector2(left,bottom), uvBottomRight=new Vector2(right,bottom) });
                }
                if (reader.BaseStream.Position != reader.BaseStream.Length) throw new InvalidDataException("Unexpected pixel font data");
                if (!glyphs.ContainsKey('\u25a1')) throw new InvalidDataException("Unifont replacement glyph is required");
            }
            texture=new Texture2D(2,2,TextureFormat.RGBA32,false);
            if (!ImageConversion.LoadImage(texture,File.ReadAllBytes(Path.Combine(folder,"dialogue-16.png")),true) || texture.width!=width || texture.height!=height)
                throw new InvalidDataException("Pixel font image does not match glyph coordinates");
            texture.name="Kibu8 Chinese " + PixelSize + "px";
            texture.filterMode=FilterMode.Point;
            texture.wrapMode=TextureWrapMode.Clamp;
            texture.anisoLevel=0;
            UnityEngine.Object.DontDestroyOnLoad(texture);
        }
        public bool TryGet(char c, out CharacterInfo info) { return glyphs.TryGetValue(c,out info); }
        public bool TryGetForDisplay(char c, out CharacterInfo info)
        {
            c=LegacyFontRenderer.DisplayCharacter(c);
            if (glyphs.TryGetValue(c, out info)) return true;
            if (c < ' ') return false;
            missing.Add(c);
            // Never silently reintroduce another typeface for dynamic input.
            return glyphs.TryGetValue('\u25a1', out info);
        }
        public Material MaterialFor(Font original)
        {
            Material result;
            Shader shader=original.material.shader;
            if (!materials.TryGetValue(shader,out result))
            {
                result=new Material(original.material);
                result.mainTexture=texture;
                result.name="Kibu1 Chinese Pixel Material";
                UnityEngine.Object.DontDestroyOnLoad(result);
                materials.Add(shader,result);
            }
            return result;
        }
        public void Dispose()
        {
            foreach (Material material in materials.Values) if (material!=null) UnityEngine.Object.Destroy(material);
            if (texture!=null) UnityEngine.Object.Destroy(texture);
            materials.Clear();
        }
    }
}
