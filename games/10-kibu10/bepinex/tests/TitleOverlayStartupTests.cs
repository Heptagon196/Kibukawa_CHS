using System;
using System.Reflection;
namespace HarmonyLib {
 public class Harmony { public void Patch(MethodInfo m,HarmonyMethod postfix=null) {} }
 public class HarmonyMethod { public HarmonyMethod(Type t,string n) {} }
 public static class AccessTools {
  public static Type TypeByName(string n) {return typeof(AccessTools).Assembly.GetType(n);}
  public static FieldInfo Field(Type t,string n) {return t.GetField(n);}
  public static MethodInfo Method(Type t,string n) {return t.GetMethod(n);}
  public static MethodInfo Method(Type t,string n,Type[] a) {return t.GetMethod(n,a);}
 }
}
namespace UnityEngine {
 public class Object {}
 public enum TextureFormat {RGBA32} public enum FilterMode {Point}
 public class Texture2D {public int width,height;public FilterMode filterMode;public Texture2D(int w,int h,TextureFormat f,bool m){width=w;height=h;}}
 public static class ImageConversion {public static bool LoadImage(Texture2D t,byte[] b,bool m){return true;}}
 public static class Debug {public static void LogWarning(string m){throw new Exception(m);}}
}
namespace Socotra.UI {
 public class Image {
  public static System.Collections.Generic.List<Image> Instances=new System.Collections.Generic.List<Image>();
  public static bool ScreenReady;public static int Created,Disposed;
  public UnityEngine.Texture2D Texture {get;set;} public bool IsDisposable {get;set;}
  public static Image CreateImage(int w,int h){if(!ScreenReady)throw new NullReferenceException("StScreenManager.Instance is null during BepInEx Awake");Created++;var image=new Image();Instances.Add(image);return image;}
  public void Dispose(){Disposed++;}
 }
 public class StGraphics {public int Drawn;public void DrawImage(Image i,int x,int y){if(i==null || x!=27 || y!=34)throw new Exception("Missing or displaced complete title panel");if(i.Texture==null)return;Drawn++;}}
}
public class TitleCanvasStub {public static object Image_Haikei=new object();public int CommandCursorPos,t_counter,MainTask;public bool draw_flag=true;public void PaintTitle(Socotra.UI.StGraphics g){}}
public static class TitleOverlayStartupTests {
 public static void Run(string folder){
  Kibu10ZhCN.Images.TitleMenuOverlay.Initialize(folder,typeof(TitleCanvasStub),new HarmonyLib.Harmony());
  if(Socotra.UI.Image.Created!=0)throw new Exception("Startup must not create screen-owned images before the game screen exists");
  Socotra.UI.Image.ScreenReady=true;
  var g=new Socotra.UI.StGraphics();var c=new TitleCanvasStub();
  var method=typeof(Kibu10ZhCN.Images.TitleMenuOverlay).GetMethod("AfterPaint",BindingFlags.Static|BindingFlags.NonPublic);
  method.Invoke(null,new object[]{c,g});method.Invoke(null,new object[]{c,g});
  if(Socotra.UI.Image.Created!=15 || g.Drawn!=2)throw new Exception("First title paint must lazily load 15 complete panels once and draw one panel per frame");
  for(int selected=0;selected<3;selected++)for(int phase=0;phase<8;phase++){
   c.CommandCursorPos=selected;c.t_counter=phase;method.Invoke(null,new object[]{c,g});
  }
  if(Socotra.UI.Image.Created!=15 || g.Drawn!=26)throw new Exception("Every selection/phase must reuse its panel without leaking images");
  // DrawImage silently skips a lost texture, as the real game does. Re-entry
  // must not leave the older, smaller native button visible underneath.
  foreach(var im in Socotra.UI.Image.Instances)im.Texture=null;
  method.Invoke(null,new object[]{c,g});
  if(g.Drawn!=27 || Socotra.UI.Image.Created!=30)throw new Exception("Returning to title must recreate lost menu panels and cover the old button");
  for(int entry=0;entry<3;entry++){
   TitleCanvasStub.Image_Haikei=new object();c.CommandCursorPos=entry;
   method.Invoke(null,new object[]{c,g});
  }
  if(g.Drawn!=30 || Socotra.UI.Image.Created!=75)throw new Exception("Repeated title backgrounds must renew screen-owned panels");
  Kibu10ZhCN.Images.TitleMenuOverlay.Dispose();
  if(Socotra.UI.Image.Disposed!=75)throw new Exception("All overlay images must be disposed");
 }
}
