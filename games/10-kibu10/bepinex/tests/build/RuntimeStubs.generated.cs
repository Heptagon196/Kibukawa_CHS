// Test-only dependencies. Never include in plugin build or load a game assembly.
using System;
using System.Reflection;
namespace BepInEx {
 public class BepInPlugin : Attribute { public BepInPlugin(string a,string b,string c) {} }
 public class BepInProcess : Attribute { public BepInProcess(string a) {} }
 public class BaseUnityPlugin { public ConfigStub Config = new ConfigStub(); public InfoStub Info = new InfoStub(); public LogStub Logger = new LogStub(); }
 public class ConfigStub { public ValueStub Bind(string a,string b,bool c,string d) { return new ValueStub { Value=c }; } }
 public class ValueStub { public bool Value; }
 public class InfoStub { public string Location; }
 public class LogStub { public void LogInfo(object v) {} public void LogWarning(object v) {} public void LogError(object v) {} }
 public static class Paths { public static string GameRootPath; }
}
namespace HarmonyLib {
 public class Harmony { public Harmony(string s) {} public void UnpatchSelf() {} public void Unpatch(MethodBase original,MethodInfo patch) {} public void Patch(MethodBase a,HarmonyMethod prefix=null,HarmonyMethod postfix=null,object transpiler=null,HarmonyMethod finalizer=null,object f=null) {} }
 public class HarmonyMethod { public HarmonyMethod(Type t,string s) {} }
 public static class AccessTools {
  public static FieldInfo Field(Type t,string s) { return t.GetField(s,BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.Static); }
  public static Type TypeByName(string s) { return Type.GetType(s); }
  public static MethodInfo Method(Type t,string s) { return t.GetMethod(s); }
  public static MethodInfo Method(Type t,string s,Type[] p) { return t.GetMethod(s,p); }
  public static MethodInfo EnumeratorMoveNext(MethodInfo m) { return m; }
 }
}
namespace UnityEngine {
 public class Font {}
 public struct Vector2 { public float x,y; }
 public struct Rect { public float x,y,width,height; public Rect(float a,float b,float c,float d) { x=a;y=b;width=c;height=d; } }
 public class GUIContent { public GUIContent(string s) {} }
 public class GUIStyle { public GUIStyle() {} public GUIStyle(GUIStyle s) {} public bool wordWrap;public int fontSize;public Font font; public float CalcHeight(GUIContent c,float f) { return f; } }
 public class GUISkin { public GUIStyle label = new GUIStyle(); }
 public static class GUI { public static GUISkin skin = new GUISkin(); public static void Box(Rect r,string s) {} public static bool Button(Rect r,string s,GUIStyle g) { return false; } public static Vector2 BeginScrollView(Rect r,Vector2 v,Rect q) { return v; } public static void Label(Rect r,string s,GUIStyle g) {} public static void EndScrollView() {} }
 public static class Screen { public static int width=640,height=480; }
}
namespace Kibu1ZhCN {
 public class BitmapFontAtlas { public BitmapFontAtlas(string p) {} public int GlyphCount; public void Dispose() {} }
 public static class LegacyFontRenderer { public static BitmapFontAtlas Small,Primary; public static int X,Y; public static float Scale; public static float? Top; public static bool Draw(object o,char[] c,int x,int y,object a,BitmapFontAtlas f,float s,BitmapFontAtlas small=null,float? top=null) { X=x;Y=y;Scale=s;Top=top;Small=small;Primary=f;return false; } }
}
namespace Kibu8ZhCN {
 public static class UiLocalization { public static void Initialize(Action<string> a) {} public static void RegisterDisplayTranslation(string a,string b) {} public static void Update() {} public static void Dispose() {} public static UnityEngine.Font GetChineseFont() { return null; } }
}

namespace Kibukawa.Engine.Gmode20050817 { internal static class NativeChoiceMemory { internal static void Install(HarmonyLib.Harmony harmony, System.Type canvas) {} } }

namespace Kibukawa.Engine.Gmode20050817 { internal static class NativeMenuPosition { internal static void Install(HarmonyLib.Harmony harmony, System.Type canvas, int y) {} } }

namespace Kibu8ZhCN { internal static class NotebookReading { internal static void Install(HarmonyLib.Harmony h,System.Type t,Kibu1ZhCN.BitmapFontAtlas f,string p) {} internal static void Dispose() {} } }

namespace HarmonyLib { public class CodeInstruction { public System.Reflection.Emit.OpCode opcode; public object operand; public System.Collections.Generic.List<System.Reflection.Emit.Label> labels=new System.Collections.Generic.List<System.Reflection.Emit.Label>(); public CodeInstruction(System.Reflection.Emit.OpCode op,object value=null) { opcode=op;operand=value; } } }

namespace Kibukawa.Engine.Gmode20050817Direct { internal static class DirectChoiceMemory { internal static void Install(HarmonyLib.Harmony h,System.Type t) {} } }
namespace Socotra.UI { public sealed class StFont { public int Id; public static StFont GetFont(int id) { return new StFont { Id=id }; } } }
namespace Kibu10ZhCN { internal static class UiLocalization { internal static void Initialize(System.Action<string> logger=null) {} internal static void RegisterDisplayTranslation(string source,string target) {} internal static void Update() {} internal static void Dispose() {} } internal static class UiLocalizationData { internal static readonly System.Collections.Generic.Dictionary<string,string> Exact=new System.Collections.Generic.Dictionary<string,string>(); internal static readonly System.Collections.Generic.Dictionary<string,string> Keys=new System.Collections.Generic.Dictionary<string,string>(); } internal static class ScriptIdentityData { internal static readonly System.Collections.Generic.Dictionary<string,string> Names=new System.Collections.Generic.Dictionary<string,string>(); } }