using System;
using System.Collections.Generic;
using System.Reflection;
using UnityEngine;

namespace Kibu1ZhCN
{
    // Draw in the game's existing character cells, without changing StFont or its metrics.
    public static class LegacyFontRenderer
    {
        private const BindingFlags Members = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;
        private sealed class Access
        {
            public FieldInfo CurrentFont, RenderTexture, Color, Font;
            public PropertyInfo Size;
            public MethodInfo Begin, End;
        }
        private static readonly Dictionary<Type, Access> access = new Dictionary<Type, Access>();

        private static FieldInfo Field(Type type, string name)
        {
            for (Type current = type; current != null; current = current.BaseType)
            {
                FieldInfo field = current.GetField(name, Members);
                if (field != null) return field;
            }
            throw new MissingFieldException(type.FullName, name);
        }
        private static MethodInfo Method(Type type, string name)
        {
            for (Type current = type; current != null; current = current.BaseType)
            {
                MethodInfo method = current.GetMethod(name, Members, null, Type.EmptyTypes, null);
                if (method != null) return method;
            }
            throw new MissingMethodException(type.FullName, name);
        }
        private static Access GetAccess(Type type)
        {
            Access result;
            if (access.TryGetValue(type, out result)) return result;
            FieldInfo wrapper = Field(type, "currentFont");
            result = new Access
            {
                CurrentFont = wrapper,
                RenderTexture = Field(type, "renderTexture"),
                Color = Field(type, "currentColor"),
                Font = Field(wrapper.FieldType, "font"),
                Size = wrapper.FieldType.GetProperty("Size", BindingFlags.Instance | BindingFlags.Public),
                Begin = Method(type, "RenderStart"),
                End = Method(type, "RenderEnd")
            };
            if (result.Size == null) throw new MissingMemberException(wrapper.FieldType.FullName, "Size");
            access.Add(type, result);
            return result;
        }

        public static float CellWidth(char c, float size)
        {
            return ((c >= ' ' && c <= '~') || (c >= '\uff66' && c <= '\uff9f')) ? size / 2f : size;
        }

        private sealed class Geometry
        {
            public readonly List<Vector3> Vertices = new List<Vector3>();
            public readonly List<Vector2> UV = new List<Vector2>();
            public readonly List<int> Triangles = new List<int>();
            public void Add(CharacterInfo info, float left, float bottom, float right, float top)
            {
                int start = Vertices.Count;
                Vertices.Add(new Vector3(left, bottom, 0));
                Vertices.Add(new Vector3(right, bottom, 0));
                Vertices.Add(new Vector3(right, top, 0));
                Vertices.Add(new Vector3(left, top, 0));
                UV.Add(info.uvBottomLeft); UV.Add(info.uvBottomRight);
                UV.Add(info.uvTopRight); UV.Add(info.uvTopLeft);
                Triangles.Add(start); Triangles.Add(start + 1); Triangles.Add(start + 2);
                Triangles.Add(start); Triangles.Add(start + 2); Triangles.Add(start + 3);
            }
            public Mesh Create()
            {
                if (Vertices.Count == 0) return null;
                Mesh mesh = new Mesh();
                mesh.vertices = Vertices.ToArray();
                mesh.uv = UV.ToArray();
                mesh.triangles = Triangles.ToArray();
                return mesh;
            }
        }

        // True means the unchanged original DrawCharImpl should handle this draw.
        public static bool Draw(object graphics, char[] text, int x, int y, Font fallback, BitmapFontAtlas bitmap = null, float horizontalScale = 1f)
        {
            if (graphics == null || text == null || text.Length == 0) return true;
            if (float.IsNaN(horizontalScale) || float.IsInfinity(horizontalScale) || horizontalScale <= 0)
                throw new ArgumentOutOfRangeException("horizontalScale");
            Access a = GetAccess(graphics.GetType());
            object wrapper = a.CurrentFont.GetValue(graphics);
            if (wrapper == null) return true;
            Font original = (Font)a.Font.GetValue(wrapper);
            RenderTexture target = (RenderTexture)a.RenderTexture.GetValue(graphics);
            if (original == null || target == null) return true;
            float size = Convert.ToSingle(a.Size.GetValue(wrapper, null));
            int requestedSize = (int)size;
            if (requestedSize <= 0) return true;

            // Request the complete atlas contents before retaining any CharacterInfo UVs.
            string value = new string(text);
            original.RequestCharactersInTexture(value + "国田口日", requestedSize);
            bool needsFallback = false, needsBitmap = false;
            CharacterInfo info;
            foreach (char c in text)
            {
                if (bitmap != null && bitmap.TryGetForDisplay(c,out info)) { needsBitmap=true; continue; }
                if (c >= ' ' && !original.GetCharacterInfo(c, out info, requestedSize))
                {
                    needsFallback = true;
                }
            }
            if (!needsFallback && !needsBitmap && horizontalScale == 1f) return true;
            if (fallback != null && needsFallback) fallback.RequestCharactersInTexture(value, requestedSize);

            // The original renderer's baseline is retained. A representative original CJK
            // glyph supplies the fallback's ink box; the font's nominal ascent may use
            // a different imported size from StFont.Size and must not replace this baseline.
            float referenceBottom = 0f, referenceTop = size;
            bool foundReference = false;
            foreach (char reference in "国田口日")
            {
                if (original.GetCharacterInfo(reference, out info, requestedSize) && info.maxY > info.minY)
                {
                    referenceBottom = info.minY;
                    referenceTop = info.maxY;
                    foundReference = true;
                    break;
                }
            }
            if (!foundReference)
            {
                referenceBottom = -(original.lineHeight - original.ascent);
                referenceTop = referenceBottom + size;
            }

            Geometry originalGeometry = new Geometry(), fallbackGeometry = new Geometry(), bitmapGeometry = new Geometry();
            float pen = 0f;
            foreach (char raw in text)
            {
                // Null marks unused cells in the game's fixed buffers; it is not a glyph.
                if (raw == '\0') continue;
                char c = raw < ' ' ? ' ' : raw;
                float cell = CellWidth(c, size);
                if (bitmap != null && bitmap.TryGetForDisplay(c,out info))
                {
                    // Use native 8x16/16x16 dimensions, not the packed tile width.
                    // Keep the game's half/full-width cursor advances unchanged.
                    float glyphWidth = info.advance * size / bitmap.PixelSize;
                    float left=Mathf.Round(pen + (cell-glyphWidth)/2f), top=Mathf.Round(referenceTop);
                    bitmapGeometry.Add(info,left,top-size,left+glyphWidth,top);
                }
                else if (original.GetCharacterInfo(c, out info, requestedSize))
                {
                    if (info.maxX > info.minX && info.maxY > info.minY)
                        originalGeometry.Add(info, pen + info.minX, info.minY, pen + info.maxX, info.maxY);
                }
                else if (fallback != null && fallback.GetCharacterInfo(c, out info, requestedSize))
                {
                    float width = info.maxX - info.minX, height = info.maxY - info.minY;
                    if (width > 0 && height > 0)
                    {
                        float scale = Mathf.Min(1f, Mathf.Min(cell / width, (referenceTop - referenceBottom) / height));
                        float glyphWidth = width * scale, glyphHeight = height * scale;
                        float left = pen + (cell - glyphWidth) / 2f;
                        float bottom = referenceBottom + ((referenceTop - referenceBottom) - glyphHeight) / 2f;
                        fallbackGeometry.Add(info, left, bottom, left + glyphWidth, bottom + glyphHeight);
                    }
                }
                // Whitespace and genuinely missing glyphs still keep their character cell.
                pen += cell;
            }

            Mesh originalMesh = null, fallbackMesh = null, bitmapMesh = null;
            bool began = false, matrixPushed = false;
            RenderTexture previousTarget = RenderTexture.active;
            try
            {
                originalMesh = originalGeometry.Create();
                fallbackMesh = fallbackGeometry.Create();
                bitmapMesh = bitmapGeometry.Create();
                began = true;
                a.Begin.Invoke(graphics, null);
                GL.PushMatrix(); matrixPushed = true;
                GL.LoadPixelMatrix(0, target.width, 0, target.height);
                float baseline = target.height - y - size + original.lineHeight - original.ascent;
                Matrix4x4 matrix = Matrix4x4.TRS(new Vector3(x, baseline, 0), Quaternion.identity, new Vector3(horizontalScale, 1f, 1f));
                Color color = (Color)a.Color.GetValue(graphics);
                Render(originalMesh, original, color, matrix);
                Render(fallbackMesh, fallback, color, matrix);
                if (bitmapMesh != null)
                {
                    Material material=bitmap.MaterialFor(original);
                    material.SetColor("_Color",color);
                    if (material.SetPass(0)) Graphics.DrawMeshNow(bitmapMesh,matrix);
                }
            }
            finally
            {
                try
                {
                    if (matrixPushed) GL.PopMatrix();
                }
                finally
                {
                    try { if (began) a.End.Invoke(graphics, null); }
                    finally
                    {
                        RenderTexture.active = previousTarget;
                        if (originalMesh != null) UnityEngine.Object.Destroy(originalMesh);
                        if (fallbackMesh != null) UnityEngine.Object.Destroy(fallbackMesh);
                        if (bitmapMesh != null) UnityEngine.Object.Destroy(bitmapMesh);
                    }
                }
            }
            return false;
        }
        private static void Render(Mesh mesh, Font font, Color color, Matrix4x4 matrix)
        {
            if (mesh == null || font == null) return;
            Material material = font.material;
            if (material == null) return;
            material.SetColor("_Color", color);
            if (material.SetPass(0)) Graphics.DrawMeshNow(mesh, matrix);
        }
    }
}
