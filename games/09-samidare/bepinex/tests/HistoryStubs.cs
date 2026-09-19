// Test-only dependencies for the ninth-game history regression.
// Never included in the plugin build and never loads a game assembly.
using System;
using System.Collections.Generic;
using System.Reflection;

namespace BepInEx
{
    public class BepInPlugin : Attribute { public BepInPlugin(string a, string b, string c) { } }
    public class BepInDependency : Attribute { public BepInDependency(string a, object b = null) { } }
    public class BaseUnityPlugin
    {
        public ConfigStub Config = new ConfigStub(); public InfoStub Info = new InfoStub();
        public LogStub Logger = new LogStub(); public bool enabled = true;
        protected void Destroy(UnityEngine.Object value) { }
    }
    public class ConfigStub { public ValueStub Bind(string a, string b, bool c, string d) { return new ValueStub { Value = c }; } }
    public class ValueStub { public bool Value; }
    public class InfoStub { public string Location; public MetadataStub Metadata = new MetadataStub(); }
    public class MetadataStub { public string GUID = "test"; }
    public class LogStub { public void LogInfo(object v) { } public void LogWarning(object v) { } public void LogError(object v) { } }
    public static class Paths { public static string GameRootPath; }
}

namespace HarmonyLib
{
    public enum Priority { Last = 800 }
    public class Harmony { public Harmony(string s) { } public void UnpatchSelf() { } public void Patch(MethodBase a, HarmonyMethod b, HarmonyMethod c, object d, HarmonyMethod e, object f = null) { } }
    public class HarmonyMethod : Attribute { public Priority priority; public HarmonyMethod(Type t, string s) { } }
    public static class AccessTools
    {
        public static FieldInfo Field(Type t, string s) { return t.GetField(s, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static); }
        public static Type TypeByName(string s) { return Type.GetType(s); }
        public static MethodInfo Method(Type t, string s) { return t.GetMethod(s); }
        public static MethodInfo Method(Type t, string s, Type[] p) { return t == null ? null : t.GetMethod(s, p); }
    }
}

namespace UnityEngine
{
    public class Object
    {
        public static Object found;
        public static Object FindObjectOfType(Type type) { return found != null && type.IsInstanceOfType(found) ? found : null; }
    }
    public class Font : Object { public static Font CreateDynamicFontFromOSFont(string[] names, int size) { return new Font(); } }
    public class Texture2D : Object { public static Texture2D whiteTexture = new Texture2D(); }
    public struct Vector2 { public float x, y; public Vector2(float a, float b) { x = a; y = b; } }
    public struct Vector3 { public float x, y, z; public Vector3(float a, float b, float c) { x = a; y = b; z = c; } }
    public struct Color
    {
        public float r, g, b, a;
        public Color(float x, float y, float z, float w) { r = x; g = y; b = z; a = w; }
        public static Color white { get { return new Color(1f, 1f, 1f, 1f); } }
    }
    public struct Rect { public float x, y, width, height; public Rect(float a, float b, float c, float d) { x = a; y = b; width = c; height = d; } }
    public struct Matrix4x4 { public static Matrix4x4 Scale(Vector3 v) { return new Matrix4x4(); } }
    public class RectOffset { public RectOffset(int a, int b, int c, int d) { } }
    public class GUIContent { public GUIContent(string s) { } }
    public class GUIStyle
    {
        public GUIStyle() { }
        public GUIStyle(GUIStyle s) { }
        public bool wordWrap; public int fontSize; public Font font; public bool richText;
        public RectOffset padding = new RectOffset(0, 0, 0, 0);
        public StyleState normal = new StyleState();
        public float lineHeight = 24f;
        public Vector2 CalcSize(GUIContent c) { return new Vector2(c == null ? 0 : 12f, lineHeight); }
    }
    public class StyleState { public Color textColor; }
    public class GUISkin { public GUIStyle label = new GUIStyle(); public GUIStyle button = new GUIStyle(); }
    public static class GUI
    {
        public static GUISkin skin = new GUISkin();
        public static bool enabled = true;
        public static Matrix4x4 matrix;
        public static int depth;
        public static Color color;
        public static void DrawTexture(Rect r, Texture2D t) { }
        public static void Label(Rect r, string s, GUIStyle g) { }
        public static bool Button(Rect r, string s, GUIStyle g) { return false; }
        public static Vector2 BeginScrollView(Rect r, Vector2 v, Rect q) { return v; }
        public static void EndScrollView() { }
    }
    public static class Screen { public static int width = 640, height = 480; }
    public static class Mathf
    {
        public static float Min(float a, float b) { return a < b ? a : b; }
        public static float Max(float a, float b) { return a > b ? a : b; }
        public static float Clamp(float v, float a, float b) { return v < a ? a : v > b ? b : v; }
    }
    public static class Time { public static int frameCount; public static float timeScale = 1f; public static float unscaledDeltaTime = 0.016f; }
    public static class Application { public static bool isFocused = true; }
    public static class Input
    {
        public static HashSet<KeyCode> held = new HashSet<KeyCode>();
        public static HashSet<KeyCode> down = new HashSet<KeyCode>();
        public static bool GetKey(KeyCode k) { return held.Contains(k); }
        public static bool GetKeyDown(KeyCode k) { return down.Contains(k); }
    }
    public enum KeyCode { None, H, PageUp, Escape, UpArrow, DownArrow, Home, End }
    public class AudioSource : Object { public bool mute; }
    public class MonoBehaviour : Object { }
}

namespace UnityEngine.UI
{
    public class Text : UnityEngine.Object { public string text = String.Empty; }
}

namespace UnityEngine.EventSystems
{
    public class EventSystem : UnityEngine.Object
    {
        public static EventSystem current;
        public bool enabled = true;
        public void Update() { }
    }
}

namespace Socotra.UI
{
    public sealed class StDisplay : UnityEngine.Object
    {
        public object currentFrame;
        public UnityEngine.UI.Text softKey1Label = new UnityEngine.UI.Text();
        public int keypadState;
    }
}
